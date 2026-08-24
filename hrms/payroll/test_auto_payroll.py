# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import date

import frappe
from frappe.utils import getdate

from hrms.payroll.auto_payroll import (
	add_working_days,
	canonical_frequency,
	days_for_frequency,
	frequency_label,
	get_pay_period,
	get_working_period_end,
	process_automatic_payroll,
	set_automatic_payroll_interval,
	subtract_working_days,
)
from hrms.tests.utils import HRMSTestSuite


class TestAutoPayroll(HRMSTestSuite):
	def setUp(self):
		self._previous = {
			"enable_automatic_payroll": frappe.db.get_single_value(
				"Payroll Settings", "enable_automatic_payroll"
			),
			"automatic_payroll_interval_days": frappe.db.get_single_value(
				"Payroll Settings", "automatic_payroll_interval_days"
			),
			"automatic_payroll_company": frappe.db.get_single_value(
				"Payroll Settings", "automatic_payroll_company"
			),
			"automatic_payroll_weekly_days": frappe.db.get_single_value(
				"Payroll Settings", "automatic_payroll_weekly_days"
			),
			"automatic_payroll_fortnightly_days": frappe.db.get_single_value(
				"Payroll Settings", "automatic_payroll_fortnightly_days"
			),
			"automatic_payroll_monthly_days": frappe.db.get_single_value(
				"Payroll Settings", "automatic_payroll_monthly_days"
			),
		}

	def tearDown(self):
		frappe.db.set_single_value("Payroll Settings", self._previous, update_modified=False)

	def test_working_days_skip_weekends(self):
		# Monday 3 Aug 2026 + 10 weekdays = Friday 14 Aug 2026
		self.assertEqual(add_working_days(date(2026, 8, 3), 10), date(2026, 8, 14))
		# Saturday start still lands on the same Friday
		self.assertEqual(add_working_days(date(2026, 8, 1), 10), date(2026, 8, 14))
		self.assertEqual(subtract_working_days(date(2026, 8, 14), 10), date(2026, 8, 3))
		self.assertEqual(get_working_period_end("2026-08-03", 10)["end_date"], "2026-08-14")

	def test_pay_period_from_last_end(self):
		start, end = get_pay_period(
			interval=10,
			as_of=date(2026, 8, 20),
			company="_Test Company",
			last_end=date(2026, 8, 10),
		)
		self.assertEqual(getdate(start), date(2026, 8, 11))
		self.assertEqual(getdate(end), date(2026, 8, 24))

	def test_first_period_ends_yesterday(self):
		start, end = get_pay_period(
			interval=10,
			as_of=date(2026, 8, 21),
			company="_Test Company",
			last_end="",
			cycle_start=None,
		)
		self.assertEqual(getdate(end), date(2026, 8, 20))
		self.assertEqual(getdate(start), date(2026, 8, 7))

	def test_cycle_start_anchor(self):
		start, end = get_pay_period(
			interval=10,
			as_of=date(2026, 8, 20),
			company="_Test Company",
			last_end="",
			cycle_start=date(2026, 8, 1),
		)
		self.assertEqual(getdate(start), date(2026, 8, 1))
		self.assertEqual(getdate(end), date(2026, 8, 14))

	def test_open_period_is_not_due(self):
		_start, end = get_pay_period(
			interval=10,
			as_of=date(2026, 8, 20),
			company="_Test Company",
			last_end=date(2026, 8, 15),
		)
		self.assertEqual(getdate(end), date(2026, 8, 28))
		self.assertGreaterEqual(getdate(end), date(2026, 8, 20))

	def test_skips_when_disabled(self):
		frappe.db.set_single_value("Payroll Settings", "enable_automatic_payroll", 0)
		result = process_automatic_payroll(force=False)
		self.assertFalse(result["created"])
		self.assertIn("turned off", result["message"].lower())

	def test_set_automatic_payroll_interval(self):
		result = set_automatic_payroll_interval(
			weekly_days=7, fortnightly_days=14, monthly_days=30, enable=1
		)
		self.assertEqual(result["weekly_days"], 7)
		self.assertEqual(result["fortnightly_days"], 14)
		self.assertEqual(result["monthly_days"], 30)
		self.assertTrue(result["enabled"])
		self.assertEqual(
			frappe.db.get_single_value("Payroll Settings", "automatic_payroll_fortnightly_days"),
			14,
		)

	def test_frequency_aliases_and_days(self):
		self.assertEqual(canonical_frequency("2 Weeks"), "Fortnightly")
		self.assertEqual(canonical_frequency("2-weeks"), "Fortnightly")
		self.assertEqual(canonical_frequency("weekly"), "Weekly")
		self.assertEqual(frequency_label("Fortnightly"), "2-weeks")
		set_automatic_payroll_interval(weekly_days=5, fortnightly_days=12, monthly_days=28, enable=1)
		self.assertEqual(days_for_frequency("Weekly"), 5)
		self.assertEqual(days_for_frequency("2 Weeks"), 12)
		self.assertEqual(days_for_frequency("2-weeks"), 12)
		self.assertEqual(days_for_frequency("Monthly"), 28)

	def test_payroll_entry_uses_attendance_not_timesheets(self):
		from frappe.utils import cint

		from hrms.payroll.auto_payroll import build_payroll_entry

		if not frappe.db.get_value("Cost Center", {"company": "_Test Company", "is_group": 0}):
			self.skipTest("No cost center for _Test Company")

		settings = frappe.get_single("Payroll Settings")
		entry = build_payroll_entry(
			settings, "_Test Company", "2026-08-10", "2026-08-14", "Weekly"
		)
		self.assertEqual(cint(entry.salary_slip_based_on_timesheet), 0)
		self.assertEqual(entry.payroll_frequency, "Weekly")
		self.assertEqual(cint(entry.deduct_social_security), 1)
