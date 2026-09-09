# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from collections import defaultdict
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.terms import ValueWrapper
from frappe.utils import (
	add_days,
	cint,
	create_batch,
	cstr,
	flt,
	format_date,
	get_datetime,
	get_first_day,
	get_last_day,
	get_link_to_form,
	get_time,
	getdate,
	now_datetime,
	nowdate,
	strip_html,
	time_diff_in_hours,
)
from frappe.utils.background_jobs import get_job

import hrms
from hrms.hr.doctype.shift_assignment.shift_assignment import has_overlapping_timings
from hrms.hr.utils import (
	get_holidays_for_employee,
	validate_active_employee,
)
from hrms.utils.holiday_list import get_holiday_dates_between_range


class DuplicateAttendanceError(frappe.ValidationError):
	pass


class OverlappingShiftAttendanceError(frappe.ValidationError):
	pass


class Attendance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_overtime_duration: DF.Float
		amended_from: DF.Link | None
		attendance_date: DF.Date
		attendance_request: DF.Link | None
		company: DF.Link
		daily_pay: DF.Currency
		department: DF.Link | None
		early_exit: DF.Check
		employee: DF.Link
		employee_name: DF.Data | None
		half_day_status: DF.Literal["", "Present", "Absent"]
		hour_rate: DF.Currency
		hours_paid: DF.Check
		in_time: DF.Datetime | None
		late_entry: DF.Check
		leave_application: DF.Link | None
		leave_type: DF.Link | None
		modify_half_day_status: DF.Check
		naming_series: DF.Literal["HR-ATT-.YYYY.-"]
		net_daily_pay: DF.Currency
		out_time: DF.Datetime | None
		overtime_type: DF.Link | None
		shift: DF.Link | None
		ss_deduction: DF.Currency
		standard_working_hours: DF.Float
		status: DF.Literal["", "Present", "Absent", "On Leave", "Half Day", "Work From Home"]
		tax_deduction: DF.Currency
		working_hours: DF.Float
	# end: auto-generated types

	def before_insert(self):
		if self.half_day_status == "":
			self.half_day_status = None

	def validate(self):
		from erpnext.controllers.status_updater import validate_status

		validate_status(self.status, ["Present", "Absent", "On Leave", "Half Day", "Work From Home"])
		validate_active_employee(self.employee)
		self.validate_attendance_date()
		self.validate_duplicate_record()
		self.validate_overlapping_shift_attendance()
		self.validate_employee_status()
		self.check_leave_record()
		self.ensure_working_hours()
		self.refresh_daily_pay()

	def ensure_working_hours(self):
		try:
			from hrms.payroll.daily_pay import ensure_working_hours_from_times

			ensure_working_hours_from_times(self)
		except Exception:
			frappe.log_error(title="Working hours calculation failed")

	def refresh_daily_pay(self):
		try:
			from hrms.payroll.daily_pay import refresh_attendance_payroll

			refresh_attendance_payroll(self)
		except Exception:
			frappe.log_error(title="Daily pay calculation failed")

	def on_update(self):
		try:
			from hrms.payroll.daily_pay import on_attendance_update

			on_attendance_update(self)
		except Exception:
			frappe.log_error(title="Daily pay week allocation failed")

	def on_submit(self):
		self.on_update()

	def on_cancel(self):
		self.unlink_attendance_from_checkins()

	def validate_attendance_date(self):
		date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")

		if date_of_joining and getdate(self.attendance_date) < getdate(date_of_joining):
			frappe.throw(
				_("Attendance date {0} can not be less than employee {1}'s joining date: {2}").format(
					frappe.bold(format_date(self.attendance_date)),
					frappe.bold(self.employee),
					frappe.bold(format_date(date_of_joining)),
				)
			)

	def validate_duplicate_record(self):
		duplicate = self.get_duplicate_attendance_record()

		if duplicate:
			frappe.throw(
				_("Attendance for employee {0} is already marked for the date {1}: {2}").format(
					frappe.bold(self.employee),
					frappe.bold(format_date(self.attendance_date)),
					get_link_to_form("Attendance", duplicate),
				),
				title=_("Duplicate Attendance"),
				exc=DuplicateAttendanceError,
			)

	def get_duplicate_attendance_record(self) -> str | None:
		Attendance = frappe.qb.DocType("Attendance")
		query = (
			frappe.qb.from_(Attendance)
			.select(Attendance.name)
			.where(
				(Attendance.employee == self.employee)
				& (Attendance.docstatus < 2)
				& (Attendance.attendance_date == self.attendance_date)
				& (Attendance.name != self.name)
				& (
					Attendance.half_day_status.isnull()
					| (Attendance.half_day_status == "")
					| (Attendance.modify_half_day_status == 0)
				)
			)
			.for_update()
		)

		if self.shift:
			query = query.where(
				((Attendance.shift.isnull()) | (Attendance.shift == ""))
				| (
					((Attendance.shift.isnotnull()) | (Attendance.shift != ""))
					& (Attendance.shift == self.shift)
				)
			)

		duplicate = query.run(pluck=True)

		return duplicate[0] if duplicate else None

	def validate_overlapping_shift_attendance(self):
		attendance = self.get_overlapping_shift_attendance()

		if attendance:
			frappe.throw(
				_("Attendance for employee {0} is already marked for an overlapping shift {1}: {2}").format(
					frappe.bold(self.employee),
					frappe.bold(attendance.shift),
					get_link_to_form("Attendance", attendance.name),
				),
				title=_("Overlapping Shift Attendance"),
				exc=OverlappingShiftAttendanceError,
			)

	def get_overlapping_shift_attendance(self) -> dict:
		if not self.shift:
			return {}

		Attendance = frappe.qb.DocType("Attendance")
		same_date_attendance = (
			frappe.qb.from_(Attendance)
			.select(Attendance.name, Attendance.shift)
			.where(
				(Attendance.employee == self.employee)
				& (Attendance.docstatus < 2)
				& (Attendance.attendance_date == self.attendance_date)
				& (Attendance.shift != self.shift)
				& (Attendance.name != self.name)
			)
		).run(as_dict=True)

		for d in same_date_attendance:
			if has_overlapping_timings(self.shift, d.shift):
				return d

		return {}

	def validate_employee_status(self):
		if frappe.db.get_value("Employee", self.employee, "status") == "Inactive":
			frappe.throw(_("Cannot mark attendance for an Inactive employee {0}").format(self.employee))

	def check_leave_record(self):
		LeaveApplication = frappe.qb.DocType("Leave Application")
		leave_record = (
			frappe.qb.from_(LeaveApplication)
			.select(
				LeaveApplication.leave_type,
				LeaveApplication.half_day,
				LeaveApplication.half_day_date,
				LeaveApplication.name,
			)
			.where(
				(LeaveApplication.employee == self.employee)
				& (self.attendance_date >= LeaveApplication.from_date)
				& (self.attendance_date <= LeaveApplication.to_date)
				& (LeaveApplication.status == "Approved")
				& (LeaveApplication.docstatus == 1)
			)
		).run(as_dict=True)

		if leave_record:
			for d in leave_record:
				self.leave_type = d.leave_type
				self.leave_application = d.name
				if d.half_day_date == getdate(self.attendance_date):
					self.status = "Half Day"
					frappe.msgprint(
						_("Employee {0} on Half day on {1}").format(
							self.employee, format_date(self.attendance_date)
						)
					)
				else:
					self.status = "On Leave"
					frappe.msgprint(
						_("Employee {0} is on Leave on {1}").format(
							self.employee, format_date(self.attendance_date)
						)
					)

		if self.status in ("On Leave", "Half Day"):
			if not leave_record:
				self.modify_half_day_status = 0
				self.half_day_status = "Absent"
				frappe.msgprint(
					_("No leave record found for employee {0} on {1}").format(
						self.employee, format_date(self.attendance_date)
					),
					alert=1,
				)
		elif self.leave_type:
			self.leave_type = None
			self.leave_application = None

	def validate_employee(self):
		Employee = frappe.qb.DocType("Employee")
		emp = (
			frappe.qb.from_(Employee)
			.select(Employee.name)
			.where((Employee.name == self.employee) & (Employee.status == "Active"))
		).run()
		if not emp:
			frappe.throw(_("Employee {0} is not active or does not exist").format(self.employee))

	def unlink_attendance_from_checkins(self):
		EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
		linked_logs = (
			frappe.qb.from_(EmployeeCheckin)
			.select(EmployeeCheckin.name)
			.where(EmployeeCheckin.attendance == self.name)
			.for_update()
			.run(as_dict=True)
		)

		if linked_logs:
			(
				frappe.qb.update(EmployeeCheckin)
				.set("attendance", "")
				.where(EmployeeCheckin.attendance == self.name)
			).run()

			frappe.msgprint(
				msg=_("Unlinked Attendance record from Employee Checkins: {}").format(
					", ".join(get_link_to_form("Employee Checkin", log.name) for log in linked_logs)
				),
				title=_("Unlinked logs"),
				indicator="blue",
				is_minimizable=True,
				wide=True,
			)

	def on_update(self):
		self.publish_update()

	def after_delete(self):
		self.publish_update()

	def publish_update(self):
		employee_user = frappe.db.get_value("Employee", self.employee, "user_id", cache=True)
		hrms.refetch_resource("hrms:attendance_calendar_events", employee_user)


