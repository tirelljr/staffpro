# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import date

import frappe
from frappe.utils import date_diff, flt, getdate

SS_EMPLOYEE_COMPONENT = "Social Security"
SS_EMPLOYER_COMPONENT = "Social Security Employer"
SS_CATEGORY_STANDARD = "Standard"
SS_CATEGORY_INJURY_ONLY = "Employment Injury Only"

BELIZE_SSB_2022_BANDS = [
	{
		"band_label": "UNDER $70.00",
		"from_weekly_earnings": 0,
		"to_weekly_earnings": 69.99,
		"insurable_earnings": 55.00,
		"employee_amount": 1.03,
		"employer_amount": 4.47,
	},
	{
		"band_label": "$70.00 - $109.99",
		"from_weekly_earnings": 70.00,
		"to_weekly_earnings": 109.99,
		"insurable_earnings": 90.00,
		"employee_amount": 1.69,
		"employer_amount": 7.31,
	},
	{
		"band_label": "$110.00 - $139.99",
		"from_weekly_earnings": 110.00,
		"to_weekly_earnings": 139.99,
		"insurable_earnings": 130.00,
		"employee_amount": 2.44,
		"employer_amount": 10.56,
	},
	{
		"band_label": "$140.00 - $179.99",
		"from_weekly_earnings": 140.00,
		"to_weekly_earnings": 179.99,
		"insurable_earnings": 160.00,
		"employee_amount": 3.94,
		"employer_amount": 12.06,
	},
	{
		"band_label": "$180.00 - $219.99",
		"from_weekly_earnings": 180.00,
		"to_weekly_earnings": 219.99,
		"insurable_earnings": 200.00,
		"employee_amount": 5.94,
		"employer_amount": 14.06,
	},
	{
		"band_label": "$220.00 - $259.99",
		"from_weekly_earnings": 220.00,
		"to_weekly_earnings": 259.99,
		"insurable_earnings": 240.00,
		"employee_amount": 7.94,
		"employer_amount": 16.06,
	},
	{
		"band_label": "$260.00 - $299.99",
		"from_weekly_earnings": 260.00,
		"to_weekly_earnings": 299.99,
		"insurable_earnings": 280.00,
		"employee_amount": 9.94,
		"employer_amount": 18.06,
	},
	{
		"band_label": "$300.00 - $339.99",
		"from_weekly_earnings": 300.00,
		"to_weekly_earnings": 339.99,
		"insurable_earnings": 320.00,
		"employee_amount": 11.94,
		"employer_amount": 20.06,
	},
	{
		"band_label": "$340.00 - $379.99",
		"from_weekly_earnings": 340.00,
		"to_weekly_earnings": 379.99,
		"insurable_earnings": 360.00,
		"employee_amount": 13.98,
		"employer_amount": 22.02,
	},
	{
		"band_label": "$380.00 - $419.99",
		"from_weekly_earnings": 380.00,
		"to_weekly_earnings": 419.99,
		"insurable_earnings": 400.00,
		"employee_amount": 16.15,
		"employer_amount": 23.85,
	},
	{
		"band_label": "$420.00 - $459.99",
		"from_weekly_earnings": 420.00,
		"to_weekly_earnings": 459.99,
		"insurable_earnings": 440.00,
		"employee_amount": 18.45,
		"employer_amount": 25.55,
	},
	{
		"band_label": "$460.00 - $499.99",
		"from_weekly_earnings": 460.00,
		"to_weekly_earnings": 499.99,
		"insurable_earnings": 480.00,
		"employee_amount": 20.86,
		"employer_amount": 27.14,
	},
	{
		"band_label": "$500.00 - OVER",
		"from_weekly_earnings": 500.00,
		"to_weekly_earnings": 0,
		"insurable_earnings": 520.00,
		"employee_amount": 23.40,
		"employer_amount": 28.60,
	},
]


def weekly_earnings_from_gross(gross_pay, payroll_frequency: str | None) -> float:
	"""Convert a salary-slip gross amount into weekly earnings for SSB lookup."""
	gross = flt(gross_pay)
	frequency = payroll_frequency or "Weekly"
	if frequency == "Weekly":
		return gross
	if frequency == "Fortnightly":
		return gross / 2.0
	if frequency == "Bimonthly":
		return gross / 2.0
	if frequency == "Daily":
		return gross * 7.0
	# Monthly and any other period: annualize then divide by 52 contribution weeks
	return gross * 12.0 / 52.0


def contribution_weeks(payroll_frequency: str | None, start_date, end_date) -> float:
	"""How many SSB contribution weeks this slip covers."""
	frequency = payroll_frequency or "Weekly"
	if frequency == "Weekly":
		return 1.0
	if not start_date or not end_date:
		return 1.0
	days = date_diff(getdate(end_date), getdate(start_date)) + 1
	return max(flt(days) / 7.0, 0.0)


