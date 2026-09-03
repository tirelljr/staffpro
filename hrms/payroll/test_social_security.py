# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import unittest

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip
from hrms.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure
from hrms.payroll.report.social_security_deductions.social_security_deductions import execute as ss_report
from hrms.payroll.social_security import (
	BELIZE_SSB_2022_BANDS,
	SS_CATEGORY_INJURY_ONLY,
	SS_CATEGORY_STANDARD,
	SS_EMPLOYEE_COMPONENT,
	calculate_contribution,
	contribution_weeks,
	ensure_employee_ss_fields,
	ensure_ss_salary_components,
	get_age,
	is_injury_only,
	lookup_band,
	seed_belize_ssb_2022_table,
	weekly_earnings_from_gross,
)
from hrms.tests.utils import HRMSTestSuite


class TestSocialSecurityCalculator(unittest.TestCase):
	def test_under_70_band(self):
		band = lookup_band(55, BELIZE_SSB_2022_BANDS)
		self.assertEqual(band["band_label"], "UNDER $70.00")
		self.assertEqual(band["employee_amount"], 1.03)
		self.assertEqual(band["employer_amount"], 4.47)

	def test_mid_band_edge(self):
		band = lookup_band(70, BELIZE_SSB_2022_BANDS)
		self.assertEqual(band["band_label"], "$70.00 - $109.99")
		band = lookup_band(109.99, BELIZE_SSB_2022_BANDS)
		self.assertEqual(band["band_label"], "$70.00 - $109.99")

	def test_ceiling_band(self):
		band = lookup_band(500, BELIZE_SSB_2022_BANDS)
		self.assertEqual(band["band_label"], "$500.00 - OVER")
		self.assertEqual(band["employee_amount"], 23.40)
		self.assertEqual(band["employer_amount"], 28.60)
		band = lookup_band(2500, BELIZE_SSB_2022_BANDS)
		self.assertEqual(band["insurable_earnings"], 520)

	def test_weekly_earnings_conversion(self):
		self.assertEqual(weekly_earnings_from_gross(80, "Weekly"), 80)
		self.assertEqual(weekly_earnings_from_gross(160, "Fortnightly"), 80)
		self.assertAlmostEqual(weekly_earnings_from_gross(520, "Monthly"), 520 * 12 / 52)
		self.assertEqual(weekly_earnings_from_gross(10, "Daily"), 70)

	def test_contribution_weeks(self):
		self.assertEqual(contribution_weeks("Weekly", "2026-05-04", "2026-05-10"), 1)
		self.assertAlmostEqual(contribution_weeks("Monthly", "2026-05-01", "2026-05-31"), 31 / 7)

	def test_age_and_injury_only(self):
		self.assertEqual(get_age("1960-05-10", "2026-05-10"), 66)
		self.assertEqual(get_age("1966-05-11", "2026-05-10"), 59)
		self.assertTrue(is_injury_only(65, False))
		self.assertTrue(is_injury_only(62, True))
		self.assertFalse(is_injury_only(62, False))
		self.assertFalse(is_injury_only(40, True))

	def test_standard_weekly_contribution(self):
		result = calculate_contribution(
			gross_pay=80,
			payroll_frequency="Weekly",
			start_date="2026-05-04",
			end_date="2026-05-10",
			date_of_birth="1990-01-01",
		)
		self.assertEqual(result["category"], SS_CATEGORY_STANDARD)
		self.assertEqual(result["employee_amount"], 1.69)
		self.assertEqual(result["employer_amount"], 7.31)

	def test_injury_only_age_65(self):
		result = calculate_contribution(
			gross_pay=500,
			payroll_frequency="Weekly",
			start_date="2026-05-04",
			end_date="2026-05-10",
			date_of_birth="1950-01-01",
			injury_only_employee_amount=0,
			injury_only_employer_amount=2.60,
		)
		self.assertEqual(result["category"], SS_CATEGORY_INJURY_ONLY)
		self.assertEqual(result["employee_amount"], 0)
		self.assertEqual(result["employer_amount"], 2.60)

	def test_injury_only_age_60_with_benefit(self):
		result = calculate_contribution(
			gross_pay=300,
			payroll_frequency="Weekly",
			start_date="2026-05-04",
			end_date="2026-05-10",
			date_of_birth="1964-05-04",
			receiving_ss_benefit=True,
			injury_only_employer_amount=2.60,
		)
		self.assertEqual(result["category"], SS_CATEGORY_INJURY_ONLY)
		self.assertEqual(result["employee_amount"], 0)

	def test_zero_gross_skips_category(self):
		result = calculate_contribution(
			gross_pay=0,
			payroll_frequency="Weekly",
			start_date="2026-05-04",
			end_date="2026-05-10",
			date_of_birth="1990-01-01",
		)
		self.assertEqual(result["category"], "")
		self.assertEqual(result["employee_amount"], 0)

	def test_monthly_scales_weekly_amount(self):
		monthly_gross = 3000
		result = calculate_contribution(
			gross_pay=monthly_gross,
			payroll_frequency="Monthly",
			start_date="2026-05-01",
			end_date="2026-05-31",
			date_of_birth="1990-01-01",
		)
		self.assertEqual(result["category"], SS_CATEGORY_STANDARD)
		self.assertEqual(result["wage_band"], "$500.00 - OVER")
		self.assertAlmostEqual(result["employee_amount"], round(23.40 * 31 / 7, 2))


