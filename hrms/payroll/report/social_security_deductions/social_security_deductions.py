# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import io
import zipfile

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Coalesce
from frappe.utils import getdate
from frappe.utils.csvutils import to_csv
from frappe.utils.xlsxutils import make_xlsx


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

	rows = query.orderby(SalarySlip.employee_name).orderby(SalarySlip.ss_number).orderby(SalarySlip.start_date).run(
		as_dict=True
	)
	ssn_map = _employee_ssn_map([row.employee for row in rows])

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
				"total": employee_ss + employer_ss,
			}
		)
	return data


def _employee_ssn_map(employees: list[str]) -> dict[str, str]:
	if not employees or not frappe.get_meta("Employee").has_field("social_security_number"):
		return {}
	rows = frappe.get_all(
		"Employee",
		filters={"name": ["in", employees]},
		fields=["name", "social_security_number"],
	)
	return {row.name: row.social_security_number for row in rows if row.social_security_number}


def _export_rows(filters=None):
	columns, data = execute(filters)
	headers = [col.get("label") for col in columns]
	fieldnames = [col.get("fieldname") for col in columns]
	rows = [headers]
	for row in data:
		rows.append(["" if row.get(fieldname) is None else row.get(fieldname) for fieldname in fieldnames])
	return rows


def _period_label(filters) -> str:
	filters = frappe._dict(filters or {})
	if filters.get("from_date") and filters.get("to_date"):
		return f"{getdate(filters.from_date)}_{getdate(filters.to_date)}"
	return "all"


@frappe.whitelist()
def download_zip(filters=None):
	"""Download Social Security deductions as a ZIP of CSV and Excel."""
	if not frappe.permissions.can_export("Salary Slip"):
		frappe.throw(_("Not permitted to export"), frappe.PermissionError)

	if isinstance(filters, str):
		filters = frappe.parse_json(filters)

	rows = _export_rows(filters)
	period = _period_label(filters)
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
		archive.writestr(f"Social_Security_Deductions_{period}.csv", to_csv(rows))
		archive.writestr(
			f"Social_Security_Deductions_{period}.xlsx",
			make_xlsx(rows, "Social Security Deductions").getvalue(),
		)

	frappe.response["filename"] = f"Social_Security_Deductions_{period}.zip"
	frappe.response["filecontent"] = buffer.getvalue()
	frappe.response["type"] = "binary"
