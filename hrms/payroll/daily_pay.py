# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Daily pay, social security, and tax estimates on time tracking."""

from __future__ import annotations

from datetime import date

import frappe
from frappe.utils import cint, flt, get_first_day_of_week, getdate, time_diff_in_hours

from hrms.payroll.social_security import calculate_contribution, get_active_contribution_table

HOURS_PER_PERIOD = {
	"Daily": 8.0,
	"Weekly": 40.0,
	"Fortnightly": 80.0,
	"Bimonthly": 86.67,
	"Monthly": 173.33,
}

PAYROLL_FIELDS = ("hour_rate", "daily_pay", "ss_deduction", "tax_deduction", "net_daily_pay", "hours_paid")


def attendance_has_payroll_fields() -> bool:
	return frappe.db.has_column("Attendance", "daily_pay") and frappe.db.has_column("Attendance", "hour_rate")


def attendance_columns(*names) -> list[str]:
	return [name for name in names if name == "name" or frappe.db.has_column("Attendance", name)]


def pay_from_row(row) -> float:
	data = row if isinstance(row, dict) else {}
	pay = flt(data.get("daily_pay"))
	if pay:
		return pay
	hours = flt(data.get("working_hours"))
	rate = flt(data.get("hour_rate"))
	if not rate and data.get("employee") and data.get("attendance_date"):
		rate = get_hour_rate(data.get("employee"), data.get("attendance_date"))
	return flt(rate * hours, 2)


def week_bounds(day) -> tuple[date, date]:
	start = getdate(get_first_day_of_week(day))
	from frappe.utils import add_days

	return start, add_days(start, 6)


def get_assignment(employee: str, on_date):
	if not employee or not on_date:
		return None
	rows = frappe.get_all(
		"Salary Structure Assignment",
		filters={"employee": employee, "docstatus": 1, "from_date": ("<=", getdate(on_date))},
		fields=["name", "salary_structure", "base", "income_tax_slab", "company"],
		order_by="from_date desc",
		limit=1,
	)
	return rows[0] if rows else None


def get_hour_rate(employee: str, on_date) -> float:
	assignment = get_assignment(employee, on_date)
	if not assignment:
		return 0.0

	hour_rate = 0.0
	frequency = "Weekly"
	base = flt(assignment.base)
	if assignment.salary_structure and frappe.db.exists("Salary Structure", assignment.salary_structure):
		structure = frappe.get_cached_doc("Salary Structure", assignment.salary_structure)
		hour_rate = flt(structure.hour_rate)
		frequency = structure.payroll_frequency or frequency

	if hour_rate:
		return flt(hour_rate, 6)

	period_hours = HOURS_PER_PERIOD.get(frequency, 40.0)
	if base and period_hours:
		return flt(base / period_hours, 6)
	return 0.0


def _weekly_ss(employee: str, company: str | None, week_pay: float, week_start, week_end) -> float:
	if week_pay <= 0:
		return 0.0

	table = get_active_contribution_table(company, week_end)
	bands = None
	injury_employee = 0.0
	injury_employer = 2.60
	if table:
		bands = table.get("bands") or None
		injury_employee = flt(table.get("injury_only_employee_amount"))
		injury_employer = flt(table.get("injury_only_employer_amount"))

	emp_fields = ["date_of_birth"]
	if frappe.get_meta("Employee").has_field("receiving_ss_benefit"):
		emp_fields.append("receiving_ss_benefit")
	emp = frappe.db.get_value("Employee", employee, emp_fields, as_dict=True) or {}
	result = calculate_contribution(
		week_pay,
		"Weekly",
		week_start,
		week_end,
		date_of_birth=emp.get("date_of_birth"),
		receiving_ss_benefit=bool(emp.get("receiving_ss_benefit")),
		bands=bands,
		injury_only_employee_amount=injury_employee,
		injury_only_employer_amount=injury_employer,
	)
	return flt(result.get("employee_amount"), 2)


