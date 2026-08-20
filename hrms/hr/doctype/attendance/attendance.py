# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


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
		self.refresh_daily_pay()

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


@frappe.whitelist()
def get_events(start: date | str, end: date | str, filters: str | list | None = None) -> list[dict]:
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
	if not employee:
		return []

	if isinstance(filters, str):
		import json

		filters = json.loads(filters)
	if not filters:
		filters = []
	filters.append(["attendance_date", "between", [get_datetime(start).date(), get_datetime(end).date()]])
	attendance_records = add_attendance(filters)
	add_holidays(attendance_records, start, end, employee)
	return attendance_records


def add_attendance(filters):
	attendance = frappe.get_list(
		"Attendance",
		fields=[
			"name",
			ValueWrapper("Attendance").as_("doctype"),
			"attendance_date",
			"employee_name",
			"status",
			"docstatus",
		],
		filters=filters,
	)
	for record in attendance:
		record["title"] = f"{record['employee_name']} : {record['status']}"
	return attendance


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


def _replace_existing_attendance(employee: str, attendance_date, shift: str | None = None):
	filters = {
		"employee": employee,
		"attendance_date": getdate(attendance_date),
		"docstatus": ("<", 2),
	}
	if shift:
		filters["shift"] = shift

	existing = frappe.db.get_value("Attendance", filters, ["name", "status", "docstatus"], as_dict=True)
	if not existing:
		return

	if existing.status == "On Leave":
		frappe.throw(
			_("Attendance for {0} on {1} is already marked as On Leave: {2}").format(
				frappe.bold(employee),
				frappe.bold(format_date(attendance_date)),
				get_link_to_form("Attendance", existing.name),
			),
			title=_("Cannot Replace Leave"),
		)

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
	_replace_existing_attendance(employee, attendance_date, shift)

	in_dt = _combine_date_and_time(attendance_date, in_time)
	logs = [_insert_hours_checkin(employee, "IN", in_dt, shift)]
	out_dt = None
	if not working_now:
		out_dt = _combine_date_and_time(attendance_date, out_time)
		if out_dt <= in_dt:
			out_dt += timedelta(days=1)
		logs.append(_insert_hours_checkin(employee, "OUT", out_dt, shift))

	from hrms.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log

	hours = (
		max(flt(time_diff_in_hours(in_dt, now_datetime()), 2), 0)
		if working_now
		else flt(time_diff_in_hours(in_dt, out_dt), 2)
	)
	attendance = mark_attendance_and_link_log(
		logs,
		"Present",
		attendance_date,
		working_hours=hours,
		in_time=in_dt,
		out_time=out_dt,
		shift=shift,
	)
	if not attendance:
		frappe.throw(_("Could not add hours entry. Check for overlapping attendance."))
	_add_hours_comment(attendance.name, comment)
	return attendance.name


