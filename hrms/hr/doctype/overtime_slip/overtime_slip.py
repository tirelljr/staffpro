# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils.data import get_link_to_form, getdate

from hrms.payroll.doctype.payroll_entry.payroll_entry import get_start_end_dates
from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
	get_assigned_salary_structure,
)

DEFAULT_OVERTIME_THRESHOLD_HOURS = 80.0
DEFAULT_OVERTIME_PAY_MULTIPLIER = 1.5
REGULAR_DAY_HOURS = 8.0


def get_employee_overtime_threshold(employee: str) -> float:
	"""Return the employee override, falling back to the HR-wide default."""
	employee_threshold = None
	employee_meta = frappe.get_meta("Employee")
	if employee_meta.has_field("overtime_threshold_hours"):
		employee_threshold = frappe.db.get_value("Employee", employee, "overtime_threshold_hours")
	if employee_threshold not in (None, "") and flt(employee_threshold) > 0:
		return flt(employee_threshold)

	global_threshold = None
	if frappe.get_meta("HR Settings").has_field("overtime_threshold_hours"):
		global_threshold = frappe.db.get_single_value("HR Settings", "overtime_threshold_hours")
	if global_threshold in (None, "") or flt(global_threshold) <= 0:
		global_threshold = DEFAULT_OVERTIME_THRESHOLD_HOURS
	return flt(global_threshold)


def get_overtime_pay_multiplier() -> float:
	value = None
	if frappe.get_meta("HR Settings").has_field("overtime_pay_multiplier"):
		value = frappe.db.get_single_value("HR Settings", "overtime_pay_multiplier")
	if value in (None, ""):
		value = DEFAULT_OVERTIME_PAY_MULTIPLIER
	return max(flt(value), 0.0)


def ordinary_overtime_hours(day_hours, hours_before: float, threshold: float) -> float:
	"""Hours on this day that sit past the pay-period threshold (default 80)."""
	day_hours = flt(day_hours)
	period_over = max(flt(hours_before) + day_hours - flt(threshold), 0.0)
	return flt(min(day_hours, period_over), 2)


def get_pay_period_overtime(
	employee: str,
	start_date,
	end_date,
	*,
	ensure_holidays: bool = True,
) -> dict:
	"""Hours past the pay-period threshold (10 working days / 80 hours by default)."""
	from hrms.payroll.daily_pay import (
		ensure_paid_holiday_attendance,
		ensure_working_hours_from_times,
		get_public_holiday_pay_context,
	)

	start_date = getdate(start_date)
	end_date = getdate(end_date)
	if ensure_holidays:
		ensure_paid_holiday_attendance(start_date, end_date, employee=employee)

	fields = ["name", "attendance_date", "working_hours", "status"]
	attendance_meta = frappe.get_meta("Attendance")
	for fieldname in ("in_time", "out_time", "daily_pay"):
		if attendance_meta.has_field(fieldname):
			fields.append(fieldname)

	rows = frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"attendance_date": ("between", [start_date, end_date]),
			"docstatus": ("<", 2),
		},
		fields=fields,
		order_by="attendance_date asc, creation asc, name asc",
	)

	threshold = get_employee_overtime_threshold(employee)
	running_hours = 0.0
	allocations = []
	ordinary_overtime = 0.0
	holiday_overtime = 0.0
	period_hours = 0.0

	for row in rows:
		row_date = getdate(row.attendance_date)
		is_holiday = bool(get_public_holiday_pay_context(employee, row_date))
		if (row.status or "") == "On Leave":
			continue
		if (row.status or "") == "Absent" and not is_holiday:
			continue
		hours = flt(row.working_hours) or flt(ensure_working_hours_from_times(row))
		if is_holiday and hours <= 0 and flt(row.get("daily_pay")) > 0:
			hours = REGULAR_DAY_HOURS
		if hours <= 0:
			continue

		if is_holiday:
			before = max(running_hours - threshold, 0.0)
			running_hours += hours
			overtime_duration = flt(max(running_hours - threshold, 0.0) - before, 2)
		else:
			overtime_duration = ordinary_overtime_hours(hours, running_hours, threshold)
			running_hours += hours

		period_hours += hours
		if overtime_duration <= 0:
			continue

		if is_holiday:
			holiday_overtime += overtime_duration
		else:
			ordinary_overtime += overtime_duration
		allocations.append(
			{
				"reference_document": row.name,
				"date": row.attendance_date,
				"overtime_duration": overtime_duration,
				"is_holiday": is_holiday,
			}
		)

	return {
		"employee": employee,
		"start_date": start_date,
		"end_date": end_date,
		"threshold_hours": threshold,
		"total_hours": flt(period_hours, 2),
		"total_overtime_duration": flt(ordinary_overtime + holiday_overtime, 2),
		"ordinary_overtime_duration": flt(ordinary_overtime, 2),
		"holiday_overtime_duration": flt(holiday_overtime, 2),
		"allocations": allocations,
	}


