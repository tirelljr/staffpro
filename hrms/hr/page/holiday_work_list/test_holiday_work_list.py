# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import getdate

from hrms.hr.doctype.holiday_work_election.holiday_work_election import set_holiday_work_election
from hrms.hr.doctype.holiday_work_election.test_holiday_work_election import (
	add_public_holiday,
	make_election_employee,
	next_weekday,
)
from hrms.hr.page.holiday_work_list.holiday_work_list import get_holiday_work_list, get_upcoming_holidays
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list
from hrms.tests.utils import HRMSTestSuite


class TestHolidayWorkList(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.holiday_list = make_holiday_list(
			list_name="HWE Admin Holiday List",
			from_date=getdate().replace(month=1, day=1),
			to_date=getdate().replace(month=12, day=31),
		)
		self.weekday = next_weekday()
		add_public_holiday(self.holiday_list, self.weekday, "Admin Public Holiday")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_working_list_only_includes_elections(self):
		working, _working_user = make_election_employee("hwe.admin.work@example.com", self.holiday_list)
		off, _off_user = make_election_employee("hwe.admin.off@example.com", self.holiday_list)
		set_holiday_work_election(working, self.weekday, 1)

		holidays = get_upcoming_holidays()
		match = next(row for row in holidays if row["holiday_date"] == str(self.weekday))
		self.assertEqual(match["description"], "Admin Public Holiday")
		self.assertGreaterEqual(match["working_count"], 1)

		roster = get_holiday_work_list(str(self.weekday))
		by_employee = {row["employee"]: row for row in roster["details"]}
		self.assertTrue(by_employee[working]["will_work"])
		self.assertFalse(by_employee[off]["will_work"])
		self.assertEqual(by_employee[working]["status"], "Working")
		self.assertEqual(by_employee[off]["status"], "Not Working")
		self.assertGreaterEqual(roster["working_count"], 1)
		self.assertIn(off, {row["employee"] for row in roster["details"] if not row["will_work"]})

	def test_admin_api_is_hr_only(self):
		_employee, user = make_election_employee("hwe.admin.deny@example.com", self.holiday_list)
		frappe.set_user(user)
		self.assertRaises(frappe.PermissionError, get_upcoming_holidays)
		self.assertRaises(frappe.PermissionError, get_holiday_work_list, str(self.weekday))
