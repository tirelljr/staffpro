# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.attendance.attendance import mark_attendance
from hrms.payroll.doctype.bonus_type.bonus_type import (
	BONUS_SALARY_COMPONENT,
	ensure_bonus_component_accounts,
	ensure_bonus_salary_component,
	seed_bonus_types,
)
from hrms.payroll.user_bonus import calculate_user_bonus
from hrms.tests.utils import HRMSTestSuite


class TestBonusType(HRMSTestSuite):
	def test_user_bonus_pays_when_attendance_meets_target(self):
		seed_bonus_types()
		as_of = getdate()
		employee = make_employee(
			"user.bonus.eligible@example.com",
			company="_Test Company",
			date_of_joining=add_days(as_of, -120),
		)
		frappe.db.set_value(
			"Employee",
			employee,
			{
				"user_bonus": 500,
				"user_bonus_period_months": 3,
				"user_bonus_attendance_target": 90,
				"user_bonus_if_below": "No Bonus",
			},
		)

		result = calculate_user_bonus(employee, "Attendance Bonus", as_of)
		self.assertEqual(result["auto_calculate"], 1)
		self.assertEqual(result["eligible"], 1)
		self.assertEqual(result["amount"], 166.67)
		self.assertEqual(result["is_deduction"], 0)

	def test_user_bonus_is_withheld_when_attendance_is_below_target(self):
		seed_bonus_types()
		as_of = getdate()
		employee = make_employee(
			"user.bonus.absent@example.com",
			company="_Test Company",
			date_of_joining=add_days(as_of, -120),
		)
		frappe.db.set_value(
			"Employee",
			employee,
			{
				"user_bonus": 500,
				"user_bonus_period_months": 3,
				"user_bonus_attendance_target": 90,
				"user_bonus_if_below": "No Bonus",
			},
		)
		for offset in range(20):
			mark_attendance(employee, add_days(as_of, -offset), "Absent")

		result = calculate_user_bonus(employee, "Attendance Bonus", as_of)
		self.assertEqual(result["eligible"], 0)
		self.assertEqual(result["amount"], 0)
		self.assertIn("below target", result["status"].lower())

	def test_bonus_component_account_is_auto_assigned(self):
		ensure_bonus_salary_component()
		frappe.db.delete("Salary Component Account", {"parent": BONUS_SALARY_COMPONENT, "company": "_Test Company"})
		mapped = ensure_bonus_component_accounts("_Test Company")
		self.assertTrue(mapped.get(f"{BONUS_SALARY_COMPONENT}:_Test Company"))
		self.assertTrue(
			frappe.db.get_value(
				"Salary Component Account",
				{"parent": BONUS_SALARY_COMPONENT, "company": "_Test Company"},
				"account",
			)
		)
