# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from frappe.utils import add_days, add_years, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.desk_dashboard import get_upcoming_absences, get_upcoming_celebrations
from hrms.tests.utils import HRMSTestSuite


class TestDeskDashboardCelebrations(HRMSTestSuite):
	def setUp(self):
		self.company = "_Test Company"

	def test_celebrations_use_date_of_birth_and_date_of_joining(self):
		today = getdate()
		birthday = add_days(today, 2)
		anniversary = add_days(today, 3)
		date_of_birth = add_years(birthday, -32)
		date_of_joining = add_years(anniversary, -4)

		employee = make_employee(
			"dash.celebrations@example.com",
			company=self.company,
			first_name="Celeb",
			last_name="Dates",
			date_of_birth=date_of_birth,
			date_of_joining=date_of_joining,
		)

		payload = get_upcoming_celebrations(period="weekly", company=self.company)
		mine = [event for event in payload["events"] if event["employee"] == employee]
		by_type = {event["event_type"]: event for event in mine}

		self.assertFalse(payload["fallback"])
		self.assertIn("birthday", by_type)
		self.assertEqual(by_type["birthday"]["day"], birthday.day)
		self.assertEqual(by_type["birthday"]["month"], birthday.strftime("%b"))
		self.assertEqual(getdate(by_type["birthday"]["source_date"]), getdate(date_of_birth))

		self.assertIn("anniversary", by_type)
		self.assertEqual(by_type["anniversary"]["day"], anniversary.day)
		self.assertEqual(by_type["anniversary"]["month"], anniversary.strftime("%b"))
		self.assertEqual(by_type["anniversary"]["years_completed"], 4)
		self.assertEqual(getdate(by_type["anniversary"]["source_date"]), getdate(date_of_joining))


class TestDeskDashboardAbsences(HRMSTestSuite):
	def setUp(self):
		self.company = "_Test Company"

	def test_absences_show_upcoming_leave_applications(self):
		# The HRMS bootstrap test data creates Leave Applications in May 2013.
		frappe.flags.current_date = getdate("2013-05-02")

		payload = get_upcoming_absences(period="monthly", company=self.company)
		employees = {row["employee"] for row in payload["rows"]}
		self.assertEqual(len(payload["rows"]), 2)
		self.assertIn("_T-Employee-00001", employees)
		self.assertIn("_T-Employee-00002", employees)

		types = {row["leave_type"] for row in payload["rows"]}
		self.assertEqual(types, {"_Test Leave Type"})