def get_age(date_of_birth, as_on) -> int | None:
	if not date_of_birth or not as_on:
		return None
	dob = getdate(date_of_birth)
	on = getdate(as_on)
	age = on.year - dob.year
	if (on.month, on.day) < (dob.month, dob.day):
		age -= 1
	return age


def is_injury_only(age: int | None, receiving_ss_benefit: bool) -> bool:
	if age is None:
		return False
	if age >= 65:
		return True
	if 60 <= age < 65 and receiving_ss_benefit:
		return True
	return False


def lookup_band(weekly_earnings: float, bands) -> dict | None:
	amount = flt(weekly_earnings)
	matched = None
	for band in bands:
		from_amt = flt(band.get("from_weekly_earnings") if isinstance(band, dict) else band.from_weekly_earnings)
		to_amt = flt(band.get("to_weekly_earnings") if isinstance(band, dict) else band.to_weekly_earnings)
		if amount < from_amt:
			continue
		if to_amt and amount > to_amt:
			continue
		matched = band if isinstance(band, dict) else band.as_dict()
	return matched


def calculate_contribution(
	gross_pay,
	payroll_frequency,
	start_date,
	end_date,
	date_of_birth=None,
	receiving_ss_benefit=False,
	bands=None,
	injury_only_employee_amount=0.0,
	injury_only_employer_amount=2.60,
) -> dict:
	weekly_earnings = weekly_earnings_from_gross(gross_pay, payroll_frequency)
	weeks = contribution_weeks(payroll_frequency, start_date, end_date)
	age = get_age(date_of_birth, end_date or start_date or date.today())
	injury_only = is_injury_only(age, bool(receiving_ss_benefit))

	result = {
		"weekly_earnings": flt(weekly_earnings, 2),
		"weeks": weeks,
		"age": age,
		"category": SS_CATEGORY_INJURY_ONLY if injury_only else SS_CATEGORY_STANDARD,
		"wage_band": "",
		"insurable_earnings": 0.0,
		"employee_amount": 0.0,
		"employer_amount": 0.0,
	}

	if weekly_earnings <= 0 or weeks <= 0:
		result["category"] = ""
		return result

	if injury_only:
		result.update(
			{
				"wage_band": "(A) & (B)",
				"insurable_earnings": 0.0,
				"employee_amount": flt(flt(injury_only_employee_amount) * weeks, 2),
				"employer_amount": flt(flt(injury_only_employer_amount) * weeks, 2),
			}
		)
		return result

	band = lookup_band(weekly_earnings, bands or BELIZE_SSB_2022_BANDS)
	if not band:
		return result

	result.update(
		{
			"wage_band": band.get("band_label") or "",
			"insurable_earnings": flt(band.get("insurable_earnings"), 2),
			"employee_amount": flt(flt(band.get("employee_amount")) * weeks, 2),
			"employer_amount": flt(flt(band.get("employer_amount")) * weeks, 2),
		}
	)
	return result


def get_active_contribution_table(company: str | None, as_on):
	if not frappe.db.table_exists("Social Security Contribution Table"):
		return None
	as_on = getdate(as_on) if as_on else getdate()
	rows = frappe.get_all(
		"Social Security Contribution Table",
		filters={"disabled": 0, "effective_from": ("<=", as_on)},
		fields=["name", "company", "effective_from"],
		order_by="effective_from desc",
	)
	if not rows:
		return None
	company_match = [row for row in rows if row.company and row.company == company]
	global_match = [row for row in rows if not row.company]
	picked = (company_match or global_match)
	if not picked:
		return None
	return frappe.get_cached_doc("Social Security Contribution Table", picked[0].name)


