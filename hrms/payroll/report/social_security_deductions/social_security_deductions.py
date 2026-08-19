# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Coalesce
from frappe.utils import getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Agent"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"label": _("Agent Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Social Security Number"),
			"fieldname": "ss_number",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Team Group"),
			"fieldname": "employee_group",
			"fieldtype": "Link",
			"options": "Employee Group",
			"width": 140,
		},
		{
			"label": _("Salary Slip"),
			"fieldname": "salary_slip",
			"fieldtype": "Link",
			"options": "Salary Slip",
			"width": 160,
		},
		{
			"label": _("From"),
			"fieldname": "start_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("To"),
			"fieldname": "end_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Weekly Earnings"),
			"fieldname": "ss_weekly_earnings",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Wage Band"),
			"fieldname": "ss_wage_band",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Insurable Earnings"),
			"fieldname": "ss_insurable_earnings",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Category"),
			"fieldname": "ss_category",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Employee SS"),
			"fieldname": "ss_employee_amount",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Employer SS"),
			"fieldname": "ss_employer_amount",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Total"),
			"fieldname": "total",
			"fieldtype": "Currency",
			"width": 120,
		},
	]


def get_data(filters):
	SalarySlip = DocType("Salary Slip")
	query = (
		frappe.qb.from_(SalarySlip)
		.select(
			SalarySlip.employee,
			SalarySlip.employee_name,
			SalarySlip.ss_number,
			SalarySlip.name.as_("salary_slip"),
			SalarySlip.start_date,
			SalarySlip.end_date,
			SalarySlip.ss_weekly_earnings,
			SalarySlip.ss_wage_band,
			SalarySlip.ss_insurable_earnings,
			SalarySlip.ss_category,
			SalarySlip.ss_employee_amount,
			SalarySlip.ss_employer_amount,
		)
		.where(SalarySlip.docstatus == 1)
		.where(Coalesce(SalarySlip.ss_category, "") != "")
	)

	if filters.get("company"):
		query = query.where(SalarySlip.company == filters.company)
	if filters.get("from_date"):
		query = query.where(SalarySlip.end_date >= getdate(filters.from_date))
	if filters.get("to_date"):
		query = query.where(SalarySlip.start_date <= getdate(filters.to_date))
	if filters.get("employee"):
		query = query.where(SalarySlip.employee == filters.employee)
	if filters.get("ss_number"):
		query = query.where(SalarySlip.ss_number == filters.ss_number)

	group_employees = _employees_in_group(filters.get("employee_group"))
	if filters.get("employee_group"):
		if not group_employees:
			return []
		query = query.where(SalarySlip.employee.isin(group_employees))

	rows = query.orderby(SalarySlip.employee_name).orderby(SalarySlip.ss_number).orderby(SalarySlip.start_date).run(
		as_dict=True
	)
	ssn_map = _employee_ssn_map([row.employee for row in rows])
	group_map = _employee_group_map([row.employee for row in rows])

	data = []
	for row in rows:
		employee_ss = row.ss_employee_amount or 0
		employer_ss = row.ss_employer_amount or 0
		ss_number = row.ss_number or ssn_map.get(row.employee) or ""
		if filters.get("ss_number") and ss_number != filters.ss_number:
			continue
		data.append(
			{
				**row,
				"ss_number": ss_number,
				"employee_group": group_map.get(row.employee),
				"total": employee_ss + employer_ss,
			}
		)
	return data


def _employees_in_group(employee_group: str | None) -> list[str]:
	if not employee_group or not frappe.db.table_exists("Employee Group Table"):
		return []
	return frappe.get_all(
		"Employee Group Table",
		filters={"parent": employee_group, "parenttype": "Employee Group"},
		pluck="employee",
	)


def _employee_group_map(employees: list[str]) -> dict[str, str]:
	if not employees or not frappe.db.table_exists("Employee Group Table"):
		return {}
	rows = frappe.get_all(
		"Employee Group Table",
		filters={"employee": ["in", employees], "parenttype": "Employee Group"},
		fields=["employee", "parent"],
	)
	return {row.employee: row.parent for row in rows}


def _employee_ssn_map(employees: list[str]) -> dict[str, str]:
	if not employees or not frappe.get_meta("Employee").has_field("social_security_number"):
		return {}
	rows = frappe.get_all(
		"Employee",
		filters={"name": ["in", employees]},
		fields=["name", "social_security_number"],
	)
	return {row.name: row.social_security_number for row in rows if row.social_security_number}
