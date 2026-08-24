# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import io
import zipfile

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Coalesce
from frappe.utils import flt, formatdate, fmt_money, getdate, sbool
from frappe.utils.csvutils import to_csv
from frappe.utils.pdf import get_pdf


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

	employees = as_list(filters.get("selected_employees")) or as_list(filters.get("employee"))
	if employees:
		query = query.where(SalarySlip.employee.isin(employees))

	salary_slips = as_list(filters.get("selected_salary_slips"))
	if salary_slips:
		query = query.where(SalarySlip.name.isin(salary_slips))

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


def as_list(value) -> list:
	if value in (None, "", []):
		return []
	if isinstance(value, str):
		stripped = value.strip()
		if stripped.startswith("["):
			value = frappe.parse_json(stripped)
		else:
			return [stripped] if stripped else []
	if isinstance(value, (list, tuple, set)):
		return [item for item in value if item not in (None, "")]
	return [value]


def _parse_filters(filters) -> frappe._dict:
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	return frappe._dict(filters or {})


def _assert_can_export():
	if not frappe.permissions.can_export("Salary Slip"):
		frappe.throw(_("Not permitted to export"), frappe.PermissionError)


def _export_rows(filters=None):
	columns, data = execute(filters)
	headers = [col.get("label") for col in columns]
	fieldnames = [col.get("fieldname") for col in columns]
	rows = [headers]
	for row in data:
		rows.append(["" if row.get(fieldname) is None else row.get(fieldname) for fieldname in fieldnames])
	return columns, data, rows


def _period_label(filters) -> str:
	filters = frappe._dict(filters or {})
	if filters.get("from_date") and filters.get("to_date"):
		return f"{getdate(filters.from_date)}_{getdate(filters.to_date)}"
	return "all"


def _period_display(filters) -> str:
	filters = frappe._dict(filters or {})
	if filters.get("from_date") and filters.get("to_date"):
		return _("{0} to {1}").format(formatdate(filters.from_date), formatdate(filters.to_date))
	return _("All Periods")


def _safe_filename(value: str) -> str:
	cleaned = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in str(value or ""))
	return cleaned.strip().replace(" ", "_") or "agent"


def _respond_file(filename: str, content, file_type: str = "binary"):
	frappe.response["filename"] = filename
	frappe.response["filecontent"] = content
	frappe.response["type"] = file_type


def _csv_bytes(rows: list) -> str:
	return to_csv(rows)


@frappe.whitelist()
def download_csv(filters: dict | str | None = None) -> None:
	"""Download Social Security deductions as CSV."""
	_assert_can_export()
	filters = _parse_filters(filters)
	_columns, data, rows = _export_rows(filters)
	if not data:
		frappe.throw(_("No data to export"))
	period = _period_label(filters)
	_respond_file(f"Social_Security_Deductions_{period}.csv", _csv_bytes(rows))


@frappe.whitelist()
def download_pdf(filters: dict | str | None = None) -> None:
	"""Download Social Security deductions as PDF."""
	_assert_can_export()
	filters = _parse_filters(filters)
	columns, data, _rows = _export_rows(filters)
	if not data:
		frappe.throw(_("No data to export"))

	html = frappe.render_template(
		"hrms/payroll/report/social_security_deductions/social_security_deductions.html",
		{
			"columns": columns,
			"data": [_pdf_row(columns, row) for row in data],
			"period_label": _period_display(filters),
			"generated_on": formatdate(getdate()),
			"totals": _pdf_totals(data),
		},
	)
	period = _period_label(filters)
	_respond_file(
		f"Social_Security_Deductions_{period}.pdf",
		get_pdf(html, {"orientation": "Landscape"}),
	)


def _pdf_row(columns, row) -> dict:
	formatted = {}
	for column in columns:
		fieldname = column.get("fieldname")
		value = row.get(fieldname)
		fieldtype = column.get("fieldtype")
		if value in (None, ""):
			formatted[fieldname] = ""
		elif fieldtype == "Date":
			formatted[fieldname] = formatdate(value)
		elif fieldtype == "Currency":
			formatted[fieldname] = fmt_money(flt(value))
		else:
			formatted[fieldname] = value
	return formatted


def _pdf_totals(data) -> dict:
	return {
		"ss_weekly_earnings": fmt_money(sum(flt(row.get("ss_weekly_earnings")) for row in data)),
		"ss_insurable_earnings": fmt_money(sum(flt(row.get("ss_insurable_earnings")) for row in data)),
		"ss_employee_amount": fmt_money(sum(flt(row.get("ss_employee_amount")) for row in data)),
		"ss_employer_amount": fmt_money(sum(flt(row.get("ss_employer_amount")) for row in data)),
		"total": fmt_money(sum(flt(row.get("total")) for row in data)),
	}


@frappe.whitelist()
def download_zip(filters: dict | str | None = None) -> None:
	"""Download one CSV per selected agent, packed as a ZIP."""
	_assert_can_export()
	filters = _parse_filters(filters)
	require_multiple = sbool(filters.get("require_multiple", True))
	selected_employees = as_list(filters.get("selected_employees"))

	if require_multiple and len(set(selected_employees)) < 2:
		frappe.throw(_("Select more than one agent to export a ZIP of CSV files."))

	columns, data, _rows = _export_rows(filters)
	grouped = {}
	for row in data:
		employee = row.get("employee")
		if not employee:
			continue
		grouped.setdefault(employee, []).append(row)

	if require_multiple and len(grouped) < 2:
		frappe.throw(_("Select more than one agent to export a ZIP of CSV files."))
	if not grouped:
		frappe.throw(_("No data to export"))

	headers = [col.get("label") for col in columns]
	fieldnames = [col.get("fieldname") for col in columns]
	period = _period_label(filters)
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
		for employee, employee_rows in grouped.items():
			csv_rows = [headers]
			for row in employee_rows:
				csv_rows.append(
					["" if row.get(fieldname) is None else row.get(fieldname) for fieldname in fieldnames]
				)
			agent_name = _safe_filename(employee_rows[0].get("employee_name") or employee)
			archive.writestr(
				f"{agent_name}_{_safe_filename(employee)}_{period}.csv",
				_csv_bytes(csv_rows),
			)

	_respond_file(f"Social_Security_Deductions_{period}.zip", buffer.getvalue())