def seed_belize_ssb_2022_table(title: str = "Belize SSB 2022"):
	if frappe.db.exists("Social Security Contribution Table", title):
		return frappe.get_doc("Social Security Contribution Table", title)

	doc = frappe.get_doc(
		{
			"doctype": "Social Security Contribution Table",
			"title": title,
			"effective_from": "2022-04-04",
			"injury_only_employee_amount": 0,
			"injury_only_employer_amount": 2.60,
			"bands": [dict(band) for band in BELIZE_SSB_2022_BANDS],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def ensure_employee_ss_fields():
	"""Add Social Security Number and benefit flag on Employee if missing."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	meta = frappe.get_meta("Employee")
	if not meta.has_field("social_security_number"):
		create_custom_field(
			"Employee",
			{
				"fieldname": "social_security_number",
				"fieldtype": "Data",
				"label": "Social Security Number",
				"insert_after": "date_of_birth",
				"in_standard_filter": 1,
				"in_list_view": 1,
				"translatable": 0,
				"description": "Belize Social Security Board registration number. Deductions are matched to this number and the agent's name.",
			},
		)
		frappe.clear_cache(doctype="Employee")
		meta = frappe.get_meta("Employee")

	if not meta.has_field("receiving_ss_benefit"):
		create_custom_field(
			"Employee",
			{
				"fieldname": "receiving_ss_benefit",
				"fieldtype": "Check",
				"label": "Receiving Social Security Benefit",
				"insert_after": "social_security_number"
				if meta.has_field("social_security_number")
				else "date_of_birth",
				"description": "Category (A): persons aged 60-64 who have received or are receiving a Social Security benefit.",
			},
		)
		frappe.clear_cache(doctype="Employee")


def ensure_ss_salary_components():
	_ensure_component(
		SS_EMPLOYEE_COMPONENT,
		abbr="SS",
		component_type="Deduction",
		depends_on_payment_days=0,
		is_tax_applicable=0,
		exempted_from_income_tax=1,
		remove_if_zero_valued=0,
	)
	_ensure_component(
		SS_EMPLOYER_COMPONENT,
		abbr="SSE",
		component_type="Employer Contribution",
		depends_on_payment_days=0,
		is_tax_applicable=0,
		do_not_include_in_total=1,
		remove_if_zero_valued=0,
	)


def _ensure_component(name: str, abbr: str, component_type: str, **kwargs):
	if frappe.db.exists("Salary Component", name):
		updates = {key: value for key, value in kwargs.items() if value is not None}
		if updates:
			frappe.db.set_value("Salary Component", name, updates, update_modified=False)
		return
	doc = frappe.get_doc(
		{
			"doctype": "Salary Component",
			"salary_component": name,
			"salary_component_abbr": abbr,
			"type": component_type,
			"description": name,
			**kwargs,
		}
	)
	doc.insert(ignore_permissions=True)


def apply_social_security(salary_slip) -> None:
	"""Inject Belize SSB employee deduction and persist band details on the slip."""
	if frappe.flags.in_test and not frappe.flags.get("apply_social_security"):
		return
	if not salary_slip.employee or not salary_slip.start_date:
		return

	table = get_active_contribution_table(
		salary_slip.company, salary_slip.end_date or salary_slip.posting_date or salary_slip.start_date
	)
	bands = table.bands if table else None
	injury_employee = flt(table.injury_only_employee_amount) if table else 0.0
	injury_employer = flt(table.injury_only_employer_amount) if table else 2.60

	employee_fields = ["date_of_birth", "employee_name"]
	meta = frappe.get_meta("Employee")
	if meta.has_field("social_security_number"):
		employee_fields.append("social_security_number")
	if meta.has_field("receiving_ss_benefit"):
		employee_fields.append("receiving_ss_benefit")

	employee = frappe.db.get_value(
		"Employee",
		salary_slip.employee,
		employee_fields,
		as_dict=True,
	) or {}

	contribution = calculate_contribution(
		gross_pay=salary_slip.gross_pay,
		payroll_frequency=salary_slip.payroll_frequency,
		start_date=salary_slip.start_date,
		end_date=salary_slip.end_date,
		date_of_birth=employee.get("date_of_birth"),
		receiving_ss_benefit=employee.get("receiving_ss_benefit"),
		bands=bands,
		injury_only_employee_amount=injury_employee,
		injury_only_employer_amount=injury_employer,
	)

	if employee.get("employee_name"):
		salary_slip.employee_name = employee.get("employee_name")
	if hasattr(salary_slip, "ss_number"):
		salary_slip.ss_number = employee.get("social_security_number") or salary_slip.ss_number

	if hasattr(salary_slip, "ss_weekly_earnings"):
		salary_slip.ss_weekly_earnings = contribution["weekly_earnings"]
		salary_slip.ss_insurable_earnings = contribution["insurable_earnings"]
		salary_slip.ss_wage_band = contribution["wage_band"]
		salary_slip.ss_category = contribution["category"]
		salary_slip.ss_employee_amount = contribution["employee_amount"]
		salary_slip.ss_employer_amount = contribution["employer_amount"]

	if contribution["category"] and contribution["weekly_earnings"] > 0:
		_inject_employee_deduction(salary_slip, contribution["employee_amount"])


def _inject_employee_deduction(salary_slip, amount: float) -> None:
	if not frappe.db.exists("Salary Component", SS_EMPLOYEE_COMPONENT):
		ensure_ss_salary_components()
	if not frappe.db.exists("Salary Component", SS_EMPLOYEE_COMPONENT):
		return

	component = frappe.get_cached_doc("Salary Component", SS_EMPLOYEE_COMPONENT)
	salary_slip.update_component_row(
		component,
		flt(amount, 2),
		"deductions",
		remove_if_zero_valued=False,
	)