class OvertimeSlip(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from hrms.hr.doctype.overtime_details.overtime_details import OvertimeDetails

		amended_from: DF.Link | None
		company: DF.Link
		department: DF.Link | None
		employee: DF.Link
		employee_name: DF.Data | None
		end_date: DF.Date
		overtime_details: DF.Table[OvertimeDetails]
		payroll_entry: DF.Link | None
		posting_date: DF.Date
		salary_slip: DF.Link | None
		start_date: DF.Date
		submitted_via_payroll_entry: DF.Check
		total_overtime_duration: DF.Float
	# end: auto-generated types

	def validate(self):
		if not self.start_date or not self.end_date:
			self.get_frequency_and_dates()

		if self.start_date > self.end_date:
			frappe.throw(_("Start date cannot be greater than end date"))

		self.validate_overlap()
		self.total_overtime_duration = flt(
			sum(flt(detail.overtime_duration) for detail in self.overtime_details), 2
		)

	def on_submit(self):
		"""Overtime slips are audit records; payroll handles payment directly."""

	def validate_overlap(self):
		overtime_slips = frappe.db.get_all(
			"Overtime Slip",
			filters={
				"docstatus": ("!=", 2),
				"employee": self.employee,
				"end_date": (">=", self.start_date),
				"start_date": ("<=", self.end_date),
				"name": ("!=", self.name),
			},
		)
		if len(overtime_slips):
			form_link = get_link_to_form("Overtime Slip", overtime_slips[0].name)
			msg = _("Overtime Slip:{0} has been created between {1} and {2}").format(
				bold(form_link), bold(self.start_date), bold(self.end_date)
			)
			frappe.throw(msg)

	@frappe.whitelist()
	def get_frequency_and_dates(self):
		date = self.posting_date

		salary_structure = get_assigned_salary_structure(self.employee, date)
		if salary_structure:
			payroll_frequency = frappe.db.get_value("Salary Structure", salary_structure, "payroll_frequency")
			date_details = get_start_end_dates(
				payroll_frequency, date, frappe.db.get_value("Employee", self.employee, "company")
			)
			self.start_date = date_details.start_date
			self.end_date = date_details.end_date
		else:
			frappe.throw(
				_("Salary Structure not assigned for employee {0} for date {1}").format(
					self.employee, self.start_date
				)
			)

	@frappe.whitelist()
	def get_emp_and_overtime_details(self):
		result = get_pay_period_overtime(self.employee, self.start_date, self.end_date)
		self.overtime_details = []
		for allocation in result["allocations"]:
			self.append(
				"overtime_details",
				{
					"reference_document": allocation["reference_document"],
					"date": allocation["date"],
					"overtime_duration": allocation["overtime_duration"],
				},
			)
		self.total_overtime_duration = result["total_overtime_duration"]
		if not self.overtime_details:
			frappe.throw(
				_("No overtime found for employee {0} between {1} and {2}").format(
					self.employee, self.start_date, self.end_date
				)
			)
		self.save()


def filter_employees_for_overtime_slip_creation(start_date, end_date, employees, limit=None):
	if not employees:
		return []

	if not isinstance(employees, list):
		employees = json.loads(employees)

	OvertimeSlip = frappe.qb.DocType("Overtime Slip")
	employees_with_overtime = [
		employee
		for employee in employees
		if get_pay_period_overtime(employee, start_date, end_date)["total_overtime_duration"] > 0
	]
	if not employees_with_overtime:
		return []

	# exclude employees who already have overtime slips for this period
	employees_with_existing_overtime_slips = (
		frappe.qb.from_(OvertimeSlip)
		.select(OvertimeSlip.employee)
		.distinct()
		.where(
			(OvertimeSlip.employee.isin(employees_with_overtime))
			& (OvertimeSlip.docstatus != 2)
			& (OvertimeSlip.start_date <= end_date)
			& (OvertimeSlip.end_date >= start_date)
		)
	).run(pluck=True)

	# Get eligible employees (those with overtime attendance but no existing slips)
	existing = set(employees_with_existing_overtime_slips)
	eligible_employees = [
		employee for employee in employees_with_overtime if employee not in existing
	]

	return eligible_employees[:limit] if limit else eligible_employees


def create_overtime_slips_for_employees(employees, args):
	count = 0
	errors = []
	for emp in employees:
		emp_args = args.copy()
		relieving_date = frappe.db.get_value("Employee", emp, "relieving_date")
		relieving_date = getdate(relieving_date) if relieving_date else None
		if relieving_date and relieving_date < getdate(emp_args.get("end_date")):
			emp_args["start_date"] = getdate(emp_args.get("start_date"))
			emp_args["end_date"] = relieving_date
		emp_args.update({"doctype": "Overtime Slip", "employee": emp})
		try:
			frappe.get_doc(emp_args).get_emp_and_overtime_details()
			count += 1
		except Exception as e:
			frappe.clear_last_message()
			errors.append(_("Employee {0} : {1}").format(emp, str(e)))
			frappe.log_error(frappe.get_traceback(), _("Overtime Slip Creation Error for {0}").format(emp))

	if count:
		frappe.msgprint(
			_("Overtime Slip created for {0} employee(s)").format(count),
			indicator="green",
			title=_("Overtime Slips Created"),
		)
	if errors:
		error_list_html = "".join(f"<li>{err}</li>" for err in errors)
		frappe.msgprint(
			title=_("Overtime Slip Creation Failed"),
			msg=f"<ul>{error_list_html}</ul>",
			indicator="red",
		)

	status = "Failed" if errors else "Draft"
	frappe.get_doc("Payroll Entry", args.get("payroll_entry")).db_set({"status": status})
	frappe.publish_realtime("completed_overtime_slip_creation", user=frappe.session.user)


def submit_overtime_slips_for_employees(overtime_slips, payroll_entry):
	count = 0
	errors = []
	for overtime_slip in overtime_slips:
		try:
			doc = frappe.get_doc("Overtime Slip", overtime_slip)
			doc.submitted_via_payroll_entry = 1
			doc.submit()
			count += 1
		except Exception as e:
			frappe.clear_last_message()
			errors.append(_("{0} : {1}").format(overtime_slip, str(e)))
			frappe.log_error(
				frappe.get_traceback(), _("Overtime Slip Submission Error for {0}").format(overtime_slip)
			)
	if count:
		frappe.msgprint(
			_("Overtime Slips submitted for {0} employee(s)").format(count),
			indicator="green",
			title=_("Overtime Slip Submitted"),
		)
	if errors:
		error_list_html = "".join(f"<li>{err}</li>" for err in errors)
		frappe.msgprint(
			title=_("Overtime Slip Submission Failed"),
			msg=_(f"<ul>{error_list_html}</ul>"),
			indicator="red",
		)

	status = "Failed" if errors else "Draft"
	payroll_entry = frappe.get_doc("Payroll Entry", payroll_entry).db_set({"status": status})
	frappe.publish_realtime("completed_overtime_slip_submission", user=frappe.session.user)