def _normalize_calendar_filters(filters: str | list | dict | None) -> list | dict:
	if isinstance(filters, str):
		import json

		filters = json.loads(filters)
	if not filters:
		return []
	if isinstance(filters, dict):
		return filters

	normalized = []
	for item in filters:
		if isinstance(item, (list, tuple)) and len(item) >= 4 and item[0] == "Attendance":
			normalized.append(list(item[1:4]))
		else:
			normalized.append(item)
	return normalized


@frappe.whitelist()
def get_events(start: date | str, end: date | str, filters: str | list | None = None) -> list[dict]:
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
	filters = _normalize_calendar_filters(filters)
	if isinstance(filters, list):
		filters.append(["attendance_date", "between", [get_datetime(start).date(), get_datetime(end).date()]])
	else:
		filters["attendance_date"] = ["between", [get_datetime(start).date(), get_datetime(end).date()]]
	attendance_records = add_attendance(filters)
	_merge_live_day_entries(attendance_records, start, end)
	if employee:
		add_holidays(attendance_records, start, end, employee)
	return attendance_records


@frappe.whitelist()
def get_calendar_day_roster(attendance_date: str):
	day = getdate(attendance_date)
	payload = _today_live_payload(day)
	if payload is None:
		payload = roster_from_attendance(day)
		_attach_clients(payload)
	return _trim_inactive_roster(payload, day)


def _today_live_payload(day):
	hr_roles = {"HR Manager", "HR User", "System Manager", "Administrator"}
	if not hr_roles.intersection(frappe.get_roles()):
		return None
	from hrms.hr.page.in_out_today.in_out_today import get_in_out_today

	try:
		payload = get_in_out_today(attendance_date=str(day))
	except frappe.PermissionError:
		return None
	_attach_clients(payload)
	return payload


def _attach_clients(payload: dict) -> dict:
	details = payload.get("details") or []
	clients = _employee_clients([row.get("employee") for row in details])
	for row in details:
		row["client"] = clients.get(row.get("employee")) or row.get("client") or ""
	return payload


def _has_day_activity(row: dict) -> bool:
	return bool(
		row.get("in_time")
		or row.get("out_time")
		or row.get("time")
		or row.get("attendance")
		or row.get("pto_code")
		or row.get("status") == "IN"
		or row.get("late")
	)


def _trim_inactive_roster(payload: dict, day) -> dict:
	if getdate(day) == getdate():
		return payload
	details = [row for row in payload.get("details") or [] if _has_day_activity(row)]
	payload["details"] = details
	payload["departments"] = sorted({row.get("department") for row in details if row.get("department")})
	payload["totals"] = {
		"total": len(details),
		"in_count": sum(1 for row in details if row.get("status") == "IN"),
		"out_count": sum(1 for row in details if row.get("status") == "OUT"),
		"late": sum(1 for row in details if row.get("late")),
	}
	return payload


def roster_from_attendance(attendance_date):
	rows = frappe.get_list(
		"Attendance",
		fields=[
			"name",
			"employee",
			"employee_name",
			"department",
			"status",
			"in_time",
			"out_time",
			"late_entry",
		],
		filters={"attendance_date": getdate(attendance_date), "docstatus": ["<", 2]},
		order_by="employee_name",
	)
	images = _employee_images([row.employee for row in rows])
	as_of = now_datetime() if getdate(attendance_date) == getdate() else get_datetime(add_days(attendance_date, 1))
	details = []
	for row in rows:
		in_dt = get_datetime(row.in_time) if row.in_time else None
		out_dt = get_datetime(row.out_time) if row.out_time else None
		if out_dt and out_dt <= as_of:
			status = "OUT"
		elif in_dt and in_dt <= as_of:
			status = "IN"
		else:
			status = "OUT"

		details.append(
			{
				"employee": row.employee,
				"employee_name": row.employee_name or row.employee,
				"image": images.get(row.employee) or "",
				"department": row.department or "",
				"status": status,
				"late": bool(row.late_entry),
				"late_minutes": 0,
				"late_label": "",
				"attendance_status": row.status or "",
				"attendance": row.name,
				"date": str(getdate(attendance_date)),
				"in_time": _format_clock(in_dt),
				"out_time": _format_clock(out_dt),
				"time": _format_clock(out_dt or in_dt),
				"leave_type": "On Leave" if row.status == "On Leave" else "",
				"pto_code": row.status if row.status == "On Leave" else "",
				"device_id": "",
			}
		)

	departments = sorted({row["department"] for row in details if row["department"]})
	return {
		"date": str(getdate(attendance_date)),
		"departments": departments,
		"totals": {
			"total": len(details),
			"in_count": sum(1 for row in details if row["status"] == "IN"),
			"out_count": sum(1 for row in details if row["status"] == "OUT"),
			"late": sum(1 for row in details if row["late"]),
		},
		"summary": [],
		"details": details,
	}


def _format_clock(value):
	if not value:
		return ""
	return get_datetime(value).strftime("%I:%M %p").lstrip("0")


def _employee_images(employee_ids: list[str]) -> dict[str, str]:
	ids = [name for name in {cstr(employee_id) for employee_id in employee_ids} if name]
	if not ids:
		return {}
	return {
		row.name: row.image or ""
		for row in frappe.get_all("Employee", filters={"name": ["in", ids]}, fields=["name", "image"])
	}


def _employee_clients(employee_ids: list[str]) -> dict[str, str]:
	ids = [name for name in {cstr(employee_id) for employee_id in employee_ids} if name]
	if not ids or not frappe.get_meta("Employee").has_field("bill_to_customer"):
		return {}
	employees = frappe.get_all(
		"Employee",
		filters={"name": ["in", ids]},
		fields=["name", "bill_to_customer"],
	)
	customer_ids = [row.bill_to_customer for row in employees if row.bill_to_customer]
	customer_names = {}
	if customer_ids and frappe.db.exists("DocType", "Customer"):
		customer_names = {
			row.name: row.customer_name or row.name
			for row in frappe.get_all(
				"Customer",
				filters={"name": ["in", customer_ids]},
				fields=["name", "customer_name"],
			)
		}
	return {
		row.name: customer_names.get(row.bill_to_customer) or row.bill_to_customer or ""
		for row in employees
	}


def add_attendance(filters):
	attendance = frappe.get_list(
		"Attendance",
		fields=[
			"name",
			ValueWrapper("Attendance").as_("doctype"),
			"attendance_date",
			"employee",
			"employee_name",
			"department",
			"status",
			"in_time",
			"out_time",
			"late_entry",
			"docstatus",
		],
		filters=filters,
	)
	images = _employee_images([record.employee for record in attendance])
	clients = _employee_clients([record.employee for record in attendance])
	for record in attendance:
		record["image"] = images.get(record.employee) or ""
		record["client"] = clients.get(record.employee) or ""
		record["title"] = f"{record['employee_name']} : {record['status']}"
		record["allDay"] = 1
		record["color"] = "transparent"
		record["in_time"] = cstr(record.get("in_time") or "")
		record["out_time"] = cstr(record.get("out_time") or "")
		if record["in_time"] and not record["out_time"]:
			record["inout"] = "IN"
		elif record["out_time"]:
			record["inout"] = "OUT"
	return attendance


