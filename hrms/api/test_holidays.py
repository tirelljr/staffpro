# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import getdate

from hrms.api import get_holidays_for_employee, set_holiday_work_election
from hrms.hr.doctype.holiday_work_election.test_holiday_work_election import (
	add_public_holiday,
	make_election_employee,
	next_weekday,
)
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list
from hrms.tests.utils import HRMSTestSuite


class TestHolidayWorkElectionAPI(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.holiday_list = make_holiday_list(
			list_name="HWE API Holiday List",
			from_date=getdate().replace(month=1, day=1),
			to_date=getdate().replace(month=12, day=31),
		)
		self.weekday = next_weekday()
		add_public_holiday(self.holiday_list, self.weekday, "API Public Holiday")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_employee_can_fetch_own_holidays_without_holiday_list_permission(self):
		employee, user = make_election_employee("hwe.api.own@example.com", self.holiday_list)
		frappe.set_user(user)
		holidays = get_holidays_for_employee(employee)
		dates = {row["holiday_date"] for row in holidays}
		self.assertIn(str(self.weekday), dates)
		holiday = next(row for row in holidays if row["holiday_date"] == str(self.weekday))
		self.assertTrue(holiday["is_work_day"])
		self.assertTrue(holiday["can_toggle"])
		self.assertFalse(holiday["will_work"])
		self.assertEqual(holiday["description"], "API Public Holiday")

	def test_employee_cannot_fetch_another_employees_holidays(self):
		_employee_one, user_one = make_election_employee("hwe.api.one@example.com", self.holiday_list)
		employee_two, _user_two = make_election_employee("hwe.api.two@example.com", self.holiday_list)

		frappe.set_user(user_one)
		self.assertRaises(frappe.PermissionError, get_holidays_for_employee, employee_two)

	def test_toggle_updates_will_work(self):
		employee, user = make_election_employee("hwe.api.toggle@example.com", self.holiday_list)
		frappe.set_user(user)
		set_holiday_work_election(employee, str(self.weekday), 1)
		holiday = next(
			row for row in get_holidays_for_employee(employee) if row["holiday_date"] == str(self.weekday)
		)
		self.assertTrue(holiday["will_work"])