def _weekly_tax(employee: str, company: str | None, on_date, week_pay: float) -> float:
	if week_pay <= 0:
		return 0.0
	assignment = get_assignment(employee, on_date)
	slab_name = assignment.income_tax_slab if assignment else None
	if not slab_name:
		return 0.0

	from hrms.payroll.doctype.income_tax_slab.income_tax_slab import calculate_tax_by_tax_slab

	tax_slab = frappe.get_cached_doc("Income Tax Slab", slab_name)
	annual = flt(week_pay) * 52.0
	annual_tax, _other = calculate_tax_by_tax_slab(annual, tax_slab)
	return flt(flt(annual_tax) / 52.0, 2)


def week_attendance_rows(employee: str, on_date) -> list[dict]:
	start, end = week_bounds(on_date)
	fields = attendance_columns(
		"name", "attendance_date", "working_hours", "daily_pay", "hour_rate", "company"
	)
	return frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"attendance_date": ["between", [start, end]],
			"docstatus": ["<", 2],
		},
		fields=fields,
		order_by="attendance_date asc",
	)


def apply_daily_pay_to_doc(doc) -> None:
	"""Set hour rate and daily pay on a single Attendance doc."""
	if not attendance_has_payroll_fields():
		return
	if not doc.employee or not doc.attendance_date:
		return
	if (doc.status or "") == "Absent":
		doc.hour_rate = get_hour_rate(doc.employee, doc.attendance_date)
		doc.daily_pay = 0
		doc.ss_deduction = 0
		doc.tax_deduction = 0
		doc.net_daily_pay = 0
		return

	doc.hour_rate = get_hour_rate(doc.employee, doc.attendance_date)
	doc.daily_pay = flt(flt(doc.hour_rate) * flt(doc.working_hours), 2)


def allocate_week_deductions(employee: str, on_date, overlay: dict | None = None) -> None:
	"""Spread this week's SS and tax across the employee's attendance rows."""
	if not attendance_has_payroll_fields() or not employee or not on_date:
		return
	if frappe.flags.in_daily_pay_alloc:
		return

	frappe.flags.in_daily_pay_alloc = True
	try:
		start, end = week_bounds(on_date)
		rows = week_attendance_rows(employee, on_date)
		overlay = overlay or {}
		company = None
		week_pay = 0.0
		for row in rows:
			if row.name in overlay:
				row.update(overlay[row.name])
			week_pay += flt(row.get("daily_pay"))
			company = company or row.get("company")

		if not company:
			company = frappe.db.get_value("Employee", employee, "company")

		week_ss = _weekly_ss(employee, company, week_pay, start, end)
		week_tax = _weekly_tax(employee, company, on_date, week_pay)

		for row in rows:
			pay = flt(row.get("daily_pay"))
			share = (pay / week_pay) if week_pay else 0.0
			ss_amount = flt(week_ss * share, 2)
			tax_amount = flt(week_tax * share, 2)
			values = {
				"ss_deduction": ss_amount,
				"tax_deduction": tax_amount,
				"net_daily_pay": flt(pay - ss_amount - tax_amount, 2),
			}
			if overlay.get(row.name):
				continue
			frappe.db.set_value("Attendance", row.name, values, update_modified=False)
	finally:
		frappe.flags.in_daily_pay_alloc = False


def refresh_attendance_payroll(doc) -> dict:
	"""Apply pay + this day's share of weekly SS/tax onto `doc`."""
	apply_daily_pay_to_doc(doc)
	if not attendance_has_payroll_fields() or (doc.status or "") == "Absent":
		return {
			"hour_rate": flt(getattr(doc, "hour_rate", 0)),
			"daily_pay": 0.0,
			"ss_deduction": 0.0,
			"tax_deduction": 0.0,
			"net_daily_pay": 0.0,
		}

	start, end = week_bounds(doc.attendance_date)
	rows = week_attendance_rows(doc.employee, doc.attendance_date)
	week_pay = 0.0
	company = doc.company
	for row in rows:
		pay = flt(doc.daily_pay) if row.name == doc.name else flt(row.get("daily_pay"))
		week_pay += pay
		company = company or row.get("company")

	if not any(row.name == doc.name for row in rows):
		week_pay += flt(doc.daily_pay)

	week_ss = _weekly_ss(doc.employee, company, week_pay, start, end)
	week_tax = _weekly_tax(doc.employee, company, doc.attendance_date, week_pay)
	pay = flt(doc.daily_pay)
	share = (pay / week_pay) if week_pay else 0.0
	doc.ss_deduction = flt(week_ss * share, 2)
	doc.tax_deduction = flt(week_tax * share, 2)
	doc.net_daily_pay = flt(pay - flt(doc.ss_deduction) - flt(doc.tax_deduction), 2)
	return {
		"hour_rate": flt(doc.hour_rate),
		"daily_pay": pay,
		"ss_deduction": flt(doc.ss_deduction),
		"tax_deduction": flt(doc.tax_deduction),
		"net_daily_pay": flt(doc.net_daily_pay),
	}