def _merge_live_day_entries(events: list[dict], start: date | str, end: date | str) -> None:
	"""Include today's clock-ins even when Attendance has not been marked yet."""
	today = getdate()
	range_start = get_datetime(start).date()
	range_end = get_datetime(end).date()
	if today < range_start or today > range_end:
		return

	existing = {}
	for row in events:
		if row.get("doctype") == "Holiday":
			continue
		if getdate(row.get("attendance_date")) != today:
			continue
		if row.get("employee"):
			existing[row["employee"]] = row

	checkins = frappe.get_list(
		"Employee Checkin",
		fields=["employee", "log_type", "time"],
		filters=[
			["time", ">=", get_datetime(today)],
			["time", "<", get_datetime(add_days(today, 1))],
		],
		order_by="time asc",
	)
	punches_by_employee = defaultdict(list)
	for row in checkins:
		punches_by_employee[row.employee].append(row)

	employee_ids = list(set(punches_by_employee) | set(existing))
	if not employee_ids:
		_merge_today_roster(events, existing, today)
		return

	images = _employee_images(employee_ids)
	clients = _employee_clients(employee_ids)
	employees = {
		row.name: row
		for row in frappe.get_all(
			"Employee",
			filters={"name": ["in", employee_ids]},
			fields=["name", "employee_name", "department", "image"],
		)
	}
	as_of = now_datetime()

	for employee_id, punches in punches_by_employee.items():
		occurred = [punch for punch in punches if punch.time and get_datetime(punch.time) <= as_of]
		if not occurred:
			continue
		first_in = next((punch for punch in occurred if (punch.log_type or "IN") == "IN"), None)
		last_out = None
		for punch in occurred:
			if (punch.log_type or "IN") == "OUT":
				last_out = punch
		latest = occurred[-1]
		inout = "IN" if (latest.log_type or "IN") != "OUT" else "OUT"
		in_time = cstr(first_in.time) if first_in else ""
		out_time = cstr(last_out.time) if last_out else ""

		if employee_id in existing:
			row = existing[employee_id]
			if in_time:
				row["in_time"] = in_time
			if out_time:
				row["out_time"] = out_time
			row["inout"] = inout
			if not row.get("client"):
				row["client"] = clients.get(employee_id) or ""
			continue

		employee = employees.get(employee_id)
		employee_name = (employee.employee_name if employee else None) or employee_id
		events.append(
			{
				"doctype": "Attendance",
				"attendance_date": today,
				"employee": employee_id,
				"employee_name": employee_name,
				"department": (employee.department if employee else "") or "",
				"client": clients.get(employee_id) or "",
				"status": "Present",
				"in_time": in_time,
				"out_time": out_time,
				"inout": inout,
				"late_entry": 0,
				"image": images.get(employee_id) or (employee.image if employee else "") or "",
				"title": f"{employee_name} : Present",
				"allDay": 1,
				"color": "transparent",
			}
		)
		existing[employee_id] = events[-1]

	_merge_today_roster(events, existing, today)


def _merge_today_roster(events: list[dict], existing: dict, today) -> None:
	"""Keep today's cell populated from the live In/Out roster, not only saved attendance."""
	payload = _today_live_payload(today)
	if not payload:
		return

	for detail in payload.get("details") or []:
		employee_id = detail.get("employee")
		if not employee_id:
			continue
		inout = detail.get("status") or "OUT"
		attendance_status = detail.get("attendance_status") or "Present"
		if employee_id in existing:
			row = existing[employee_id]
			row["inout"] = inout
			if detail.get("client"):
				row["client"] = detail["client"]
			if detail.get("image") and not row.get("image"):
				row["image"] = detail["image"]
			continue

		employee_name = detail.get("employee_name") or employee_id
		events.append(
			{
				"doctype": "Attendance",
				"attendance_date": today,
				"employee": employee_id,
				"employee_name": employee_name,
				"department": detail.get("department") or "",
				"client": detail.get("client") or "",
				"status": attendance_status,
				"in_time": detail.get("in_time") or "",
				"out_time": detail.get("out_time") or "",
				"inout": inout,
				"late_entry": 1 if detail.get("late") else 0,
				"late_minutes": detail.get("late_minutes") or 0,
				"late_label": detail.get("late_label") or "",
				"image": detail.get("image") or "",
				"title": f"{employee_name} : {attendance_status}",
				"allDay": 1,
				"color": "transparent",
			}
		)
		existing[employee_id] = events[-1]


def add_holidays(events, start, end, employee=None):
	holidays = get_holidays_for_employee(employee, start, end)
	if not holidays:
		return

	for holiday in holidays:
		events.append(
			{
				"doctype": "Holiday",
				"attendance_date": holiday.holiday_date,
				"title": _("Holiday") + ": " + cstr(holiday.description),
				"name": holiday.name,
				"allDay": 1,
			}
		)


def mark_attendance(
	employee,
	attendance_date,
	status,
	shift=None,
	leave_type=None,
	late_entry=False,
	early_exit=False,
	half_day_status=None,
):
	savepoint = "attendance_creation"

	try:
		frappe.db.savepoint(savepoint)
		attendance = frappe.new_doc("Attendance")
		attendance.update(
			{
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": attendance_date,
				"status": status,
				"shift": shift,
				"leave_type": leave_type,
				"late_entry": late_entry,
				"early_exit": early_exit,
				"half_day_status": half_day_status,
			}
		)
		attendance.insert()
		attendance.submit()
	except (DuplicateAttendanceError, OverlappingShiftAttendanceError):
		frappe.db.rollback(save_point=savepoint)
		return

	return attendance.name


@frappe.whitelist()
def mark_bulk_attendance(data: str | dict):
	import json

	if isinstance(data, str):
		data = json.loads(data)
	data = frappe._dict(data)
	if not data.unmarked_days:
		frappe.throw(_("Please select a date."))
		return
	if len(data.unmarked_days) > 10 or frappe.flags.test_bg_job:
		job_id = f"process_bulk_attendance_for_employee_{data.employee}"
		job = frappe.enqueue(
			process_bulk_attendance_in_batches, data=data, job_id=job_id, timeout=600, deduplicate=True
		)
		if job:
			message = _(
				"Bulk attendance marking is queued with a background job. It may take a while. You can monitor the job status {0}"
			).format(get_link_to_form("RQ Job", job.id, label="here"))
		else:
			message = _(
				"Bulk attendance marking is already in progress for employee {0}. You can monitor the job status {1}"
			).format(frappe.bold(data.employee), get_link_to_form("RQ Job", get_job(job_id).id, label="here"))
		frappe.msgprint(message, allow_dangerous_html=True)
	else:
		process_bulk_attendance_in_batches(data)
		frappe.msgprint(_("Attendance marked successfully."), alert=True)


def process_bulk_attendance_in_batches(data, chunk_size=20):
	savepoint = "mark_bulk_attendance"
	for days in create_batch(data.unmarked_days, chunk_size):
		for attendance_date in days:
			try:
				frappe.db.savepoint(savepoint)
				doc_dict = {
					"doctype": "Attendance",
					"employee": data.employee,
					"attendance_date": getdate(attendance_date),
					"status": data.status,
					"half_day_status": "Absent" if data.status == "Half Day" else None,
					"shift": data.shift,
				}
				attendance = frappe.get_doc(doc_dict).insert()
				attendance.submit()
			except (DuplicateAttendanceError, OverlappingShiftAttendanceError, Exception):
				if not frappe.flags.in_test:
					frappe.db.rollback(save_point=savepoint)
				continue
		if not frappe.flags.in_test:
			frappe.db.commit()  # nosemgrep


@frappe.whitelist()
def get_unmarked_days(
	employee: str, from_date: str | date, to_date: str | date, exclude_holidays: str | int = 0
) -> list:
	frappe.has_permission("Employee", "read", employee, throw=True)
	joining_date, relieving_date = frappe.get_cached_value(
		"Employee", employee, ["date_of_joining", "relieving_date"]
	)

	from_date = max(getdate(from_date), joining_date or getdate(from_date))
	to_date = min(getdate(to_date), relieving_date or getdate(to_date))

	records = frappe.get_all(
		"Attendance",
		fields=["attendance_date", "employee"],
		filters=[
			["attendance_date", ">=", from_date],
			["attendance_date", "<=", to_date],
			["employee", "=", employee],
			["docstatus", "!=", 2],
		],
	)

	marked_days = [getdate(record.attendance_date) for record in records]

	if cint(exclude_holidays):
		holiday_dates = get_holiday_dates_between_range(
			employee, from_date, to_date, raise_exception_for_holiday_list=False
		)
		holidays = [getdate(record) for record in holiday_dates]
		marked_days.extend(holidays)

	unmarked_days = []

	while from_date <= to_date:
		if from_date not in marked_days:
			unmarked_days.append(from_date)

		from_date = add_days(from_date, 1)

	return unmarked_days


