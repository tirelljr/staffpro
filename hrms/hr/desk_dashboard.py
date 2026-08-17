# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, flt, formatdate, get_first_day, get_last_day, getdate

from erpnext.accounts.utils import build_qb_match_conditions

PERIOD_DAYS = {
	"weekly": 7,
	"monthly": 30,
	"yearly": 365,
}

FALLBACK_LIMIT = 5
PAYROLL_LIMIT = 8


@frappe.whitelist()
def get_upcoming_celebrations(
	period: str = "weekly", company: str | None = None, event_type: str | None = None
) -> dict:
	"""Return upcoming employee birthdays and work anniversaries for the desk dashboard."""
	company = company or frappe.defaults.get_user_default("Company")
	if not company:
		return {"events": [], "fallback": False}

	days = PERIOD_DAYS.get(period, PERIOD_DAYS["weekly"])
	today = getdate()
	end_date = add_days(today, days - 1)

	employees = _get_active_employees(company)
	all_events = _collect_employee_events(employees, today)

	if event_type and event_type != "all":
		all_events = [event for event in all_events if event["event_type"] == event_type]

	period_events = [event for event in all_events if today <= event["event_date"] <= end_date]
	if period_events:
		return {"events": period_events, "fallback": False}

	future_events = [event for event in all_events if event["event_date"] > end_date]
	return {
		"events": future_events[:FALLBACK_LIMIT],
		"fallback": bool(future_events),
	}


@frappe.whitelist()
def get_upcoming_payroll(period: str = "monthly", company: str | None = None) -> dict:
	"""Return agent payroll rows for the People dashboard panel."""
	company = company or frappe.defaults.get_user_default("Company")
	if not company:
		return {"rows": [], "period_label": "", "start_date": None, "end_date": None}

	start_date, end_date = _payroll_period_bounds(period)
	rows = _get_payroll_rows(company, start_date, end_date)
	return {
		"rows": rows[:PAYROLL_LIMIT],
		"period_label": _payroll_period_label(start_date, end_date),
		"start_date": start_date,
		"end_date": end_date,
	}


def _payroll_period_bounds(period: str):
	today = getdate()
	if period == "weekly":
		start_date = add_days(today, -today.weekday())
		end_date = add_days(start_date, 6)
		return start_date, end_date

	if period == "yearly":
		start_date = getdate(f"{today.year}-01-01")
		end_date = getdate(f"{today.year}-12-31")
		return start_date, end_date

	start_date = get_first_day(today)
	end_date = get_last_day(today)
	return start_date, end_date


def _payroll_period_label(start_date, end_date):
	if start_date.month == end_date.month and start_date.year == end_date.year:
		return start_date.strftime("%B %Y")
	return f"{formatdate(start_date)} – {formatdate(end_date)}"


def _get_payroll_rows(company, start_date, end_date):
	salary_slip = frappe.qb.DocType("Salary Slip")
	employee = frappe.qb.DocType("Employee")

	slips = (
		frappe.qb.from_(salary_slip)
		.left_join(employee)
		.on(salary_slip.employee == employee.name)
		.select(
			salary_slip.name,
			salary_slip.employee,
			salary_slip.employee_name,
			salary_slip.end_date,
			salary_slip.net_pay,
			salary_slip.currency,
			salary_slip.total_working_hours,
			salary_slip.payment_days,
			salary_slip.status,
			salary_slip.docstatus,
			salary_slip.journal_entry,
			employee.designation,
			employee.department,
			employee.image,
			employee.company_email,
			employee.personal_email,
		)
		.where(salary_slip.company == company)
		.where(salary_slip.start_date <= end_date)
		.where(salary_slip.end_date >= start_date)
		.where(salary_slip.docstatus != 2)
		.orderby(salary_slip.end_date, order=frappe.qb.desc)
		.orderby(salary_slip.employee_name)
	).run(as_dict=True)

	rows = []
	seen_employees = set()

	for slip in slips:
		if slip.employee in seen_employees:
			continue
		seen_employees.add(slip.employee)
		rows.append(_build_payroll_row(slip, start_date, end_date))

	if rows:
		return rows

	employees = _get_active_employees(company)
	hours_by_employee = _attendance_hours_by_employee(company, start_date, end_date)
	currency = frappe.db.get_value("Company", company, "default_currency")

	for emp in employees:
		rows.append(
			{
				"employee": emp.name,
				"employee_name": emp.employee_name,
				"subtitle": _employee_subtitle(emp),
				"image": emp.image,
				"hours_worked": flt(hours_by_employee.get(emp.name)),
				"net_pay": None,
				"currency": currency,
				"pay_date": end_date,
				"pay_date_label": formatdate(end_date),
				"status": "pending",
				"status_label": _("Pending"),
				"salary_slip": None,
			}
		)

	rows.sort(key=lambda row: (-row["hours_worked"], row["employee_name"].lower()))
	return rows


