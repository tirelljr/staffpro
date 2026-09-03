# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Employee profile password + lifetime payroll/billing stats for the form sidebar."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


@frappe.whitelist()
def update_employee_user_password(employee: str, new_password: str, logout_all_sessions: int = 0) -> dict:
	"""Set or change the linked HRMS User password for an Employee."""
	frappe.has_permission("Employee", "write", employee, throw=True)
	emp = frappe.get_doc("Employee", employee)
	user = (emp.user_id or "").strip()
	if not user:
		frappe.throw(_("Link a User ID on this employee before setting a password."))

	password = (new_password or "").strip()
	if len(password) < 8:
		frappe.throw(_("Password must be at least 8 characters."))

	if not frappe.db.exists("User", user):
		frappe.throw(_("User {0} does not exist.").format(frappe.bold(user)))

	# HR/System Manager, or the employee changing their own login.
	roles = set(frappe.get_roles())
	is_self = frappe.session.user == user
	is_hr = bool(roles.intersection({"System Manager", "HR Manager", "HR User", "Administrator"}))
	if not (is_self or is_hr):
		frappe.throw(_("Not permitted to change this password."), frappe.PermissionError)

	from frappe.utils.password import update_password

	update_password(user, password, logout_all_sessions=cint(logout_all_sessions))
	return {"ok": True, "user": user}


@frappe.whitelist()
def get_employee_profile_stats(employee: str) -> dict:
	"""Lifetime payroll / billing totals for the Employee form sidebar."""
	frappe.has_permission("Employee", "read", employee, throw=True)
	emp = frappe.db.get_value(
		"Employee",
		employee,
		["name", "employee_name", "company", "user_id"],
		as_dict=True,
	)
	if not emp:
		frappe.throw(_("Employee not found"))

	company_currency = (
		frappe.db.get_value("Company", emp.company, "default_currency") if emp.company else "BZD"
	) or "BZD"

	hours = _total_hours(employee)
	income = _salary_totals(employee)
	billed = _billed_totals(employee)
	leave_remaining = _leave_remaining(employee)
	billed_company = _convert_amount(billed["amount"], billed["currency"], company_currency)
	agent_profit = flt(billed_company) - flt(income["gross_pay"])

	return {
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"user_id": emp.user_id or "",
		"company_currency": company_currency,
		"billing_currency": billed["currency"],
		"total_hours": hours,
		"total_income": flt(income["gross_pay"], 2),
		"total_ss": flt(income["ss"], 2),
		"total_tax": flt(income["tax"], 2),
		"total_billed": flt(billed["amount"], 2),
		"agent_profit": flt(agent_profit, 2),
		"leave_remaining": leave_remaining,
	}


def _leave_remaining(employee: str) -> float:
	try:
		from hrms.hr.doctype.leave_application.leave_application import get_leave_details

		details = get_leave_details(employee, getdate())
	except Exception:
		return 0.0

	total = 0.0
	for values in (details.get("leave_allocation") or {}).values():
		total += flt(values.get("remaining_leaves"))
	return flt(total, 2)


def _total_hours(employee: str) -> float:
	if not frappe.db.table_exists("Attendance"):
		return 0.0
	rows = frappe.get_all(
		"Attendance",
		filters={"employee": employee, "docstatus": ["<", 2], "status": ["in", ["Present", "Half Day", "Work From Home"]]},
		fields=["working_hours", "status"],
	)
	standard = flt(frappe.db.get_single_value("HR Settings", "standard_working_hours")) or 8.0
	total = 0.0
	for row in rows:
		hours = flt(row.working_hours)
		if not hours:
			hours = standard / 2.0 if row.status == "Half Day" else standard
		total += hours
	return flt(total, 2)


def _salary_totals(employee: str) -> dict:
	gross = ss = tax = 0.0
	if frappe.db.table_exists("Salary Slip"):
		fields = ["name", "gross_pay", "net_pay", "total_working_hours"]
		meta_fields = {df.fieldname for df in frappe.get_meta("Salary Slip").fields}
		if "ss_employee_amount" in meta_fields:
			fields.append("ss_employee_amount")
		if "current_month_income_tax" in meta_fields:
			fields.append("current_month_income_tax")
		if "total_income_tax" in meta_fields:
			fields.append("total_income_tax")

		slips = frappe.get_all(
			"Salary Slip",
			filters={"employee": employee, "docstatus": 1},
			fields=fields,
		)
		for slip in slips:
			gross += flt(slip.gross_pay)
			ss += flt(slip.get("ss_employee_amount"))
			tax += flt(slip.get("current_month_income_tax") or 0)
			if not slip.get("current_month_income_tax"):
				tax += _tax_from_deductions(slip.name)

	if not ss and frappe.db.table_exists("Attendance"):
		att_fields = ["ss_deduction"] if frappe.db.has_column("Attendance", "ss_deduction") else []
		if att_fields:
			for amount in frappe.get_all(
				"Attendance",
				filters={"employee": employee, "docstatus": ["<", 2]},
				pluck="ss_deduction",
			):
				ss += flt(amount)

	if not tax and frappe.db.has_column("Attendance", "tax_deduction"):
		for amount in frappe.get_all(
			"Attendance",
			filters={"employee": employee, "docstatus": ["<", 2]},
			pluck="tax_deduction",
		):
			tax += flt(amount)

	if not gross and frappe.db.has_column("Attendance", "net_daily_pay"):
		for amount in frappe.get_all(
			"Attendance",
			filters={"employee": employee, "docstatus": ["<", 2]},
			pluck="net_daily_pay",
		):
			gross += flt(amount)

	return {"gross_pay": gross, "ss": ss, "tax": tax}


def _tax_from_deductions(salary_slip: str) -> float:
	if not salary_slip or not frappe.db.table_exists("Salary Detail"):
		return 0.0
	rows = frappe.get_all(
		"Salary Detail",
		filters={
			"parent": salary_slip,
			"parenttype": "Salary Slip",
			"parentfield": "deductions",
		},
		fields=["salary_component", "amount"],
	)
	total = 0.0
	for row in rows:
		name = (row.salary_component or "").lower()
		if "tax" in name or name in {"paye", "income tax"}:
			total += flt(row.amount)
	return total


def _billed_totals(employee: str) -> dict:
	currency = "USD"
	amount = 0.0
	if not frappe.db.table_exists("Client Invoice Item"):
		return {"amount": amount, "currency": currency}

	Item = frappe.qb.DocType("Client Invoice Item")
	Invoice = frappe.qb.DocType("Client Invoice")
	rows = (
		frappe.qb.from_(Item)
		.inner_join(Invoice)
		.on(Item.parent == Invoice.name)
		.select(Item.amount, Invoice.currency)
		.where(Item.employee == employee)
		.where(Invoice.docstatus == 1)
	).run(as_dict=True)
	for row in rows:
		amount += flt(row.amount)
		if row.currency:
			currency = row.currency
	return {"amount": amount, "currency": currency or "USD"}


def _convert_amount(amount: float, from_currency: str, to_currency: str) -> float:
	amount = flt(amount)
	if not amount or not from_currency or not to_currency or from_currency == to_currency:
		return amount
	try:
		from erpnext.setup.utils import get_exchange_rate

		rate = flt(get_exchange_rate(from_currency, to_currency, getdate())) or 1.0
	except Exception:
		rate = 1.0
	return flt(amount) * flt(rate)