@frappe.whitelist()
def get_employee_shift(employee: str, for_date: str | date | None = None) -> str | None:
	if not employee:
		return None

	if employee and not frappe.has_permission("Employee", "read", employee):
		return None

	if not for_date:
		for_date = nowdate()

	for_date = getdate(for_date)

	if not frappe.has_permission("Shift Assignment", "read"):
		return None

	shifts = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": employee,
			"docstatus": 1,
			"status": "Active",
			"start_date": ("<=", for_date),
		},
		fields=["shift_type", "start_date"],
		order_by="start_date desc",
		limit=1,
	)

	if shifts:
		return shifts[0].shift_type

	default_shift = frappe.db.get_value("Employee", employee, "default_shift")
	if default_shift:
		return default_shift

	return None


def _combine_date_and_time(attendance_date, clock_time) -> datetime:
	return datetime.combine(getdate(attendance_date), get_time(clock_time))


def _get_day_attendance(employee: str, attendance_date, shift: str | None = None):
	filters = {
		"employee": employee,
		"attendance_date": getdate(attendance_date),
		"docstatus": ("<", 2),
	}
	if shift:
		found = frappe.db.get_value(
			"Attendance", {**filters, "shift": shift}, ["name", "status", "docstatus"], as_dict=True
		)
		if found:
			return found
	return frappe.db.get_value("Attendance", filters, ["name", "status", "docstatus"], as_dict=True)


def _ensure_not_on_leave(employee: str, attendance_date, shift: str | None = None):
	# Leave check is day-wide; shift is only a preference when locating the Present row.
	day_row = frappe.db.get_value(
		"Attendance",
		{
			"employee": employee,
			"attendance_date": getdate(attendance_date),
			"docstatus": ("<", 2),
			"status": "On Leave",
		},
		["name", "status", "docstatus"],
		as_dict=True,
	)
	if day_row:
		frappe.throw(
			_("Attendance for {0} on {1} is already marked as On Leave: {2}").format(
				frappe.bold(employee),
				frappe.bold(format_date(attendance_date)),
				get_link_to_form("Attendance", day_row.name),
			),
			title=_("Cannot Replace Leave"),
		)
	return _get_day_attendance(employee, attendance_date, shift)


def _replace_existing_attendance(employee: str, attendance_date, shift: str | None = None):
	existing = _ensure_not_on_leave(employee, attendance_date, shift)
	if not existing:
		return

	doc = frappe.get_doc("Attendance", existing.name)
	if doc.docstatus == 1:
		doc.cancel()
	else:
		doc.delete()


def _clock_str(value) -> str | None:
	if not value:
		return None
	return get_datetime(value).strftime("%H:%M:%S")


def _insert_hours_checkin(employee: str, log_type: str, when: datetime, shift: str | None = None):
	log = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": employee,
			"log_type": log_type,
			"time": when,
			"shift": shift,
			"skip_auto_attendance": 1,
		}
	)
	log.flags.ignore_geolocation = True
	log.insert()
	return log


def _delete_checkin(name: str | None):
	if not name or not frappe.db.exists("Employee Checkin", name):
		return
	frappe.delete_doc("Employee Checkin", name, ignore_permissions=True, force=True)


def _resync_day_hours(employee: str, attendance_date, attendance_name: str | None = None) -> str | None:
	from hrms.payroll.daily_pay import resync_attendance_from_day_logs

	return resync_attendance_from_day_logs(
		employee, getdate(attendance_date), attendance_name=attendance_name
	)


@frappe.whitelist()
def add_hours_entry(
	employee: str,
	attendance_date: str | date,
	in_time: str,
	out_time: str | None = None,
	shift: str | None = None,
	comment: str | None = None,
	working_now: int | str | None = 0,
) -> str:
	frappe.has_permission("Attendance", "create", throw=True)
	frappe.has_permission("Employee Checkin", "create", throw=True)

	if not employee:
		frappe.throw(_("Employee is required."))

	working_now = cint(working_now)
	if not working_now and not out_time:
		frappe.throw(_("Out time is required."))

	attendance_date = getdate(attendance_date)
	existing = _ensure_not_on_leave(employee, attendance_date, shift)

	in_dt = _combine_date_and_time(attendance_date, in_time)
	_insert_hours_checkin(employee, "IN", in_dt, shift)
	if not working_now:
		out_dt = _combine_date_and_time(attendance_date, out_time)
		if out_dt <= in_dt:
			out_dt += timedelta(days=1)
		_insert_hours_checkin(employee, "OUT", out_dt, shift)

	attendance_name = _resync_day_hours(
		employee, attendance_date, attendance_name=existing.name if existing else None
	)
	if not attendance_name:
		frappe.throw(_("Could not add hours entry. Check for overlapping attendance."))
	# Apply shift if provided and attendance has none
	if shift and not frappe.db.get_value("Attendance", attendance_name, "shift"):
		frappe.db.set_value("Attendance", attendance_name, "shift", shift, update_modified=False)
	_add_hours_comment(attendance_name, comment)
	return attendance_name


@frappe.whitelist()
def add_hours_entries(
	employees: str | list,
	attendance_date: str | date,
	in_time: str,
	out_time: str | None = None,
	shift: str | None = None,
	comment: str | None = None,
	working_now: int | str | None = 0,
) -> list[str]:
	if isinstance(employees, str):
		employees = frappe.parse_json(employees)
	if not employees:
		frappe.throw(_("Select at least one user."))
	return [
		add_hours_entry(
			employee,
			attendance_date,
			in_time,
			out_time=out_time,
			shift=shift or None,
			comment=comment,
			working_now=working_now,
		)
		for employee in employees
	]


@frappe.whitelist()
def get_hours_entry(name: str, in_log: str | None = None, out_log: str | None = None) -> dict:
	if not name:
		frappe.throw(_("Attendance is required."))
	doc = frappe.get_doc("Attendance", name)
	doc.check_permission("read")
	comments = _hours_comments_by_attendance([name]).get(name, [])
	payload = {
		"name": doc.name,
		"employee": doc.employee,
		"shift": doc.shift,
		"attendance_date": doc.attendance_date,
		"in_time": _clock_str(doc.in_time),
		"out_time": _clock_str(doc.out_time),
		"working_now": 0 if doc.out_time else 1,
		"comment": comments[0]["content"] if comments else "",
		"in_log": None,
		"out_log": None,
		"kind": "attendance",
	}
	if in_log:
		in_doc = frappe.get_doc("Employee Checkin", in_log)
		if in_doc.employee != doc.employee:
			frappe.throw(_("Checkin does not belong to this attendance."))
		payload["in_log"] = in_log
		payload["out_log"] = out_log
		payload["kind"] = "pair"
		payload["in_time"] = _clock_str(in_doc.time)
		if out_log:
			out_doc = frappe.get_doc("Employee Checkin", out_log)
			payload["out_time"] = _clock_str(out_doc.time)
			payload["working_now"] = 0
		else:
			payload["out_time"] = None
			payload["working_now"] = 1
	return payload