@frappe.whitelist()
def add_hours_entries(
	employees,
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
def get_hours_entry(name: str) -> dict:
	if not name:
		frappe.throw(_("Attendance is required."))
	doc = frappe.get_doc("Attendance", name)
	doc.check_permission("read")
	comments = _hours_comments_by_attendance([name]).get(name, [])
	return {
		"name": doc.name,
		"employee": doc.employee,
		"shift": doc.shift,
		"attendance_date": doc.attendance_date,
		"in_time": _clock_str(doc.in_time),
		"out_time": _clock_str(doc.out_time),
		"working_now": 0 if doc.out_time else 1,
		"comment": comments[0]["content"] if comments else "",
	}


@frappe.whitelist()
def update_hours_entry(
	name: str,
	attendance_date: str | date,
	in_time: str,
	out_time: str | None = None,
	shift: str | None = None,
	comment: str | None = None,
	working_now: int | str | None = 0,
) -> str:
	if not name:
		frappe.throw(_("Attendance is required."))
	doc = frappe.get_doc("Attendance", name)
	doc.check_permission("write")
	employee = doc.employee
	if doc.docstatus == 1:
		doc.cancel()
	else:
		doc.delete()
	return add_hours_entry(
		employee,
		attendance_date,
		in_time,
		out_time=out_time,
		shift=shift,
		comment=comment,
		working_now=working_now,
	)


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


def _hours_buckets(row, lwp_map: dict, ot_map: dict) -> dict:
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
	if status == "Absent":
		unpaid = hours or std
		total = unpaid
	elif is_leave:
		pto = hours if hours else (std / 2 if status == "Half Day" else std)
		if is_lwp or not hours_paid:
			unpaid = pto
		else:
			paid = pto
		total = pto
	else:
		reg = max(flt(hours - ot - dt, 2), 0)
		total = hours
		if hours_paid:
			paid = hours
		else:
			unpaid = hours

	job = leave_type or ("Absent" if status == "Absent" else "")
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

	employee_ids = list({row.employee for row in rows if row.employee})
	emp_map = {}
	if employee_ids:
		for emp in frappe.get_all(
			"Employee",
			filters={"name": ["in", employee_ids]},
			fields=["name", "first_name", "last_name", "employee_name"],
		):
			emp_map[emp.name] = emp

	leave_types = list({row.leave_type for row in rows if row.get("leave_type")})
	lwp_map = {}
	if leave_types:
		for leave_type in frappe.get_all(
			"Leave Type",
			filters={"name": ["in", leave_types]},
			fields=["name", "is_lwp"],
		):
			lwp_map[leave_type.name] = cint(leave_type.is_lwp)

	ot_types = list({row.overtime_type for row in rows if row.get("overtime_type")})
	ot_map = {}
	if ot_types:
		for overtime in frappe.get_all(
			"Overtime Type",
			filters={"name": ["in", ot_types]},
			fields=["name", "standard_multiplier"],
		):
			ot_map[overtime.name] = flt(overtime.standard_multiplier)

	decorated = []
	for row in rows:
		data = dict(row)
		data["employee_label"] = _employee_hours_label(emp_map.get(row.employee), row.employee_name)
		data.update(_hours_buckets(row, lwp_map, ot_map))
		decorated.append(data)
	return _attach_weekly_ss(decorated)


def _attach_weekly_ss(rows: list) -> list:
	"""SS is a weekly SSB lookup on all clocks that week, not a per-punch amount."""
	from hrms.payroll.daily_pay import _weekly_ss, attendance_columns, pay_from_row, week_bounds

	if not rows:
		return rows

	employee_ids = list({row.get("employee") for row in rows if row.get("employee")})
	week_meta = {}
	min_start = None
	max_end = None
	for row in rows:
		if not row.get("employee") or not row.get("attendance_date"):
			row["week_ss"] = 0
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
	for key, meta in week_meta.items():
		company = week_company.get(key) or emp_company.get(meta["employee"])
		week_ss[key] = _weekly_ss(
			meta["employee"],
			company,
			week_pay.get(key, 0.0),
			meta["start"],
			meta["end"],
		)

	for row in rows:
		start = getdate(row["week_start"]) if row.get("week_start") else None
		key = (row.get("employee"), start)
		row["week_ss"] = flt(week_ss.get(key), 2)
		row["ss_deduction"] = 0
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
			if key == "ss_deduction":
				continue
			totals[key] += flt(row.get(key))
	seen = set()
	ss_total = 0.0
	for row in rows:
		key = (row.get("employee"), row.get("week_start"))
		if not row.get("week_start") or key in seen:
			continue
		seen.add(key)
		ss_total += flt(row.get("week_ss"))
	totals["ss_deduction"] = flt(ss_total, 2)
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
	rows = _decorate_hours_rows(
		frappe.get_list(
			"Attendance",
			fields=_hours_list_fields(),
			filters=_hours_filters(from_date, to_date, employee, department),
			limit=0,
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
	rows = frappe.get_list(
		"Attendance",
		fields=_hours_list_fields(),
		filters=_hours_filters(from_date, to_date, employee, department),
		order_by="attendance_date desc, employee_name asc",
		limit=500,
	)
	comments = _hours_comments_by_attendance([row.name for row in rows])
	decorated = _decorate_hours_rows(rows)
	for row in decorated:
		row["comments"] = comments.get(row["name"], [])
	return {
		"rows": decorated,
		"totals": _sum_hour_buckets(decorated),
		"approval": _hours_approval_status(decorated),
	}


def _add_hours_comment(name: str, comment: str | None, doctype: str = "Attendance") -> None:
	text = (comment or "").strip()
	if not name or not text:
		return
	frappe.get_doc(doctype, name).add_comment("Comment", text)


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
	departments = frappe.get_list("Department", fields=["name"], order_by="name asc", limit=200)
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
def cancel_hours_entry(name: str) -> None:
	if not name:
		frappe.throw(_("Attendance is required."))

	doc = frappe.get_doc("Attendance", name)
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
def approve_hours_entries(names) -> dict:
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
def cancel_hours_entries(names) -> dict:
	removed = []
	for name in _as_name_list(names):
		cancel_hours_entry(name)
		removed.append(name)
	return {"removed": removed}

