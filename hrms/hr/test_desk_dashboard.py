# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from frappe.utils import add_days, add_years, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.desk_dashboard import get_upcoming_celebrations
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