@frappe.whitelist()
def update_hours_entry(
	name: str,
	attendance_date: str | date,
	in_time: str,
	out_time: str | None = None,
	shift: str | None = None,
	comment: str | None = None,
	working_now: int | str | None = 0,
	in_log: str | None = None,
	out_log: str | None = None,
) -> str:
	if not name:
		frappe.throw(_("Attendance is required."))
	doc = frappe.get_doc("Attendance", name)
	doc.check_permission("write")
	employee = doc.employee
	working_now = cint(working_now)
	attendance_date = getdate(attendance_date)

	if in_log:
		if not frappe.db.exists("Employee Checkin", in_log):
			frappe.throw(_("IN checkin not found."))
		in_dt = _combine_date_and_time(attendance_date, in_time)
		frappe.db.set_value(
			"Employee Checkin",
			in_log,
			{"time": in_dt, "shift": shift or None},
			update_modified=False,
		)
		if working_now:
			_delete_checkin(out_log)
			out_log = None
		else:
			if not out_time:
				frappe.throw(_("Out time is required."))
			out_dt = _combine_date_and_time(attendance_date, out_time)
			if out_dt <= in_dt:
				out_dt += timedelta(days=1)
			if out_log and frappe.db.exists("Employee Checkin", out_log):
				frappe.db.set_value(
					"Employee Checkin",
					out_log,
					{"time": out_dt, "shift": shift or None},
					update_modified=False,
				)
			else:
				_insert_hours_checkin(employee, "OUT", out_dt, shift)
		if shift:
			frappe.db.set_value("Attendance", name, "shift", shift, update_modified=False)
		attendance_name = _resync_day_hours(employee, attendance_date, attendance_name=name)
		if comment:
			_add_hours_comment(attendance_name or name, comment)
		return attendance_name or name

	# No pair ids: replace the day's punches with this single pair (legacy edit).
	day_logs = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [f"{attendance_date} 00:00:00", f"{attendance_date} 23:59:59"]],
		},
		pluck="name",
	)
	for log_name in day_logs:
		_delete_checkin(log_name)

	in_dt = _combine_date_and_time(attendance_date, in_time)
	_insert_hours_checkin(employee, "IN", in_dt, shift)
	if not working_now:
		if not out_time:
			frappe.throw(_("Out time is required."))
		out_dt = _combine_date_and_time(attendance_date, out_time)
		if out_dt <= in_dt:
			out_dt += timedelta(days=1)
		_insert_hours_checkin(employee, "OUT", out_dt, shift)

	if shift:
		frappe.db.set_value("Attendance", name, "shift", shift, update_modified=False)
	attendance_name = _resync_day_hours(employee, attendance_date, attendance_name=name)
	if comment:
		_add_hours_comment(attendance_name or name, comment)
	return attendance_name or name


@frappe.whitelist()
def add_absence(
	employee: str,
	from_date: str | date,
	to_date: str | date,
	leave_type: str | None = None,
	comment: str | None = None,
) -> dict:
	frappe.has_permission("Attendance", "create", throw=True)
	from_date = getdate(from_date)
	to_date = getdate(to_date)
	if to_date < from_date:
		frappe.throw(_("To date cannot be before from date."))

	if leave_type:
		frappe.has_permission("Leave Application", "create", throw=True)
		from hrms.hr.doctype.leave_application.leave_application import get_employee_leave_approver

		leave = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": leave_type,
				"from_date": from_date,
				"to_date": to_date,
				"leave_approver": get_employee_leave_approver(employee),
				"description": _("Added from Hours"),
			}
		)
		leave.insert()
		if leave.docstatus == 0:
			leave.submit()
		_add_hours_comment(leave.name, comment, doctype="Leave Application")
		for attendance_name in frappe.get_all(
			"Attendance",
			filters={"leave_application": leave.name, "docstatus": ("<", 2)},
			pluck="name",
		):
			_add_hours_comment(attendance_name, comment)
		return {
			"name": leave.name,
			"message": _("Time off request {0} submitted").format(leave.name),
		}

	created = []
	day = from_date
	while day <= to_date:
		if not frappe.db.exists(
			"Attendance",
			{"employee": employee, "attendance_date": day, "docstatus": ("<", 2)},
		):
			name = mark_attendance(employee, day, "Absent")
			if name:
				created.append(name)
				_add_hours_comment(name, comment)
		day = add_days(day, 1)

	return {
		"names": created,
		"message": _("Marked Absent for {0} day(s)").format(len(created)),
	}


def _hours_filters(
	from_date: str | date | None = None,
	to_date: str | date | None = None,
	employee: str | None = None,
	department: str | None = None,
) -> dict:
	filters: dict = {"docstatus": ("<", 2)}
	if from_date and to_date:
		filters["attendance_date"] = ["between", [getdate(from_date), getdate(to_date)]]
	if employee:
		filters["employee"] = employee
	if department:
		filters["department"] = department
	return filters


def _hours_list_fields() -> list[str]:
	fields = [
		"name",
		"employee",
		"employee_name",
		"attendance_date",
		"in_time",
		"out_time",
		"working_hours",
		"status",
		"shift",
		"leave_type",
		"docstatus",
		"actual_overtime_duration",
		"overtime_type",
		"standard_working_hours",
	]
	meta = frappe.get_meta("Attendance")
	for extra in (
		"hours_paid",
		"hour_rate",
		"daily_pay",
		"ss_deduction",
		"tax_deduction",
		"net_daily_pay",
		"company",
	):
		if meta.has_field(extra) and frappe.db.has_column("Attendance", extra):
			fields.append(extra)
	return fields


def _employee_hours_label(employee: dict | None, fallback: str | None = None) -> str:
	row = employee or {}
	last = cstr(row.get("last_name")).strip()
	first = cstr(row.get("first_name")).strip()
	if last and first:
		return f"{last}, {first}"
	return cstr(row.get("employee_name") or fallback or row.get("name") or "").strip()


def _hours_buckets(row, lwp_map: dict, ot_map: dict, holiday_ctx: dict | None = None) -> dict:
	row = frappe._dict(row)
	hours = flt(row.working_hours)
	ot_raw = flt(row.get("actual_overtime_duration"))
	std = flt(row.get("standard_working_hours")) or 8
	status = cstr(row.status)
	leave_type = cstr(row.get("leave_type"))
	multiplier = flt(ot_map.get(row.get("overtime_type"))) if row.get("overtime_type") else 0
	dt = ot_raw if multiplier >= 2 else 0
	ot = 0 if dt else ot_raw
	is_leave = status in ("On Leave", "Half Day") or bool(leave_type)
	is_lwp = bool(lwp_map.get(leave_type)) if leave_type else False

	reg = pto = paid = unpaid = 0.0
	hours_paid = cint(row.get("hours_paid"))
	if status == "Absent" and not (holiday_ctx and flt(row.get("daily_pay"))):
		unpaid = hours or std
		total = unpaid
	elif is_leave:
		pto = hours if hours else (std / 2 if status == "Half Day" else std)
		if is_lwp or not hours_paid:
			unpaid = pto
		else:
			paid = pto
		total = pto
	elif holiday_ctx:
		# Public holiday: show premium hours in OT/DT; statutory day still counts as reg.
		worked = hours if hours else std
		reg = worked
		if holiday_ctx.get("pay_double_time") and hours > 0:
			dt = hours
			ot = 0
		elif holiday_ctx.get("pay_time_and_a_half") and hours > 0:
			ot = hours
			dt = 0
		total = worked
		if hours_paid:
			paid = worked
		else:
			unpaid = worked
	else:
		reg = max(flt(hours - ot - dt, 2), 0)
		total = hours
		if hours_paid:
			paid = hours
		else:
			unpaid = hours

	job = leave_type or ("Absent" if status == "Absent" else "")
	if holiday_ctx and not job:
		job = "Holiday"
	return {
		"reg": flt(reg, 2),
		"ot": flt(ot, 2),
		"dt": flt(dt, 2),
		"pto": flt(pto, 2),
		"paid": flt(paid, 2),
		"unpaid": flt(unpaid, 2),
		"total": flt(total, 2),
		"job": job,
	}


def _decorate_hours_rows(rows: list) -> list:
	if not rows:
		return []

	employee_ids = list({cstr(row.get("employee")) for row in rows if row.get("employee")})
	emp_map = {}
	if employee_ids:
		for emp in frappe.get_all(
			"Employee",
			filters={"name": ["in", employee_ids]},
			fields=["name", "first_name", "last_name", "employee_name"],
		):
			emp_map[emp.name] = emp

	leave_types = list({cstr(row.get("leave_type")) for row in rows if row.get("leave_type")})
	lwp_map = {}
	if leave_types:
		for leave_type in frappe.get_all(
			"Leave Type",
			filters={"name": ["in", leave_types]},
			fields=["name", "is_lwp"],
		):
			lwp_map[leave_type.name] = cint(leave_type.is_lwp)

	ot_types = list({cstr(row.get("overtime_type")) for row in rows if row.get("overtime_type")})
	ot_map = {}
	if ot_types:
		for overtime in frappe.get_all(
			"Overtime Type",
			filters={"name": ["in", ot_types]},
			fields=["name", "standard_multiplier"],
		):
			ot_map[overtime.name] = flt(overtime.standard_multiplier)

	from hrms.payroll.daily_pay import get_public_holiday_pay_context

	holiday_cache = {}

	decorated = []
	for row in rows:
		data = dict(row)
		holiday_ctx = None
		emp = data.get("employee")
		day = data.get("attendance_date")
		status = cstr(data.get("status"))
		if emp and day and status not in ("On Leave", "Half Day", "Lunch"):
			cache_key = (emp, str(getdate(day)))
			if cache_key not in holiday_cache:
				holiday_cache[cache_key] = get_public_holiday_pay_context(emp, day)
			holiday_ctx = holiday_cache[cache_key]
		if data.get("kind") != "lunch":
			_fill_hours_from_clock(data)
		_ensure_hours_row_pay(data, holiday_ctx)
		data["employee_label"] = _employee_hours_label(
			emp_map.get(data.get("employee")), data.get("employee_name")
		)
		data.update(_hours_buckets(data, lwp_map, ot_map, holiday_ctx))
		if data.get("kind") == "lunch":
			data["status"] = "Lunch"
			data["job"] = "Lunch"
			data["shift"] = data.get("shift") or "Lunch"
		decorated.append(data)
	return _attach_weekly_ss(decorated)


