# Copyright (c) 2026, Staff Pro BPO and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Extract
from frappe.utils import cint, flt, formatdate, get_first_day, get_last_day, getdate
from frappe.utils.pdf import get_pdf
from frappe.utils.xlsxutils import make_xlsx


def execute(filters=None):
	filters = frappe._dict(filters or {})
	normalize_filters(filters)
	data = get_data(filters)
	return get_columns(), data


def normalize_filters(filters):
	"""Prefer from/to dates; fall back to month/year when dates are blank."""
	if filters.get("from_date") and filters.get("to_date"):
		return

	if filters.get("month") and filters.get("year"):
		month = cint(filters.month)
		year = cint(filters.year)
		filters.from_date = get_first_day(f"{year}-{month:02d}-01")
		filters.to_date = get_last_day(filters.from_date)


def get_columns():
	return [
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 160,
		},
		{
			"label": _("Employer SS Reg. No"),
			"fieldname": "employer_ss_reg_no",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Social Security Number"),
			"fieldname": "social_security_number",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Period Start"),
			"fieldname": "start_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Period End"),
			"fieldname": "end_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Wage Band"),
			"fieldname": "ss_wage_band",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Weekly Insurable Earnings"),
			"fieldname": "ss_weekly_insurable_earnings",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Weeks"),
			"fieldname": "ss_weeks",
			"fieldtype": "Float",
			"width": 80,
		},
		{
			"label": _("Employee Contribution"),
			"fieldname": "ss_employee_contribution",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Employer Contribution"),
			"fieldname": "ss_employer_contribution",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Total"),
			"fieldname": "total",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Scheme"),
			"fieldname": "ss_scheme",
			"fieldtype": "Data",
			"width": 160,
		},
	]


def get_data(filters):
	SalarySlip = DocType("Salary Slip")

	query = (
		frappe.qb.from_(SalarySlip)
		.select(
			SalarySlip.name.as_("salary_slip"),
			SalarySlip.company,
			SalarySlip.employee,
			SalarySlip.employee_name,
			SalarySlip.start_date,
			SalarySlip.end_date,
			SalarySlip.ss_scheme,
			SalarySlip.ss_wage_band,
			SalarySlip.ss_weeks,
			SalarySlip.ss_weekly_insurable_earnings,
			SalarySlip.ss_employee_contribution,
			SalarySlip.ss_employer_contribution,
			SalarySlip.ss_social_security_number,
		)
		.where(SalarySlip.docstatus == 1)
		.where(
			(SalarySlip.ss_employee_contribution > 0)
			| (SalarySlip.ss_employer_contribution > 0)
			| (SalarySlip.ss_scheme.isnotnull())
		)
		.orderby(SalarySlip.company)
		.orderby(SalarySlip.start_date)
		.orderby(SalarySlip.employee)
	)

	if filters.get("company"):
		query = query.where(SalarySlip.company == filters.company)
	if filters.get("from_date"):
		query = query.where(SalarySlip.end_date >= getdate(filters.from_date))
	if filters.get("to_date"):
		query = query.where(SalarySlip.start_date <= getdate(filters.to_date))
	if filters.get("employee"):
		query = query.where(SalarySlip.employee == filters.employee)
	if filters.get("department"):
		query = query.where(SalarySlip.department == filters.department)
	if filters.get("branch"):
		query = query.where(SalarySlip.branch == filters.branch)

	rows = query.run(as_dict=True)
	if not rows:
		return []

	company_reg = {}
	employee_ssn = {}
	if frappe.db.has_column("Company", "social_security_registration_no"):
		for company in {r.company for r in rows}:
			company_reg[company] = frappe.db.get_value(
				"Company", company, "social_security_registration_no"
			)
	if frappe.db.has_column("Employee", "social_security_number"):
		for employee in {r.employee for r in rows}:
			employee_ssn[employee] = frappe.db.get_value("Employee", employee, "social_security_number")

	data = []
	for row in rows:
		employee_amt = flt(row.ss_employee_contribution)
		employer_amt = flt(row.ss_employer_contribution)
		data.append(
			{
				"company": row.company,
				"employer_ss_reg_no": company_reg.get(row.company),
				"employee": row.employee,
				"employee_name": row.employee_name,
				"social_security_number": row.ss_social_security_number or employee_ssn.get(row.employee),
				"start_date": row.start_date,
				"end_date": row.end_date,
				"start_date_formatted": formatdate(row.start_date) if row.start_date else "",
				"end_date_formatted": formatdate(row.end_date) if row.end_date else "",
				"ss_wage_band": row.ss_wage_band,
				"ss_weekly_insurable_earnings": flt(row.ss_weekly_insurable_earnings),
				"ss_weeks": flt(row.ss_weeks),
				"ss_employee_contribution": employee_amt,
				"ss_employer_contribution": employer_amt,
				"total": employee_amt + employer_amt,
				"ss_scheme": row.ss_scheme,
				"salary_slip": row.salary_slip,
			}
		)

	return data


