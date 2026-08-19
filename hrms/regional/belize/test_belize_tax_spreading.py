# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import unittest
from unittest.mock import patch

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.payroll.doctype.income_tax_slab.income_tax_slab import calculate_tax_by_tax_slab
from hrms.payroll.doctype.payroll_period.payroll_period import get_period_factor
from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip
from hrms.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure
from hrms.regional.belize.setup import create_belize_income_tax_slabs
from hrms.tests.utils import HRMSTestSuite


class TestBelizeFortnightlyTaxSpreading(HRMSTestSuite):
	def setUp(self):
		super().setUp()
		frappe.flags.apply_social_security = False
		self.company = "_Test Company"
		frappe.db.set_value("Company", self.company, "country", "Belize")

		if not frappe.db.exists("Salary Component", "BZ Test Basic"):
			frappe.get_doc(
				{
					"doctype": "Salary Component",
					"salary_component": "BZ Test Basic",
					"salary_component_abbr": "BZTB",
					"type": "Earning",
					"depends_on_payment_days": 0,
					"is_tax_applicable": 1,
				}
			).insert()

		if not frappe.db.exists("Salary Component", "Income Tax"):
			frappe.get_doc(
				{
					"doctype": "Salary Component",
					"salary_component": "Income Tax",
					"type": "Deduction",
					"is_income_tax_component": 1,
					"variable_based_on_taxable_salary": 1,
				}
			).insert()
		else:
			frappe.db.set_value(
				"Salary Component",
				"Income Tax",
				"variable_based_on_taxable_salary",
				1,
				update_modified=False,
			)

		create_belize_income_tax_slabs()
		self.tax_slab = frappe.db.get_value(
			"Income Tax Slab",
			{"company": self.company},
			"name",
			order_by="creation desc",
		) or frappe.db.get_value("Income Tax Slab", {"company": ["is", "not set"]}, "name")

		if not frappe.db.exists("Payroll Period", {"company": self.company}):
			frappe.get_doc(
				{
					"doctype": "Payroll Period",
					"company": self.company,
					"start_date": "2026-01-01",
					"end_date": "2026-12-31",
				}
			).insert()

	def tearDown(self):
		frappe.flags.apply_social_security = False
		frappe.db.set_value("Company", self.company, "country", "India")
		super().tearDown()

	def test_belize_override_used_for_belize_company(self):
		with patch("hrms.get_region", return_value="Belize"):
			tax, _ = calculate_tax_by_tax_slab(27000, frappe._dict(tax_relief_limit=26000))
		self.assertEqual(tax, 500)

	def test_fortnightly_tax_spread_over_remaining_periods(self):
		employee = make_employee(
			"bz_fortnight_agent@example.com",
			company=self.company,
			date_of_birth="1990-01-01",
			date_of_joining="2026-01-01",
		)
		annual_gross = 27000
		fortnightly_gross = annual_gross / 26

		structure = make_salary_structure(
			"BZ Fortnightly Structure",
			"Fortnightly",
			employee=employee,
			company=self.company,
			from_date="2026-01-01",
			earnings=[
				{
					"salary_component": "BZ Test Basic",
					"abbr": "BZTB",
					"amount": fortnightly_gross,
					"depends_on_payment_days": 0,
				}
			],
			deductions=[
				{
					"salary_component": "Income Tax",
					"abbr": "IT",
					"variable_based_on_taxable_salary": 1,
				}
			],
		)

		frappe.db.set_value(
			"Salary Structure Assignment",
			{"employee": employee, "salary_structure": structure.name, "docstatus": 1},
			"income_tax_slab",
			self.tax_slab,
		)

		slip = make_salary_slip(structure.name, employee=employee, posting_date="2026-01-01")
		slip.start_date = "2026-01-01"
		slip.end_date = "2026-01-14"
		slip.payroll_frequency = "Fortnightly"
		slip.calculate_net_pay()

		tax_row = next((d for d in slip.deductions if d.salary_component == "Income Tax"), None)
		self.assertIsNotNone(tax_row)
		self.assertAlmostEqual(tax_row.amount, 500 / 26, places=2)

		total_sub, remaining_sub = get_period_factor(
			employee,
			slip.start_date,
			slip.end_date,
			"Fortnightly",
			slip.payroll_period,
		)
		self.assertGreater(total_sub, 0)
		self.assertEqual(remaining_sub, total_sub)
