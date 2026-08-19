# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import cint, flt, getdate

CATEGORY_FLAGS = {
	"Bonus": "exclude_bonuses",
	"Incentive": "exclude_incentives",
	"Overtime": "exclude_overtime",
	"Commission": "exclude_commissions",
}


def get_active_tax_adjustment(employee, company, payroll_period, as_on=None):
	"""Return the latest submitted tax adjustment covering this agent and date."""
	if not employee or not payroll_period:
		return None
	if not frappe.db.table_exists("Employee Tax Adjustment"):
		return None

	as_on = getdate(as_on) if as_on else getdate()
	Adjustment = frappe.qb.DocType("Employee Tax Adjustment")
	Detail = frappe.qb.DocType("Employee Tax Adjustment Employee")

	query = (
		frappe.qb.from_(Adjustment)
		.join(Detail)
		.on(Detail.parent == Adjustment.name)
		.select(
			Adjustment.name,
			Adjustment.adjustment_type,
			Adjustment.exclude_bonuses,
			Adjustment.exclude_incentives,
			Adjustment.exclude_overtime,
			Adjustment.exclude_commissions,
			Adjustment.income_tax_slab,
			Adjustment.tax_amount_override,
			Adjustment.opening_taxable_earnings,
			Adjustment.tax_deducted_till_date,
			Adjustment.valid_from,
			Adjustment.valid_to,
			Adjustment.modified,
		)
		.where(Adjustment.docstatus == 1)
		.where(Detail.employee == employee)
		.where(Adjustment.payroll_period == payroll_period)
		.where(Adjustment.valid_from <= as_on)
		.where(Adjustment.valid_to >= as_on)
	)
	if company:
		query = query.where(Adjustment.company == company)

	rows = query.orderby(Adjustment.modified, order=frappe.qb.desc).run(as_dict=True)
	if not rows:
		return None

	adjustment = rows[0]
	adjustment.excluded_components = frappe.get_all(
		"Employee Tax Adjustment Component",
		filters={"parent": adjustment.name},
		pluck="salary_component",
	)
	return adjustment


def is_excluded_from_tax(adjustment) -> bool:
	return bool(adjustment and adjustment.adjustment_type == "Exclude from Tax Period")


def get_excluded_component_names(adjustment) -> set[str]:
	if not adjustment:
		return set()
	return set(adjustment.get("excluded_components") or [])


def earning_is_tax_exempt(salary_component: str, adjustment=None, additional_salary=None) -> bool:
	if additional_salary and cint(getattr(additional_salary, "exclude_from_tax", 0)):
		return True

	if additional_salary and isinstance(additional_salary, str):
		exclude = frappe.db.get_value("Additional Salary", additional_salary, "exclude_from_tax")
		if cint(exclude):
			return True

	if not salary_component:
		return False

	if adjustment and salary_component in get_excluded_component_names(adjustment):
		return True

	if not adjustment:
		return False

	category = ""
	try:
		category = frappe.db.get_value("Salary Component", salary_component, "earning_category", cache=True) or ""
	except Exception:
		category = ""
	flag = CATEGORY_FLAGS.get(category)
	return bool(flag and cint(adjustment.get(flag)))


def apply_tax_exclusions_to_earnings(salary_slip, adjustment=None):
	"""Mark bonus/incentive/overtime/commission rows as non-taxable when configured."""
	if not salary_slip.get("earnings"):
		return

	for earning in salary_slip.earnings:
		if earning_is_tax_exempt(earning.salary_component, adjustment, earning.additional_salary):
			earning.is_tax_applicable = 0
			earning.deduct_full_tax_on_selected_payroll_date = 0


def zero_tax_components(salary_slip, tax_components):
	from hrms.payroll.doctype.salary_slip.salary_slip import get_salary_component_data

	for tax_component in tax_components:
		tax_row = get_salary_component_data(tax_component)
		if tax_row:
			salary_slip.update_component_row(tax_row, 0, "deductions")
