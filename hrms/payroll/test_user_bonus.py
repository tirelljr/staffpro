# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, getdate

from hrms.payroll.user_bonus import evaluate_attendance_plan, plan_window


class TestUserBonusRules(FrappeTestCase):
	def test_pays_period_share_when_attendance_meets_target(self):
		result = evaluate_attendance_plan(92, 90, 500, 3, "No Bonus")
		self.assertEqual(result["eligible"], 1)
		self.assertEqual(result["is_deduction"], 0)
		self.assertEqual(result["amount"], 166.67)

	def test_withholds_bonus_when_below_target(self):
		result = evaluate_attendance_plan(80, 90, 500, 3, "No Bonus")
		self.assertEqual(result["eligible"], 0)
		self.assertEqual(result["is_deduction"], 0)
		self.assertEqual(result["amount"], 0)

	def test_deducts_period_share_when_below_target(self):
		result = evaluate_attendance_plan(80, 90, 500, 3, "Deduct")
		self.assertEqual(result["eligible"], 0)
		self.assertEqual(result["is_deduction"], 1)
		self.assertEqual(result["amount"], 166.67)

	def test_plan_window_uses_months_and_does_not_start_before_joining(self):
		start, end = plan_window("2026-09-08", 3, "2026-08-01")
		self.assertEqual(getdate(end), getdate("2026-09-08"))
		self.assertEqual(getdate(start), getdate("2026-08-01"))

	def test_plan_window_looks_back_full_period(self):
		start, end = plan_window("2026-09-08", 3, "2025-01-01")
		self.assertEqual(getdate(start), add_months(getdate("2026-09-08"), -3))
		self.assertEqual(getdate(end), getdate("2026-09-08"))