class TestSocialSecuritySalarySlip(HRMSTestSuite):
	def setUp(self):
		super().setUp()
		frappe.flags.apply_social_security = True
		ensure_ss_salary_components()
		ensure_employee_ss_fields()

		if not frappe.db.exists("Salary Component", "SS Test Basic"):
			frappe.get_doc(
				{
					"doctype": "Salary Component",
					"salary_component": "SS Test Basic",
					"salary_component_abbr": "SSTB",
					"type": "Earning",
					"depends_on_payment_days": 0,
					"is_tax_applicable": 0,
				}
			).insert()

		seed_belize_ssb_2022_table()

	def tearDown(self):
		frappe.flags.apply_social_security = False
		super().tearDown()

	def test_ss_component_gets_company_account(self):
		ensure_ss_salary_components("_Test Company")
		account = frappe.db.get_value(
			"Salary Component Account",
			{"parent": SS_EMPLOYEE_COMPONENT, "company": "_Test Company"},
			"account",
		)
		self.assertTrue(account)
		self.assertTrue(frappe.db.exists("Account", account))

	def test_weekly_slip_deducts_ss_from_net_pay(self):
		employee = make_employee(
			"ss_weekly_agent@example.com",
			company="_Test Company",
			date_of_birth="1990-05-01",
			date_of_joining="2018-01-01",
		)
		if frappe.get_meta("Employee").has_field("social_security_number"):
			frappe.db.set_value("Employee", employee, "social_security_number", "001234567")
		structure = make_salary_structure(
			"SS Weekly Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date="2026-05-04",
			earnings=[
				{
					"salary_component": "SS Test Basic",
					"abbr": "SSTB",
					"amount": 80,
					"depends_on_payment_days": 0,
				}
			],
			deductions=[],
		)
		slip = make_salary_slip(structure.name, employee=employee, posting_date="2026-05-04")
		if not slip.start_date:
			slip.start_date = "2026-05-04"
			slip.end_date = "2026-05-10"
			slip.payroll_frequency = "Weekly"
			slip.calculate_net_pay()

		ss_row = next((d for d in slip.deductions if d.salary_component == SS_EMPLOYEE_COMPONENT), None)
		self.assertIsNotNone(ss_row)
		self.assertEqual(ss_row.amount, 1.69)
		self.assertEqual(slip.ss_employee_amount, 1.69)
		self.assertEqual(slip.ss_employer_amount, 7.31)
		self.assertEqual(slip.ss_category, SS_CATEGORY_STANDARD)
		self.assertEqual(slip.ss_number, "001234567")
		self.assertTrue(slip.employee_name)
		self.assertEqual(slip.net_pay, slip.gross_pay - slip.total_deduction)

	def test_senior_agent_injury_only(self):
		employee = make_employee(
			"ss_senior_agent@example.com",
			company="_Test Company",
			date_of_birth="1950-01-01",
			date_of_joining="2018-01-01",
		)
		structure = make_salary_structure(
			"SS Senior Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date="2026-05-04",
			earnings=[
				{
					"salary_component": "SS Test Basic",
					"abbr": "SSTB",
					"amount": 500,
					"depends_on_payment_days": 0,
				}
			],
			deductions=[],
		)
		slip = make_salary_slip(structure.name, employee=employee, posting_date="2026-05-04")
		if not slip.start_date:
			slip.start_date = "2026-05-04"
			slip.end_date = "2026-05-10"
			slip.payroll_frequency = "Weekly"
			slip.calculate_net_pay()

		ss_row = next((d for d in slip.deductions if d.salary_component == SS_EMPLOYEE_COMPONENT), None)
		self.assertIsNotNone(ss_row)
		self.assertEqual(ss_row.amount, 0)
		self.assertEqual(slip.ss_category, SS_CATEGORY_INJURY_ONLY)
		self.assertEqual(slip.ss_employer_amount, 2.60)

	def test_apply_social_security_without_contribution_table(self):
		from unittest.mock import patch

		employee = make_employee(
			"ss_no_table_agent@example.com",
			company="_Test Company",
			date_of_birth="1990-05-01",
			date_of_joining="2018-01-01",
		)
		structure = make_salary_structure(
			"SS No Table Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date="2026-05-04",
			earnings=[
				{
					"salary_component": "SS Test Basic",
					"abbr": "SSTB",
					"amount": 80,
					"depends_on_payment_days": 0,
				}
			],
			deductions=[],
		)
		with patch("hrms.payroll.social_security.get_active_contribution_table", return_value=None):
			slip = make_salary_slip(structure.name, employee=employee, posting_date="2026-05-04")
			if not slip.start_date:
				slip.start_date = "2026-05-04"
				slip.end_date = "2026-05-10"
				slip.payroll_frequency = "Weekly"
				slip.calculate_net_pay()

		ss_row = next((d for d in slip.deductions if d.salary_component == SS_EMPLOYEE_COMPONENT), None)
		self.assertIsNotNone(ss_row)
		self.assertEqual(ss_row.amount, 1.69)
		self.assertEqual(slip.ss_employee_amount, 1.69)

	def test_payroll_row_computes_ss_when_slip_amount_is_zero(self):
		from hrms.hr.desk_dashboard import _ss_amount_for_slip

		employee = make_employee(
			"ss_dashboard_agent@example.com",
			company="_Test Company",
			date_of_birth="1990-05-01",
			date_of_joining="2018-01-01",
		)
		amount = _ss_amount_for_slip(
			frappe._dict(
				ss_employee_amount=0,
				gross_pay=80,
				net_pay=80,
				payroll_frequency="Weekly",
				start_date="2026-05-04",
				end_date="2026-05-10",
				employee=employee,
				company="_Test Company",
			)
		)
		self.assertEqual(amount, 1.69)

	def test_report_returns_columns(self):
		columns, data = ss_report(
			{"company": "_Test Company", "from_date": "2026-01-01", "to_date": "2026-12-31"}
		)
		self.assertTrue(columns)
		fieldnames = [col["fieldname"] for col in columns]
		self.assertIn("ss_employee_amount", fieldnames)
		self.assertIn("employee_name", fieldnames)
		self.assertIn("ss_number", fieldnames)

	def test_as_list_parses_employee_filters(self):
		from hrms.payroll.report.social_security_deductions.social_security_deductions import as_list

		self.assertEqual(as_list(None), [])
		self.assertEqual(as_list("EMP-00003"), ["EMP-00003"])
		self.assertEqual(as_list(["EMP-00003", "EMP-00005"]), ["EMP-00003", "EMP-00005"])
		self.assertEqual(as_list('["EMP-00003", "EMP-00005"]'), ["EMP-00003", "EMP-00005"])

	def test_zip_export_requires_more_than_one_agent(self):
		from hrms.payroll.report.social_security_deductions.social_security_deductions import download_zip

		with self.assertRaises(frappe.ValidationError):
			download_zip({"selected_employees": ["EMP-00003"], "require_multiple": 1})
