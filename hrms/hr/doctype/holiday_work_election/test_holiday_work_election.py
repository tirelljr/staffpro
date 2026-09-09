# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import timedelta

import frappe
from frappe.utils import add_days, cint, getdate
from frappe.utils.user import add_role

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.holiday_list_assignment.test_holiday_list_assignment import (
	create_holiday_list_assignment,
)
from hrms.hr.doctype.holiday_work_election.holiday_work_election import (
	get_holiday_work_context,
	set_holiday_work_election,
)
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list
from hrms.tests.utils import HRMSTestSuite


def next_weekday(start=None):
	day = add_days(getdate(start) if start else getdate(), 1)
	while day.weekday() > 4:
		day += timedelta(days=1)
	return day


def next_sunday(start=None):
	day = add_days(getdate(start) if start else getdate(), 1)
	while day.weekday() != 6:
		day += timedelta(days=1)
	return day


def past_weekday():
	day = add_days(getdate(), -1)
	while day.weekday() > 4:
		day -= timedelta(days=1)
	return day


def add_public_holiday(holiday_list, holiday_date, description):
	doc = frappe.get_doc("Holiday List", holiday_list)
	holiday_date = getdate(holiday_date)
	for row in doc.holidays:
		if getdate(row.holiday_date) == holiday_date and not cint(row.weekly_off):
			row.description = description
			doc.save()
			return
	doc.append(
		"holidays",
		{
			"holiday_date": holiday_date,
			"description": description,
			"weekly_off": 0,
		},
	)
	doc.save()


def make_election_employee(email, holiday_list, company="_Test Company"):
	employee = make_employee(email, company=company, first_name="HWE", last_name=email.split("@")[0])
	create_holiday_list_assignment("Employee", employee, holiday_list, company=company)
	user = frappe.db.get_value("Employee", employee, "user_id")
	add_role(user, "Employee")
	for role in ("HR User", "HR Manager", "System Manager"):
		frappe.db.delete("Has Role", {"parent": user, "role": role})
	frappe.clear_cache(user=user)
	return employee, user


class TestHolidayWorkElection(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		self.holiday_list = make_holiday_list(
			list_name="HWE Test Holiday List",
			from_date=getdate().replace(month=1, day=1),
			to_date=getdate().replace(month=12, day=31),
		)
		self.weekday = next_weekday()
		self.sunday = next_sunday()
		self.past = past_weekday()
		add_public_holiday(self.holiday_list, self.weekday, "Test Public Holiday")
		add_public_holiday(self.holiday_list, self.sunday, "Sunday Public Holiday")
		add_public_holiday(self.holiday_list, self.past, "Past Public Holiday")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_context_marks_weekday_public_holiday_as_work_day(self):
		employee, _user = make_election_employee("hwe.ctx@example.com", self.holiday_list)
		workday = get_holiday_work_context(employee, self.weekday)
		weekly_off = get_holiday_work_context(employee, self.sunday)

		self.assertTrue(workday["is_public"])
		self.assertTrue(workday["is_work_day"])
		self.assertFalse(workday["is_past"])
		self.assertEqual(workday["description"], "Test Public Holiday")

		self.assertTrue(weekly_off["is_public"])
		self.assertTrue(weekly_off["is_weekly_off"])
		self.assertFalse(weekly_off["is_work_day"])

	def test_elect_to_work_on_weekday_holiday(self):
		employee, _user = make_election_employee("hwe.work@example.com", self.holiday_list)
		result = set_holiday_work_election(employee, self.weekday, 1)

		self.assertTrue(result["will_work"])
		self.assertTrue(
			frappe.db.exists(
				"Holiday Work Election",
				{"employee": employee, "holiday_date": self.weekday, "will_work": 1},
			)
		)

		updated = set_holiday_work_election(employee, self.weekday, 0)
		self.assertFalse(updated["will_work"])
		self.assertEqual(
			frappe.db.count("Holiday Work Election", {"employee": employee, "holiday_date": self.weekday}),
			1,
		)

	def test_reject_weekly_off_and_past_dates(self):
		employee, _user = make_election_employee("hwe.reject@example.com", self.holiday_list)

		self.assertRaises(frappe.ValidationError, set_holiday_work_election, employee, self.sunday, 1)
		self.assertRaises(frappe.ValidationError, set_holiday_work_election, employee, self.past, 1)

	def test_employee_cannot_elect_for_another_employee(self):
		employee_one, user_one = make_election_employee("hwe.own@example.com", self.holiday_list)
		employee_two, _user_two = make_election_employee("hwe.other@example.com", self.holiday_list)

		frappe.set_user(user_one)
		self.assertRaises(frappe.PermissionError, set_holiday_work_election, employee_two, self.weekday, 1)
		set_holiday_work_election(employee_one, self.weekday, 1)
		frappe.set_user("Administrator")
		self.assertTrue(
			frappe.db.exists(
				"Holiday Work Election",
				{"employee": employee_one, "holiday_date": self.weekday, "will_work": 1},
			)
		)
