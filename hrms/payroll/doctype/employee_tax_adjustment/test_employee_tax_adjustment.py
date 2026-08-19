# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import unittest

import frappe

from hrms.payroll.tax_adjustments import (
	earning_is_tax_exempt,
	is_excluded_from_tax,
)


class TestTaxAdjustmentHelpers(unittest.TestCase):
	def test_exclude_from_tax_period(self):
		self.assertTrue(is_excluded_from_tax(frappe._dict(adjustment_type="Exclude from Tax Period")))
		self.assertFalse(is_excluded_from_tax(frappe._dict(adjustment_type="Include in Tax Period")))
		self.assertFalse(is_excluded_from_tax(None))

	def test_additional_salary_exclude_from_tax(self):
		additional = frappe._dict(exclude_from_tax=1)
		self.assertTrue(earning_is_tax_exempt("Bonus", None, additional))
		self.assertFalse(earning_is_tax_exempt("Bonus", None, frappe._dict(exclude_from_tax=0)))

	def test_excluded_component_list(self):
		adjustment = frappe._dict(
			adjustment_type="Include in Tax Period",
			exclude_bonuses=0,
			exclude_incentives=0,
			exclude_overtime=0,
			exclude_commissions=0,
			excluded_components=["Campaign Bonus"],
		)
		self.assertTrue(earning_is_tax_exempt("Campaign Bonus", adjustment))
		self.assertFalse(earning_is_tax_exempt("Basic", adjustment, frappe._dict(exclude_from_tax=0)))

	def test_apply_exclusions_to_earnings(self):
		from hrms.payroll.tax_adjustments import apply_tax_exclusions_to_earnings

		slip = frappe._dict(
			earnings=[
				frappe._dict(
					salary_component="Campaign Bonus",
					is_tax_applicable=1,
					deduct_full_tax_on_selected_payroll_date=1,
					additional_salary=None,
				),
				frappe._dict(
					salary_component="Basic",
					is_tax_applicable=1,
					deduct_full_tax_on_selected_payroll_date=0,
					additional_salary=None,
				),
			]
		)
		adjustment = frappe._dict(excluded_components=["Campaign Bonus"], exclude_bonuses=0)
		apply_tax_exclusions_to_earnings(slip, adjustment)
		self.assertEqual(slip.earnings[0].is_tax_applicable, 0)
		self.assertEqual(slip.earnings[1].is_tax_applicable, 1)