def _build_payroll_row(slip, start_date, end_date):
	hours = flt(slip.total_working_hours)
	if not hours and slip.payment_days:
		hours = flt(slip.payment_days) * 8

	status, status_label = _payroll_status(slip)
	email = slip.company_email or slip.personal_email or ""
	subtitle = _employee_subtitle(slip)
	if email:
		subtitle = email

	return {
		"employee": slip.employee,
		"employee_name": slip.employee_name,
		"subtitle": subtitle,
		"image": slip.image,
		"hours_worked": hours,
		"net_pay": flt(slip.net_pay),
		"currency": slip.currency,
		"pay_date": slip.end_date or end_date,
		"pay_date_label": formatdate(slip.end_date or end_date),
		"status": status,
		"status_label": status_label,
		"salary_slip": slip.name,
	}


def _payroll_status(slip):
	if slip.docstatus == 0 or slip.status == "Draft":
		return "pending", _("Pending")
	if slip.journal_entry:
		return "paid", _("Paid")
	if slip.status == "Submitted":
		return "ready", _("Ready")
	if slip.status == "Withheld":
		return "pending", _("Withheld")
	return "pending", _("Pending")


def _attendance_hours_by_employee(company, start_date, end_date):
	attendance = frappe.qb.DocType("Attendance")
	rows = (
		frappe.qb.from_(attendance)
		.select(attendance.employee, Sum(attendance.working_hours).as_("hours"))
		.where(attendance.company == company)
		.where(attendance.docstatus == 1)
		.where(attendance.attendance_date.between(start_date, end_date))
		.where(attendance.status.isin(["Present", "Half Day", "Work From Home"]))
		.groupby(attendance.employee)
	).run(as_dict=True)

	return {row.employee: flt(row.hours) for row in rows}


def _employee_subtitle(employee):
	subtitle = employee.designation or ""
	if employee.designation and employee.department:
		return _("{0} in {1}").format(employee.designation, employee.department)
	if employee.department:
		return employee.department
	return subtitle


def _collect_employee_events(employees, today):
	events = []

	for employee in employees:
		if employee.date_of_birth:
			event_date = _next_occurrence(employee.date_of_birth, today)
			if event_date >= today:
				events.append(
					_build_event(
						employee,
						event_type="birthday",
						event_date=event_date,
					)
				)

		if employee.date_of_joining:
			event_date = _next_occurrence(employee.date_of_joining, today)
			if event_date >= today and event_date.year > employee.date_of_joining.year:
				events.append(
					_build_event(
						employee,
						event_type="anniversary",
						event_date=event_date,
						years_completed=event_date.year - employee.date_of_joining.year,
					)
				)

	events.sort(key=lambda row: (row["event_date"], row["employee_name"].lower()))
	return events


def _get_active_employees(company):
	employee = frappe.qb.DocType("Employee")
	return (
		frappe.qb.from_(employee)
		.select(
			employee.name,
			employee.employee_name,
			employee.date_of_birth,
			employee.date_of_joining,
			employee.designation,
			employee.department,
			employee.image,
		)
		.where(employee.company == company)
		.where(employee.status == "Active")
		.where(Criterion.all(build_qb_match_conditions("Employee")))
	).run(as_dict=True)


def _next_occurrence(source_date, from_date):
	for year in (from_date.year, from_date.year + 1):
		try:
			candidate = source_date.replace(year=year)
		except ValueError:
			candidate = source_date.replace(year=year, day=28)

		if candidate >= from_date:
			return candidate

	return source_date.replace(year=from_date.year + 1)


def _build_event(employee, event_type, event_date, years_completed=None):
	subtitle = employee.designation or ""
	if employee.designation and employee.department:
		subtitle = _("{0} in {1}").format(employee.designation, employee.department)
	elif employee.department:
		subtitle = employee.department

	event = {
		"employee": employee.name,
		"employee_name": employee.employee_name,
		"subtitle": subtitle,
		"image": employee.image,
		"event_type": event_type,
		"event_date": event_date,
		"day": event_date.day,
		"month": event_date.strftime("%b"),
	}

	if event_type == "birthday":
		event["event_label"] = _("Birthday")
		event["event_icon"] = "birthday"
	elif event_type == "anniversary":
		event["event_label"] = _("Work Anniversary")
		event["event_icon"] = "anniversary"
		event["years_completed"] = years_completed

	return event
