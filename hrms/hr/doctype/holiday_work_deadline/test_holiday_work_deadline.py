# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import timedelta

import frappe
from frappe.utils import getdate, now_datetime

from hrms.hr.doctype.holiday_work_deadline.holiday_work_deadline import (
	apply_default_working_after_deadline,
	set_holiday_work_deadline,
)
from hrms.hr.doctype.holiday_work_election.holiday_work_election import (
	get_holiday_work_roster,
	get_upcoming_holidays_for_employee,
	set_holiday_work_election,
)
from hrms.hr.doctype.holiday_work_election.test_holiday_work_election import (
	add_public_holiday,
	make_election_employee,
	next_weekday,
)
from hrms.hr.page.holiday_work_list.holiday_work_list import get_holiday_work_list
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list
from hrms.tests.utils import HRMSTestSuite


class TestHolidayWorkDeadline(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.holiday_list = make_holiday_list(
			list_name="HWD Test Holiday List",
			from_date=getdate().replace(month=1, day=1),
			to_date=getdate().replace(month=12, day=31),
		)
		self.weekday = next_weekday()
		add_public_holiday(self.holiday_list, self.weekday, "Deadline Public Holiday")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Holiday Work Deadline", {"holiday_date": self.weekday})
		frappe.db.delete("Holiday Work Election", {"holiday_date": self.weekday})

	def test_non_responders_count_as_working_once_deadline_is_set(self):
		working, _working_user = make_election_employee("hwd.work@example.com", self.holiday_list)
		off, off_user = make_election_employee("hwd.off@example.com", self.holiday_list)
		silent, silent_user = make_election_employee("hwd.silent@example.com", self.holiday_list)

		deadline = now_datetime() + timedelta(days=1)
		set_holiday_work_deadline(self.weekday, deadline, "Deadline Public Holiday")
		set_holiday_work_election(off, self.weekday, 0)
		set_holiday_work_election(working, self.weekday, 1)

		roster = get_holiday_work_list(str(self.weekday))
		by_employee = {row["employee"]: row for row in roster["details"]}
		self.assertTrue(by_employee[working]["will_work"])
		self.assertFalse(by_employee[off]["will_work"])
		self.assertTrue(by_employee[silent]["will_work"])
		self.assertTrue(by_employee[silent]["assumed_working"])
		self.assertTrue(roster["response_deadline"])

		frappe.set_user(silent_user)
		holiday = next(
			row
			for row in get_upcoming_holidays_for_employee(silent)
			if row["holiday_date"] == str(self.weekday)
		)
		self.assertTrue(holiday["will_work"])
		self.assertTrue(holiday["can_toggle"])
		self.assertFalse(holiday["responded"])

		frappe.set_user(off_user)
		set_holiday_work_election(off, self.weekday, 0)
		frappe.set_user("Administrator")

	def test_agents_cannot_toggle_after_deadline(self):
		employee, user = make_election_employee("hwd.lock@example.com", self.holiday_list)
		past = now_datetime() - timedelta(hours=1)
		set_holiday_work_deadline(self.weekday, past, "Deadline Public Holiday")

		frappe.set_user(user)
		self.assertRaises(frappe.ValidationError, set_holiday_work_election, employee, self.weekday, 0)
		holiday = next(
			row
			for row in get_upcoming_holidays_for_employee(employee)
			if row["holiday_date"] == str(self.weekday)
		)
		self.assertTrue(holiday["will_work"])
		self.assertFalse(holiday["can_toggle"])
		self.assertTrue(holiday["deadline_passed"])

		frappe.set_user("Administrator")
		set_holiday_work_election(employee, self.weekday, 0)
		roster = get_holiday_work_roster(self.weekday)
		by_employee = {row["employee"]: row for row in roster["details"]}
		self.assertFalse(by_employee[employee]["will_work"])

	def test_scheduler_persists_working_for_non_responders(self):
		silent, _user = make_election_employee("hwd.auto@example.com", self.holiday_list)
		off, _off_user = make_election_employee("hwd.auto.off@example.com", self.holiday_list)
		set_holiday_work_election(off, self.weekday, 0)
		set_holiday_work_deadline(self.weekday, now_datetime() - timedelta(minutes=5), "Deadline Public Holiday")

		created = apply_default_working_after_deadline()
		self.assertGreaterEqual(created, 1)
		self.assertTrue(
			frappe.db.exists(
				"Holiday Work Election",
				{"employee": silent, "holiday_date": self.weekday, "will_work": 1},
			)
		)
		self.assertTrue(
			frappe.db.exists(
				"Holiday Work Election",
				{"employee": off, "holiday_date": self.weekday, "will_work": 0},
			)
		)

	def test_kiosk_toggle_opts_out_before_deadline(self):
		from frappe.utils.password import update_password

		from hrms.api.kiosk import get_kiosk_profile
		from hrms.api.kiosk import set_holiday_work_election as kiosk_set

		employee, user = make_election_employee("hwd.kiosk@example.com", self.holiday_list)
		frappe.db.set_value("User", user, "username", "HwdKiosk")
		update_password(user, "KioskPass123")
		set_holiday_work_deadline(self.weekday, now_datetime() + timedelta(days=1), "Deadline Public Holiday")

		frappe.set_user("Guest")
		profile = get_kiosk_profile("HwdKiosk")
		holiday = next(row for row in profile["holidays"] if row["holiday_date"] == str(self.weekday))
		self.assertTrue(holiday["will_work"])
		self.assertTrue(holiday["can_toggle"])

		updated = kiosk_set("HwdKiosk", "KioskPass123", str(self.weekday), 0)
		holiday = next(row for row in updated["holidays"] if row["holiday_date"] == str(self.weekday))
		self.assertFalse(holiday["will_work"])
		self.assertTrue(holiday["responded"])
		self.assertEqual(frappe.session.user, "Guest")
		self.assertTrue(
			frappe.db.exists(
				"Holiday Work Election",
				{"employee": employee, "holiday_date": self.weekday, "will_work": 0},
			)
		)