def _checkins_by_employee_date(rows: list) -> dict[tuple, list]:
	"""Batch-load checkins keyed by (employee, attendance_date)."""
	employees = list({row.employee for row in rows if row.employee})
	dates = [getdate(row.attendance_date) for row in rows if row.attendance_date]
	if not employees or not dates:
		return {}
	min_day = min(dates)
	max_day = max(dates)
	from frappe.utils import add_days

	logs = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": ["in", employees],
			"time": ["between", [f"{min_day} 00:00:00", f"{add_days(max_day, 1)} 00:00:00"]],
		},
		fields=["name", "employee", "log_type", "time", "shift", "attendance"],
		order_by="time asc",
	)
	grouped: dict[tuple, list] = {}
	for log in logs:
		key = (log.employee, getdate(log.time))
		grouped.setdefault(key, []).append(log)
	return grouped


def _fill_hours_from_clock(row: dict) -> None:
	"""If hours were stored as 0, derive them from this row's in/out clocks."""
	from hrms.payroll.daily_pay import _hours_between

	if not flt(row.get("working_hours")):
		if row.get("in_time") and row.get("out_time"):
			hours = _hours_between(row.get("in_time"), row.get("out_time"))
			if hours:
				row["working_hours"] = hours


def _ensure_hours_row_pay(row: dict, holiday_ctx: dict | None = None) -> None:
	"""Fill hour_rate / daily_pay / net so Day View never drops a day's calculations."""
	from hrms.payroll.daily_pay import calculate_holiday_daily_pay, get_hour_rate

	hours = flt(row.get("working_hours"))
	rate = flt(row.get("hour_rate"))
	if not rate and row.get("employee") and row.get("attendance_date"):
		rate = get_hour_rate(row["employee"], row["attendance_date"])
		if rate:
			row["hour_rate"] = rate

	pay = flt(row.get("daily_pay"))
	if not pay and rate and hours:
		status = cstr(row.get("status"))
		kind = row.get("kind")
		if holiday_ctx and kind not in ("pair", "lunch"):
			has_clock = bool(row.get("in_time") or row.get("out_time"))
			worked = status != "Absent" and hours > 0 and has_clock
			pay = calculate_holiday_daily_pay(
				rate, hours if worked else 0, holiday_ctx.get("premium_multiplier") or 0
			)
		elif status not in ("Absent",):
			pay = flt(rate * hours, 2)
		row["daily_pay"] = pay

	if pay and not flt(row.get("net_daily_pay")):
		row["net_daily_pay"] = flt(
			pay - flt(row.get("ss_deduction")) - flt(row.get("tax_deduction")), 2
		)


def _expand_attendance_to_hour_rows(rows: list) -> list:
	"""Turn each Present Attendance into one UI row per IN/OUT pair."""
	from hrms.payroll.daily_pay import _hours_between, get_public_holiday_pay_context, pair_checkin_logs

	if not rows:
		return []

	checkins = _checkins_by_employee_date(rows)
	expanded = []
	for row in rows:
		base = dict(row)
		status = cstr(base.get("status"))
		leave_type = cstr(base.get("leave_type"))
		is_leave_or_absent = status in ("Absent", "On Leave", "Half Day") or bool(leave_type)
		key = (base.get("employee"), getdate(base.get("attendance_date"))) if base.get("attendance_date") else None
		logs = checkins.get(key, []) if key else []
		holiday_ctx = None
		if base.get("employee") and base.get("attendance_date") and not is_leave_or_absent:
			holiday_ctx = get_public_holiday_pay_context(base["employee"], base["attendance_date"])
		# Paid holiday Absent still shows as a single attendance row.
		if status == "Absent" and flt(base.get("daily_pay")):
			is_leave_or_absent = True

		if is_leave_or_absent or not logs:
			base.setdefault("kind", "attendance")
			base.setdefault("in_log", None)
			base.setdefault("out_log", None)
			if not is_leave_or_absent:
				_fill_hours_from_clock(base)
			_ensure_hours_row_pay(base, holiday_ctx)
			expanded.append(base)
			continue

		result = pair_checkin_logs(logs)
		if not result["pairs"]:
			base.setdefault("kind", "attendance")
			base.setdefault("in_log", None)
			base.setdefault("out_log", None)
			_fill_hours_from_clock(base)
			_ensure_hours_row_pay(base, holiday_ctx)
			expanded.append(base)
			continue

		_ensure_hours_row_pay(base, holiday_ctx)
		rate = flt(base.get("hour_rate"))
		attendance_pay = flt(base.get("daily_pay"))
		attendance_net = flt(base.get("net_daily_pay")) or attendance_pay
		day_parts = []
		for index, pair in enumerate(result["pairs"]):
			hours = flt(pair["hours"], 2)
			if not hours:
				hours = _hours_between(pair["in_time"], pair["out_time"]) if pair.get("out_time") else 0.0
			pair_row = dict(base)
			pair_row.update(
				{
					"kind": "pair",
					"in_time": pair["in_time"],
					"out_time": pair["out_time"],
					"working_hours": hours,
					"in_log": pair.get("in_log"),
					"out_log": pair.get("out_log"),
					"daily_pay": flt(rate * hours, 2),
					"ss_deduction": 0,
					"tax_deduction": 0,
					"net_daily_pay": flt(rate * hours, 2),
					"pair_index": index,
				}
			)
			day_parts.append(pair_row)

		# Never drop the day's stored/looked-up gross when splitting into pairs.
		if attendance_pay:
			_redistribute_day_pay(day_parts, attendance_pay, attendance_net)
		expanded.extend(day_parts)

	return expanded


def _redistribute_day_pay(parts: list, attendance_pay: float, attendance_net: float | None = None) -> None:
	"""Scale pair daily_pay so the day totals match Attendance.daily_pay."""
	net_total = flt(attendance_net) if attendance_net is not None else flt(attendance_pay)
	hours_total = sum(flt(p.get("working_hours")) for p in parts)
	if hours_total <= 0:
		if parts:
			parts[0]["daily_pay"] = flt(attendance_pay, 2)
			parts[0]["net_daily_pay"] = flt(net_total, 2)
		return
	allocated = 0.0
	allocated_net = 0.0
	for index, part in enumerate(parts):
		if index == len(parts) - 1:
			pay = flt(attendance_pay - allocated, 2)
			net = flt(net_total - allocated_net, 2)
		else:
			share = flt(part.get("working_hours")) / hours_total
			pay = flt(attendance_pay * share, 2)
			net = flt(net_total * share, 2)
			allocated += pay
			allocated_net += net
		part["daily_pay"] = pay
		part["net_daily_pay"] = net
		part["ss_deduction"] = 0
		part["tax_deduction"] = 0


