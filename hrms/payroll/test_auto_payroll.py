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
	get_payroll_agent_buckets,
	get_payroll_customers,
	get_last_working_period,
	get_working_period_end,
	plan_payroll,
	_safe_plan_payroll,
	process_automatic_payroll,
	resolve_custom_pay_period,
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
		# Thursday 3 Sep 2026: last 10 weekdays start on Friday 21 Aug
		self.assertEqual(
			get_last_working_period(10, as_of="2026-09-03"),
			{"start_date": "2026-08-21", "end_date": "2026-09-03"},
		)

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

	def test_preview_when_disabled(self):
		frappe.db.set_single_value("Payroll Settings", "enable_automatic_payroll", 0)
		result = plan_payroll(every_agent=True, force=True)
		self.assertFalse(result["can_create"])
		self.assertFalse(result["entries"])
		self.assertIn("turned off", result["message"].lower())

	def test_preview_defaults_to_last_ten_working_days(self):
		frappe.db.set_single_value(
			"Payroll Settings",
			{
				"enable_automatic_payroll": 1,
				"automatic_payroll_company": "_Test Company",
				"automatic_payroll_weekly_days": 5,
				"automatic_payroll_fortnightly_days": 0,
				"automatic_payroll_monthly_days": 0,
			},
			update_modified=False,
		)
		period = get_last_working_period()
		result = _safe_plan_payroll(every_agent=True)
		self.assertEqual(result.get("start_date"), period["start_date"])
		self.assertEqual(result.get("end_date"), period["end_date"])

	def test_custom_pay_period_uses_selected_dates(self):
		start, end = resolve_custom_pay_period({"interval": 5}, "2026-07-18", "2026-07-24")
		self.assertEqual(start, date(2026, 7, 18))
		self.assertEqual(end, date(2026, 7, 24))

	def test_custom_pay_period_fills_end_from_interval(self):
		start, end = resolve_custom_pay_period({"interval": 5}, "2026-07-20", None)
		self.assertEqual(start, date(2026, 7, 20))
		self.assertEqual(end, add_working_days(date(2026, 7, 20), 5))

	def test_custom_pay_period_rejects_inverted_range(self):
		self.assertRaises(
			frappe.ValidationError,
			resolve_custom_pay_period,
			{"interval": 5},
			"2026-07-24",
			"2026-07-18",
		)

	def test_plan_payroll_uses_custom_dates(self):
		frappe.db.set_single_value(
			"Payroll Settings",
			{
				"enable_automatic_payroll": 1,
				"automatic_payroll_company": "_Test Company",
				"automatic_payroll_weekly_days": 5,
				"automatic_payroll_fortnightly_days": 0,
				"automatic_payroll_monthly_days": 0,
			},
			update_modified=False,
		)
		result = plan_payroll(
			every_agent=True, force=True, start_date="2026-07-18", end_date="2026-07-24"
		)
		if result.get("entries"):
			self.assertEqual(result.get("start_date"), "2026-07-18")
			self.assertEqual(result.get("end_date"), "2026-07-24")
			for entry in result["entries"]:
				self.assertEqual(entry["start_date"], "2026-07-18")
				self.assertEqual(entry["end_date"], "2026-07-24")

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

	def test_get_payroll_agent_buckets_is_one_run_for_all_agents(self):
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		from hrms.setup import get_custom_fields

		create_custom_fields(get_custom_fields(), ignore_validate=True)
		if not frappe.get_meta("Employee").has_field("bill_to_customer"):
			self.skipTest("Employee.bill_to_customer is not configured")
		if not frappe.get_meta("Payroll Entry").has_field("customer"):
			self.skipTest("Payroll Entry.customer is not configured")

		from erpnext.setup.doctype.employee.test_employee import make_employee

		company = "_Test Company"
		empty_client = "_Test Payroll Empty Client"
		if not frappe.db.exists("Customer", empty_client):
			customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
			territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": empty_client,
					"customer_type": "Company",
					"customer_group": customer_group,
					"territory": territory,
				}
			).insert(ignore_permissions=True)

		assigned_client = "_Test Payroll Assigned Client"
		if not frappe.db.exists("Customer", assigned_client):
			customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
			territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": assigned_client,
					"customer_type": "Company",
					"customer_group": customer_group,
					"territory": territory,
				}
			).insert(ignore_permissions=True)

		employee = make_employee("payroll.bucket.assigned@example.com", company=company)
		frappe.db.set_value("Employee", employee, "bill_to_customer", assigned_client)

		customers = get_payroll_customers(company)
		self.assertIn(assigned_client, customers)
		self.assertNotIn(empty_client, customers)

		buckets = get_payroll_agent_buckets(company)
		self.assertEqual(len(buckets), 1)
		self.assertFalse(buckets[0].get("customer"))
		self.assertFalse(buckets[0].get("customer_is_unassigned"))

		frappe.db.set_single_value(
			"Payroll Settings",
			{
				"enable_automatic_payroll": 1,
				"automatic_payroll_company": company,
				"automatic_payroll_weekly_days": 5,
				"automatic_payroll_fortnightly_days": 0,
				"automatic_payroll_monthly_days": 0,
			},
			update_modified=False,
		)
		preview = plan_payroll(
			every_agent=True, force=True, start_date="2026-07-18", end_date="2026-07-24"
		)
		self.assertTrue(preview.get("entries"))
		self.assertEqual(len(preview["entries"]), 1)
		self.assertFalse(preview["entries"][0]["customer"])
		self.assertEqual(preview["entries"][0]["customer_label"], "All Agents")
		self.assertIn(frappe.db.get_value("Employee", employee, "employee_name"), preview["entries"][0]["agent_names"])
