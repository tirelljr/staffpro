# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from frappe.utils import flt

BELIZE_TAX_EXEMPT_LIMIT = 26000
BELIZE_STANDARD_TAX_DEDUCTION = 100
BELIZE_TAX_RATE = 0.25

BELIZE_PERSONAL_RELIEF_TIERS = (
	(27000, 24600),
	(29000, 22600),
	(float("inf"), 19600),
)


def get_belize_personal_relief(annual_taxable_earning: float) -> float:
	amount = flt(annual_taxable_earning)
	for upper_bound, relief in BELIZE_PERSONAL_RELIEF_TIERS:
		if amount <= upper_bound:
			return relief
	return 19600


def calculate_tax_by_tax_slab(annual_taxable_earning, tax_slab, eval_globals=None, eval_locals=None):
	"""Belize PAYE: flat 25% on chargeable income with tiered personal relief."""
	annual_taxable_earning = flt(annual_taxable_earning)
	exempt_limit = flt(getattr(tax_slab, "tax_relief_limit", None) or BELIZE_TAX_EXEMPT_LIMIT)

	if annual_taxable_earning <= exempt_limit:
		return 0, 0

	relief = get_belize_personal_relief(annual_taxable_earning)
	chargeable_income = max(0, annual_taxable_earning - relief)
	tax_before_deduction = chargeable_income * BELIZE_TAX_RATE
	tax_payable = max(0, tax_before_deduction - BELIZE_STANDARD_TAX_DEDUCTION)
	return flt(tax_payable, 2), 0


def apply_regional_deductions(salary_slip):
	"""Belize statutory deductions are applied via apply_social_security_deductions."""
	pass