def _attach_weekly_ss(rows: list) -> list:
	"""SS is a weekly SSB lookup on all clocks that week, not a per-punch amount."""
	from hrms.payroll.daily_pay import _weekly_ss, _weekly_tax, attendance_columns, pay_from_row, week_bounds

	if not rows:
		return rows

	employee_ids = list({row.get("employee") for row in rows if row.get("employee")})
	week_meta = {}
	min_start = None
	max_end = None
	for row in rows:
		if not row.get("employee") or not row.get("attendance_date"):
			row["week_ss"] = 0
			row["week_tax"] = 0
			row["ss_deduction"] = 0
			continue
		start, end = week_bounds(row["attendance_date"])
		key = (row["employee"], start)
		week_meta[key] = {"employee": row["employee"], "start": start, "end": end}
		min_start = start if min_start is None else min(min_start, start)
		max_end = end if max_end is None else max(max_end, end)
		row["week_start"] = str(start)
		row["week_end"] = str(end)

	week_pay = {key: 0.0 for key in week_meta}
	week_company = {}
	if employee_ids and min_start and max_end:
		for rec in frappe.get_all(
			"Attendance",
			filters={
				"employee": ["in", employee_ids],
				"attendance_date": ["between", [min_start, max_end]],
				"docstatus": ["<", 2],
			},
			fields=attendance_columns(
				"employee", "attendance_date", "working_hours", "hour_rate", "daily_pay", "company"
			),
		):
			start, _end = week_bounds(rec.attendance_date)
			key = (rec.employee, start)
			if key not in week_pay:
				continue
			week_pay[key] += pay_from_row(rec)
			week_company[key] = week_company.get(key) or rec.get("company")

	emp_company = {}
	if employee_ids:
		for emp in frappe.get_all(
			"Employee",
			filters={"name": ["in", employee_ids]},
			fields=["name", "company"],
		):
			emp_company[emp.name] = emp.company

	week_ss = {}
	week_tax = {}
	for key, meta in week_meta.items():
		company = week_company.get(key) or emp_company.get(meta["employee"])
		pay = week_pay.get(key, 0.0)
		week_ss[key] = _weekly_ss(
			meta["employee"],
			company,
			pay,
			meta["start"],
			meta["end"],
		)
		week_tax[key] = _weekly_tax(meta["employee"], company, meta["end"], pay)

	for row in rows:
		start = getdate(row["week_start"]) if row.get("week_start") else None
		key = (row.get("employee"), start)
		row["week_ss"] = flt(week_ss.get(key), 2)
		row["week_tax"] = flt(week_tax.get(key), 2)
		row["ss_deduction"] = 0
		row["tax_deduction"] = 0
	return rows


def _sum_hour_buckets(rows: list) -> dict:
	totals = {
		"reg": 0.0,
		"ot": 0.0,
		"dt": 0.0,
		"pto": 0.0,
		"paid": 0.0,
		"unpaid": 0.0,
		"total": 0.0,
		"daily_pay": 0.0,
		"ss_deduction": 0.0,
		"tax_deduction": 0.0,
		"net_daily_pay": 0.0,
	}
	for row in rows:
		for key in totals:
			if key in ("ss_deduction", "tax_deduction", "net_daily_pay"):
				continue
			totals[key] += flt(row.get(key))
	seen = set()
	ss_total = 0.0
	tax_total = 0.0
	for row in rows:
		key = (row.get("employee"), row.get("week_start"))
		if not row.get("week_start") or key in seen:
			continue
		seen.add(key)
		ss_total += flt(row.get("week_ss"))
		tax_total += flt(row.get("week_tax"))
	totals["ss_deduction"] = flt(ss_total, 2)
	totals["tax_deduction"] = flt(tax_total, 2)
	totals["net_daily_pay"] = flt(totals["daily_pay"] - totals["ss_deduction"] - totals["tax_deduction"], 2)
	return {key: flt(value, 2) for key, value in totals.items()}


def _hours_approval_status(rows: list) -> str:
	if not rows:
		return ""
	if "hours_paid" in rows[0]:
		if any(not cint(row.get("hours_paid")) for row in rows):
			return "Not Approved Yet"
		return "Approved"
	if any(cint(row.get("docstatus")) == 0 for row in rows):
		return "Not Approved Yet"
	return "Approved"


@frappe.whitelist()
def get_hours_totals(
	from_date: str | date | None = None,
	to_date: str | date | None = None,
	employee: str | None = None,
	department: str | None = None,
) -> dict:
	frappe.has_permission("Attendance", "read", throw=True)
	if from_date and to_date:
		from hrms.payroll.daily_pay import ensure_paid_holiday_attendance

		ensure_paid_holiday_attendance(from_date, to_date, employee=employee, department=department)
	rows = _decorate_hours_rows(
		_expand_attendance_to_hour_rows(
			frappe.get_list(
				"Attendance",
				fields=_hours_list_fields(),
				filters=_hours_filters(from_date, to_date, employee, department),
				limit=0,
			)
		)
	)
	return _sum_hour_buckets(rows)


@frappe.whitelist()
def get_hours_rows(
	from_date: str | date | None = None,
	to_date: str | date | None = None,
	employee: str | None = None,
	department: str | None = None,
) -> dict:
	frappe.has_permission("Attendance", "read", throw=True)
	if from_date and to_date:
		from hrms.payroll.daily_pay import ensure_paid_holiday_attendance

		ensure_paid_holiday_attendance(from_date, to_date, employee=employee, department=department)
	rows = frappe.get_list(
		"Attendance",
		fields=_hours_list_fields(),
		filters=_hours_filters(from_date, to_date, employee, department),
		order_by="attendance_date desc, employee_name asc",
		limit=500,
	)
	expanded = _expand_attendance_to_hour_rows(rows)
	decorated = _decorate_hours_rows(expanded)
	_attach_hours_row_notes(decorated, [row.name for row in rows])
	return {
		"rows": decorated,
		"totals": _sum_hour_buckets(decorated),
		"approval": _hours_approval_status(decorated),
	}


def _add_hours_comment(name: str, comment: str | None, doctype: str = "Attendance") -> None:
	text = (comment or "").strip()
	if not name or not text:
		return
	# Employees can read their hours but cannot write Attendance, so insert the
	# comment directly instead of going through get_doc + write permission.
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"comment_email": frappe.session.user,
			"comment_by": getattr(frappe.session, "user_fullname", None) or frappe.session.user,
			"reference_doctype": doctype,
			"reference_name": name,
			"content": text,
		}
	).insert(ignore_permissions=True)


def _attach_hours_row_notes(decorated: list, attendance_names: list[str]) -> None:
	comments = _hours_comments_by_attendance(attendance_names)
	adjustments = {}
	if frappe.db.table_exists("Time Clock Adjustment"):
		from hrms.hr.doctype.time_clock_adjustment.time_clock_adjustment import pending_adjustments_for_rows

		adjustments = pending_adjustments_for_rows(decorated)
	seen = set()
	for row in decorated:
		name = row.get("name")
		if name and name not in seen and row.get("kind") != "lunch":
			row["comments"] = comments.get(name, [])
			row["adjustment"] = adjustments.get(name)
			seen.add(name)
		else:
			row["comments"] = []
			row["adjustment"] = None


def _hours_comments_by_attendance(names: list[str]) -> dict[str, list[dict]]:
	if not names:
		return {}
	rows = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": "Attendance",
			"reference_name": ["in", names],
			"comment_type": "Comment",
		},
		fields=["reference_name", "content", "comment_by", "creation", "owner"],
		order_by="creation desc",
	)
	by_name: dict[str, list[dict]] = {}
	for row in rows:
		by_name.setdefault(row.reference_name, []).append(
			{
				"content": strip_html(row.content or "").strip(),
				"comment_by": row.comment_by
				or frappe.db.get_value("User", row.owner, "full_name")
				or row.owner,
				"creation": row.creation,
			}
		)
	return by_name


@frappe.whitelist()
def get_hours_filter_options() -> dict:
	frappe.has_permission("Attendance", "read", throw=True)
	employees = frappe.get_list(
		"Employee",
		fields=["name", "employee_name", "first_name", "last_name", "department", "designation", "user_id"],
		filters={"status": "Active"},
		order_by="employee_name asc",
		limit=500,
	)
	departments = frappe.get_list(
		"Department",
		fields=["name"],
		filters={"is_group": 0},
		order_by="name asc",
		limit=200,
	)
	departments = [
		row
		for row in departments
		if row.name
		and str(row.name) != "All Departments"
		and not str(row.name).startswith("All Departments - ")
	]
	shifts = []
	if frappe.has_permission("Shift Type", "read"):
		shifts = frappe.get_list(
			"Shift Type",
			fields=["name", "start_time", "end_time"],
			order_by="name asc",
			limit=200,
		)
	jobs = []
	seen = set()
	for row in employees:
		if row.designation and row.designation not in seen:
			seen.add(row.designation)
			jobs.append({"name": row.designation})
	if frappe.has_permission("Designation", "read"):
		for row in frappe.get_list("Designation", fields=["name"], order_by="name asc", limit=200):
			if row.name not in seen:
				seen.add(row.name)
				jobs.append({"name": row.name})
	return {"employees": employees, "departments": departments, "shifts": shifts, "jobs": jobs}


