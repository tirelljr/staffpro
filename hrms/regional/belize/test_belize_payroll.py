# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import unittest

import frappe

from hrms.regional.belize.utils import (
	calculate_tax_by_tax_slab,
	get_belize_personal_relief,
)
from hrms.payroll.social_security import calculate_contribution


class TestBelizeIncomeTax(unittest.TestCase):
	def _slab(self):
		return frappe._dict(tax_relief_limit=26000)

	def test_exempt_at_or_below_26000(self):
		for amount in (0, 25000, 26000):
			tax, other = calculate_tax_by_tax_slab(amount, self._slab())
			self.assertEqual(tax, 0)
			self.assertEqual(other, 0)

	def test_tier_one_relief_27000(self):
		# $27,000 - $24,600 = $2,400 chargeable -> $600 tax -> $500 payable
		tax, _ = calculate_tax_by_tax_slab(27000, self._slab())
		self.assertEqual(tax, 500)

	def test_tier_two_relief_28000(self):
		# $28,000 - $22,600 = $5,400 -> $1,350 -> $1,250
		tax, _ = calculate_tax_by_tax_slab(28000, self._slab())
		self.assertEqual(tax, 1250)

	def test_tier_three_relief_30000(self):
		# $30,000 - $19,600 = $10,400 -> $2,600 -> $2,500
		tax, _ = calculate_tax_by_tax_slab(30000, self._slab())
		self.assertEqual(tax, 2500)

	def test_personal_relief_boundaries(self):
		self.assertEqual(get_belize_personal_relief(26001), 24600)
		self.assertEqual(get_belize_personal_relief(27000), 24600)
		self.assertEqual(get_belize_personal_relief(27001), 22600)
		self.assertEqual(get_belize_personal_relief(29000), 22600)
		self.assertEqual(get_belize_personal_relief(29001), 19600)


class TestBelizeFortnightlySocialSecurity(unittest.TestCase):
	def test_fortnightly_doubles_weekly_contribution(self):
		result = calculate_contribution(
			gross_pay=160,
			payroll_frequency="Fortnightly",
			start_date="2026-05-04",
			end_date="2026-05-17",
			date_of_birth="1990-01-01",
		)
		self.assertEqual(result["weekly_earnings"], 80)
		self.assertAlmostEqual(result["weeks"], 2.0)
		self.assertEqual(result["employee_amount"], 3.38)
		self.assertEqual(result["employer_amount"], 14.62)
