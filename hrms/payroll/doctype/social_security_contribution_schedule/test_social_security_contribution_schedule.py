# Copyright (c) 2026, Staff Pro BPO and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_years, flt, getdate

from hrms.payroll.social_security import (
	SS_SCHEME_INJURY_ONLY,
	SS_SCHEME_STANDARD,
	calculate_social_security_contribution,
	find_wage_band,
	get_employee_age,
	get_period_weeks,
	is_injury_only_scheme,
	seed_default_ss_schedule,
)


class TestSocialSecurity(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.schedule_name = seed_default_ss_schedule(currency="USD")

	def test_seeded_schedule_has_thirteen_bands(self):
		schedule = frappe.get_doc("Social Security Contribution Schedule", self.schedule_name)
		self.assertEqual(len(schedule.wage_bands), 13)
		self.assertEqual(flt(schedule.injury_only_employer_amount), 2.60)
		self.assertEqual(flt(schedule.injury_only_employee_amount), 0)

	def test_band_lookup_under_70(self):
		schedule = frappe.get_doc("Social Security Contribution Schedule", self.schedule_name)
		band = find_wage_band(schedule, 55)
		self.assertEqual(flt(band.weekly_insurable_earnings), 55)
		self.assertEqual(flt(band.employee_amount), 1.03)
		self.assertEqual(flt(band.employer_amount), 4.47)

	def test_band_lookup_mid_range(self):
		schedule = frappe.get_doc("Social Security Contribution Schedule", self.schedule_name)
		band = find_wage_band(schedule, 280)
		self.assertEqual(band.band_label, "$260.00 - $299.99")
		self.assertEqual(flt(band.employee_amount), 9.94)
		self.assertEqual(flt(band.employer_amount), 18.06)

	def test_band_lookup_over_ceiling(self):
		schedule = frappe.get_doc("Social Security Contribution Schedule", self.schedule_name)
		band = find_wage_band(schedule, 900)
		self.assertEqual(band.band_label, "$500.00 - OVER")
		self.assertEqual(flt(band.employee_amount), 23.40)
		self.assertEqual(flt(band.employer_amount), 28.60)

	def test_injury_only_age_rules(self):
		self.assertFalse(is_injury_only_scheme(59, False))
		self.assertFalse(is_injury_only_scheme(60, False))
		self.assertTrue(is_injury_only_scheme(60, True))
		self.assertTrue(is_injury_only_scheme(64, True))
		self.assertTrue(is_injury_only_scheme(65, False))
		self.assertTrue(is_injury_only_scheme(70, False))

	def test_employee_age(self):
		as_of = getdate("2026-08-17")
		self.assertEqual(get_employee_age("1960-08-17", as_of), 66)
		self.assertEqual(get_employee_age("1960-08-18", as_of), 65)
		self.assertEqual(get_employee_age("1966-08-17", as_of), 60)

	def test_fortnightly_weeks_full_period(self):
		weeks = get_period_weeks("Fortnightly", payment_days=10, total_working_days=10)
		self.assertEqual(weeks, 2.0)

	def test_fortnightly_weeks_with_unpaid_leave(self):
		weeks = get_period_weeks("Fortnightly", payment_days=5, total_working_days=10)
		self.assertEqual(weeks, 1.0)

	def test_fortnightly_standard_contribution(self):
		# Fortnight earnings $560 => weekly $280 => band $260-$299.99
		# employee 9.94 * 2 = 19.88, employer 18.06 * 2 = 36.12
		result = calculate_social_security_contribution(
			ss_eligible_earnings=560,
			payroll_frequency="Fortnightly",
			payment_days=10,
			total_working_days=10,
			schedule_name=self.schedule_name,
			date_of_birth="1990-01-01",
			as_of_date="2026-08-17",
			receiving_ss_benefit=False,
		)
		self.assertIsNotNone(result)
		self.assertEqual(result["scheme"], SS_SCHEME_STANDARD)
		self.assertEqual(result["wage_band"], "$260.00 - $299.99")
		self.assertEqual(flt(result["weeks"]), 2.0)
		self.assertEqual(flt(result["employee_amount"]), 19.88)
		self.assertEqual(flt(result["employer_amount"]), 36.12)

	def test_fortnightly_injury_only_for_senior(self):
		result = calculate_social_security_contribution(
			ss_eligible_earnings=560,
			payroll_frequency="Fortnightly",
			payment_days=10,
			total_working_days=10,
			schedule_name=self.schedule_name,
			date_of_birth="1955-01-01",
			as_of_date="2026-08-17",
			receiving_ss_benefit=False,
		)
		self.assertEqual(result["scheme"], SS_SCHEME_INJURY_ONLY)
		self.assertEqual(flt(result["employee_amount"]), 0)
		self.assertEqual(flt(result["employer_amount"]), 5.20)  # 2.60 * 2 weeks

	def test_injury_only_for_60_to_64_receiving_benefit(self):
		dob = add_years(getdate("2026-08-17"), -62)
		result = calculate_social_security_contribution(
			ss_eligible_earnings=560,
			payroll_frequency="Fortnightly",
			payment_days=10,
			total_working_days=10,
			schedule_name=self.schedule_name,
			date_of_birth=dob,
			as_of_date="2026-08-17",
			receiving_ss_benefit=True,
		)
		self.assertEqual(result["scheme"], SS_SCHEME_INJURY_ONLY)
		self.assertEqual(flt(result["employer_amount"]), 5.20)