def _week_bounds(day: date) -> tuple[date, date]:
	from frappe.utils import get_first_day_of_week

	start = getdate(get_first_day_of_week(day))
	return start, add_days(start, 6)


def _pay_period_bounds(anchor: date) -> tuple[date, date]:
	rows = frappe.get_all(
		"Payroll Entry",
		filters={"start_date": ("<=", anchor), "end_date": (">=", anchor), "docstatus": ("<", 2)},
		fields=["start_date", "end_date"],
		order_by="start_date desc",
		limit=1,
	)
	if rows:
		return getdate(rows[0].start_date), getdate(rows[0].end_date)

	frequency = (
		frappe.db.get_value("Salary Structure", {"docstatus": 1, "is_active": "Yes"}, "payroll_frequency")
		or "Weekly"
	)
	if frequency == "Fortnightly":
		start, _end = _week_bounds(anchor)
		# Align to a two-week block from the most recent payroll entry, else this week + next.
		last = frappe.get_all(
			"Payroll Entry",
			fields=["start_date", "end_date"],
			order_by="start_date desc",
			limit=1,
		)
		if last:
			span = (getdate(last[0].end_date) - getdate(last[0].start_date)).days + 1 or 14
			start = getdate(last[0].start_date)
			while start > anchor:
				start = add_days(start, -span)
			while add_days(start, span - 1) < anchor:
				start = add_days(start, span)
			return start, add_days(start, span - 1)
		return start, add_days(start, 13)
	if frequency == "Monthly":
		return getdate(get_first_day(anchor)), getdate(get_last_day(anchor))
	return _week_bounds(anchor)


@frappe.whitelist()
def get_hours_date_presets() -> dict:
	frappe.has_permission("Attendance", "read", throw=True)
	today = getdate()
	this_week = _week_bounds(today)
	last_week = _week_bounds(add_days(this_week[0], -1))
	current_pay = _pay_period_bounds(today)
	previous_pay = _pay_period_bounds(add_days(current_pay[0], -1))
	return {
		"today": [str(today), str(today)],
		"this_week": [str(this_week[0]), str(this_week[1])],
		"last_week": [str(last_week[0]), str(last_week[1])],
		"this_month": [str(getdate(get_first_day(today))), str(getdate(get_last_day(today)))],
		"current_pay_period": [str(current_pay[0]), str(current_pay[1])],
		"previous_pay_period": [str(previous_pay[0]), str(previous_pay[1])],
	}


def _as_employee_list(employee: str | None, employees: str | list | None) -> list[str]:
	names: list[str] = []
	if employees:
		if isinstance(employees, str):
			employees = frappe.parse_json(employees)
		if isinstance(employees, (list, tuple)):
			names.extend(cstr(name).strip() for name in employees if cstr(name).strip())
	if employee and cstr(employee).strip() and cstr(employee).strip() not in names:
		names.insert(0, cstr(employee).strip())
	if not names:
		frappe.throw(_("Select at least one user."))
	return names


def _signed_adjustment_hours(hours: float | str, direction: str | None) -> float:
	value = flt(hours)
	kind = (direction or "").strip().lower()
	if kind == "deduction":
		value = -abs(value)
	elif kind == "addition":
		value = abs(value)
	if not value:
		frappe.throw(_("Hours cannot be zero."))
	return flt(value, 2)


def _adjustment_comment(
	comment: str | None,
	remarks: str | None,
	mode: str | None,
	adjust_type: str | None,
	job: str | None,
	hours: float,
) -> str:
	note = (comment or remarks or "").strip()
	signed = f"{hours:+.2f}"
	if (mode or "").strip().lower() in ("job", "job_shift", "job&shift"):
		prefix = _("Adjustment (Job&Shift{0}): {1} hours").format(
			f" — {job}" if job else "",
			signed,
		)
	elif adjust_type:
		prefix = _("Adjustment ({0}): {1} hours").format(adjust_type, signed)
	else:
		prefix = _("Adjustment: {0} hours").format(signed)
	return f"{prefix}. {note}" if note else prefix


def _apply_hours_adjustment(
	employee: str, attendance_date: date, hours: float, note: str, shift: str | None = None
) -> str:
	existing = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": attendance_date, "docstatus": ("<", 2)},
		["name", "working_hours"],
		as_dict=True,
	)

	if existing:
		new_hours = flt(existing.working_hours) + hours
		if new_hours < 0:
			new_hours = 0
		values = {"working_hours": flt(new_hours, 2)}
		if shift:
			values["shift"] = shift
		frappe.db.set_value("Attendance", existing.name, values)
		_add_hours_comment(existing.name, note)
		return existing.name

	name = mark_attendance(employee, attendance_date, "Present")
	if not name:
		frappe.throw(_("Could not add hours adjustment. Check for overlapping attendance."))
	values = {"working_hours": flt(max(hours, 0), 2)}
	if shift:
		values["shift"] = shift
	frappe.db.set_value("Attendance", name, values)
	_add_hours_comment(name, note)
	return name


@frappe.whitelist()
def add_hours_adjustment(
	employee: str | None = None,
	attendance_date: str | date | None = None,
	hours: float | str | None = None,
	remarks: str | None = None,
	comment: str | None = None,
	employees: str | list | None = None,
	direction: str | None = None,
	mode: str | None = None,
	job: str | None = None,
	adjust_type: str | None = None,
) -> str | list[str]:
	frappe.has_permission("Attendance", "write", throw=True)
	if not attendance_date:
		frappe.throw(_("Date is required."))

	emp_list = _as_employee_list(employee, employees)
	hours = _signed_adjustment_hours(hours, direction)
	attendance_date = getdate(attendance_date)
	note = _adjustment_comment(comment, remarks, mode, adjust_type, job, hours)
	shift = job if job and frappe.db.exists("Shift Type", job) else None
	created = [_apply_hours_adjustment(emp, attendance_date, hours, note, shift) for emp in emp_list]
	return created[0] if len(created) == 1 else created


@frappe.whitelist()
def add_hours_comment(name: str, comment: str) -> None:
	if not name:
		frappe.throw(_("Attendance is required."))
	doc = frappe.get_doc("Attendance", name)
	doc.check_permission("write")
	if not (comment or "").strip():
		frappe.throw(_("Comment is required."))
	_add_hours_comment(name, comment)


@frappe.whitelist()
def cancel_hours_entry(name: str, in_log: str | None = None, out_log: str | None = None) -> None:
	if not name:
		frappe.throw(_("Attendance is required."))

	doc = frappe.get_doc("Attendance", name)
	employee = doc.employee
	attendance_date = doc.attendance_date

	if in_log or out_log:
		doc.check_permission("write")
		_delete_checkin(in_log)
		_delete_checkin(out_log)
		remaining = _resync_day_hours(employee, attendance_date, attendance_name=name)
		if not remaining:
			return
		return

	if doc.docstatus == 1:
		doc.check_permission("cancel")
		doc.cancel()
		return

	doc.check_permission("delete")
	doc.delete()


def _as_name_list(names) -> list[str]:
	if isinstance(names, str):
		names = frappe.parse_json(names)
	if not isinstance(names, (list, tuple)):
		names = [names]
	out = [cstr(name).strip() for name in names if cstr(name).strip()]
	if not out:
		frappe.throw(_("Select at least one entry."))
	return out


@frappe.whitelist()
def approve_hours_entries(names: str | list) -> dict:
	frappe.has_permission("Attendance", "submit", throw=True)
	approved = []
	for name in _as_name_list(names):
		doc = frappe.get_doc("Attendance", name)
		doc.check_permission("submit")
		if cint(doc.get("hours_paid")):
			continue
		if doc.docstatus == 2:
			continue
		if doc.meta.has_field("hours_paid"):
			if doc.docstatus == 0:
				doc.hours_paid = 1
				doc.submit()
			else:
				frappe.db.set_value("Attendance", name, "hours_paid", 1, update_modified=False)
				doc.hours_paid = 1
		elif doc.docstatus == 0:
			doc.submit()
		approved.append(name)
	return {"approved": approved}


@frappe.whitelist()
def cancel_hours_entries(names: str | list) -> dict:
	removed = []
	for name in _as_name_list(names):
		cancel_hours_entry(name)
		removed.append(name)
	return {"removed": removed}