@frappe.whitelist()
def get_years() -> str:
	SalarySlip = DocType("Salary Slip")
	year_list = (
		frappe.qb.from_(SalarySlip)
		.select(Extract("year", SalarySlip.end_date).as_("year"))
		.distinct()
		.orderby(Extract("year", SalarySlip.end_date), order=frappe.qb.desc)
		.run(pluck=True)
	)
	if not year_list:
		year_list = [getdate().year]
	return "\n".join(str(year) for year in year_list if year)


@frappe.whitelist()
def download_excel(filters=None):
	"""Download Social Security contributions as Excel."""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	filters = frappe._dict(filters or {})
	normalize_filters(filters)
	data = get_data(filters)

	headers = [
		"Company",
		"Employer SS Reg. No",
		"Employee",
		"Employee Name",
		"Social Security Number",
		"Period Start",
		"Period End",
		"Wage Band",
		"Weekly Insurable Earnings",
		"Weeks",
		"Employee Contribution",
		"Employer Contribution",
		"Total",
		"Scheme",
	]
	xlsx_data = [headers]

	current_company = None
	company_employee = 0.0
	company_employer = 0.0
	grand_employee = 0.0
	grand_employer = 0.0

	def append_company_total():
		nonlocal company_employee, company_employer
		if current_company is None:
			return
		xlsx_data.append(
			[
				_("Total for {0}").format(current_company),
				"",
				"",
				"",
				"",
				"",
				"",
				"",
				"",
				"",
				company_employee,
				company_employer,
				company_employee + company_employer,
				"",
			]
		)
		xlsx_data.append([""] * len(headers))

	for row in data:
		if current_company and row["company"] != current_company:
			append_company_total()
			company_employee = 0.0
			company_employer = 0.0

		current_company = row["company"]
		company_employee += flt(row["ss_employee_contribution"])
		company_employer += flt(row["ss_employer_contribution"])
		grand_employee += flt(row["ss_employee_contribution"])
		grand_employer += flt(row["ss_employer_contribution"])

		xlsx_data.append(
			[
				row["company"],
				row.get("employer_ss_reg_no") or "",
				row["employee"],
				row["employee_name"],
				row.get("social_security_number") or "",
				row.get("start_date_formatted") or "",
				row.get("end_date_formatted") or "",
				row.get("ss_wage_band") or "",
				flt(row.get("ss_weekly_insurable_earnings")),
				flt(row.get("ss_weeks")),
				flt(row["ss_employee_contribution"]),
				flt(row["ss_employer_contribution"]),
				flt(row["total"]),
				row.get("ss_scheme") or "",
			]
		)

	append_company_total()
	xlsx_data.append(
		[
			_("Grand Total"),
			"",
			"",
			"",
			"",
			"",
			"",
			"",
			"",
			"",
			grand_employee,
			grand_employer,
			grand_employee + grand_employer,
			"",
		]
	)

	period = _period_label(filters)
	xlsx_file = make_xlsx(xlsx_data, "Social Security Contributions")
	frappe.response["filename"] = f"Social_Security_Contributions_{period}.xlsx"
	frappe.response["filecontent"] = xlsx_file.getvalue()
	frappe.response["type"] = "binary"


@frappe.whitelist()
def download_pdf(filters=None):
	"""Download Social Security contributions as a remittance-style PDF."""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	filters = frappe._dict(filters or {})
	normalize_filters(filters)
	data = get_data(filters)

	grouped = []
	by_company = {}
	for row in data:
		by_company.setdefault(row["company"], []).append(row)

	for company, rows in by_company.items():
		emp_total = sum(flt(r["ss_employee_contribution"]) for r in rows)
		empr_total = sum(flt(r["ss_employer_contribution"]) for r in rows)
		grouped.append(
			{
				"company": company,
				"employer_ss_reg_no": rows[0].get("employer_ss_reg_no"),
				"rows": rows,
				"employee_total": emp_total,
				"employer_total": empr_total,
				"grand_total": emp_total + empr_total,
			}
		)

	html = frappe.render_template(
		"hrms/payroll/report/social_security_contributions/social_security_contributions.html",
		{
			"grouped": grouped,
			"period_label": _period_display(filters),
			"generated_on": formatdate(getdate()),
		},
	)

	period = _period_label(filters)
	frappe.local.response.filename = f"Social_Security_Contributions_{period}.pdf"
	frappe.local.response.filecontent = get_pdf(html)
	frappe.local.response.type = "pdf"


def _period_label(filters) -> str:
	if filters.get("from_date") and filters.get("to_date"):
		return f"{getdate(filters.from_date)}_{getdate(filters.to_date)}"
	if filters.get("month") and filters.get("year"):
		return f"{cint(filters.year)}_{cint(filters.month):02d}"
	return "all"


def _period_display(filters) -> str:
	if filters.get("from_date") and filters.get("to_date"):
		return _("{0} to {1}").format(formatdate(filters.from_date), formatdate(filters.to_date))
	if filters.get("month") and filters.get("year"):
		months = [
			"",
			"Jan",
			"Feb",
			"Mar",
			"Apr",
			"May",
			"Jun",
			"Jul",
			"Aug",
			"Sep",
			"Oct",
			"Nov",
			"Dec",
		]
		return _("{0} {1}").format(months[cint(filters.month)], cint(filters.year))
	return _("All Periods")