def on_attendance_validate(doc, method=None):
	refresh_attendance_payroll(doc)


def on_attendance_update(doc, method=None):
	if frappe.flags.in_daily_pay_alloc:
		return
	if not attendance_has_payroll_fields():
		return
	allocate_week_deductions(
		doc.employee,
		doc.attendance_date,
		overlay={
			doc.name: {
				"daily_pay": flt(doc.daily_pay),
				"company": doc.company,
			}
		},
	)


def _hours_from_logs(logs: list[dict]) -> tuple:
	ins = [row for row in logs if (row.log_type or "IN") == "IN"]
	outs = [row for row in logs if row.log_type == "OUT"]
	in_time = ins[0].time if ins else None
	out_time = outs[-1].time if outs else None
	hours = flt(time_diff_in_hours(in_time, out_time), 2) if in_time and out_time else 0.0
	return in_time, out_time, hours


def sync_attendance_from_checkin(checkin) -> str | None:
	"""Create or update today's attendance when an agent punches, then recalc pay."""
	if not checkin or not checkin.employee or not checkin.time:
		return None
	if frappe.flags.in_daily_pay_sync:
		return getattr(checkin, "attendance", None)

	day = getdate(checkin.time)
	existing = checkin.attendance or frappe.db.get_value(
		"Attendance",
		{"employee": checkin.employee, "attendance_date": day, "docstatus": ("<", 2)},
		"name",
	)
	logs = frappe.get_all(
		"Employee Checkin",
		filters={"employee": checkin.employee, "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
		fields=["log_type", "time", "shift"],
		order_by="time asc",
	)
	in_time, out_time, hours = _hours_from_logs(logs)
	shift = checkin.shift or (logs[0].shift if logs else None)

	frappe.flags.in_daily_pay_sync = True
	try:
		if existing:
			doc = frappe.get_doc("Attendance", existing)
			if doc.docstatus == 2:
				return existing
			updates = {
				"in_time": in_time,
				"out_time": out_time,
				"working_hours": hours or doc.working_hours,
			}
			if shift and not doc.shift:
				updates["shift"] = shift
			if doc.docstatus == 1:
				frappe.db.set_value("Attendance", existing, updates, update_modified=False)
				doc.reload()
				refresh_attendance_payroll(doc)
				frappe.db.set_value(
					"Attendance",
					existing,
					{
						"hour_rate": doc.hour_rate,
						"daily_pay": doc.daily_pay,
						"ss_deduction": doc.ss_deduction,
						"tax_deduction": doc.tax_deduction,
						"net_daily_pay": doc.net_daily_pay,
					},
					update_modified=False,
				)
				allocate_week_deductions(doc.employee, doc.attendance_date)
			else:
				doc.update(updates)
				doc.save(ignore_permissions=True)
			if not checkin.attendance:
				frappe.db.set_value("Employee Checkin", checkin.name, "attendance", existing, update_modified=False)
			return existing

		doc = frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": checkin.employee,
				"attendance_date": day,
				"status": "Present",
				"in_time": in_time,
				"out_time": out_time,
				"working_hours": hours,
				"shift": shift,
				"hours_paid": 0,
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("Employee Checkin", checkin.name, "attendance", doc.name, update_modified=False)
		return doc.name
	finally:
		frappe.flags.in_daily_pay_sync = False


def on_employee_checkin(doc, method=None):
	if frappe.flags.in_test and not frappe.flags.get("apply_daily_pay"):
		return
	if cint(getattr(doc, "skip_auto_attendance", 0)):
		return
	try:
		sync_attendance_from_checkin(doc)
	except Exception:
		frappe.log_error(title="Daily pay punch sync failed")
