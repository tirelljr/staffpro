# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import add_days, flt, get_datetime, getdate, now_datetime

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.attendance.attendance import add_hours_entry
from hrms.hr.floor_workers import (
	FLOOR_WORKER_TAG,
	WEEKDAY_DEFAULTS,
	apply_employee_floor_worker_rules,
	ensure_floor_worker_hours,
)
from hrms.payroll.auto_client_invoice import get_billable_customers
from hrms.payroll.doctype.payroll_entry.payroll_entry import get_employees_for_client
from hrms.setup import get_custom_fields
from hrms.tests.utils import HRMSTestSuite


class TestFloorWorkers(HRMSTestSuite):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_custom_fields(get_custom_fields(), ignore_validate=True)

	def test_floor_worker_keeps_tag_and_clears_client_billing(self):
		employee = make_employee("floor.tag@example.com", company="_Test Company")
		customer = self._customer("_Test Floor Tag Client")
		doc = frappe.get_doc("Employee", employee)
		doc.is_floor_worker = 1
		doc.bill_to_customer = customer
		doc.billing_rate = 25
		doc.save()

		self.assertIn(FLOOR_WORKER_TAG, doc._user_tags or "")
		self.assertFalse(doc.bill_to_customer)
		self.assertEqual(flt(doc.billing_rate), 0)
		self.assertEqual(doc.work_monday, 1)
		self.assertEqual(doc.work_saturday, 0)

		doc.is_floor_worker = 0
		doc.save()
		self.assertNotIn(FLOOR_WORKER_TAG, doc._user_tags or "")

	def test_blank_working_days_default_to_weekdays(self):
		employee = make_employee("floor.days@example.com", company="_Test Company")
		doc = frappe.get_doc("Employee", employee)
		for field in WEEKDAY_DEFAULTS:
			doc.set(field, 0)
		doc.save()
		self.assertEqual(doc.work_monday, 1)
		self.assertEqual(doc.work_friday, 1)
		self.assertEqual(doc.work_saturday, 0)
		self.assertEqual(doc.work_sunday, 0)

	def test_new_floor_worker_inherits_group_working_days(self):
		doc = frappe.new_doc("Employee")
		doc.is_floor_worker = 1
		doc.default_shift = "Day Shift"
		for field, value in WEEKDAY_DEFAULTS.items():
			doc.set(field, value)
		if frappe.get_meta("HR Settings").has_field("floor_work_saturday"):
			frappe.db.set_single_value("HR Settings", "floor_work_saturday", 1)
		apply_employee_floor_worker_rules(doc)
		self.assertFalse(doc.default_shift)
		if frappe.get_meta("HR Settings").has_field("floor_work_saturday"):
			self.assertEqual(doc.work_saturday, 1)
		else:
			self.assertEqual(doc.work_saturday, 0)
		self.assertEqual(doc.work_monday, 1)

	def test_auto_hours_follow_checked_days_and_individual_times(self):
		employee = self._floor_worker(
			"floor.hours@example.com",
			floor_worker_start_time="10:00:00",
			floor_worker_end_time="15:00:00",
		)
		monday = _recent_weekday(0)
		saturday = add_days(monday, -2)
		ensure_floor_worker_hours(monday, monday, employee=employee)
		attendance = _attendance(employee, monday)
		self.assertTrue(attendance)
		self.assertEqual(get_datetime(attendance.in_time).hour, 10)
		self.assertGreater(flt(attendance.working_hours), 0)

		ensure_floor_worker_hours(saturday, saturday, employee=employee)
		self.assertFalse(_attendance(employee, saturday))

		frappe.db.set_value("Employee", employee, "work_saturday", 1)
		ensure_floor_worker_hours(saturday, saturday, employee=employee)
		self.assertTrue(_attendance(employee, saturday))

	def test_public_holiday_on_a_working_day_still_gets_hours(self):
		employee = self._floor_worker("floor.holiday@example.com")
		monday = _recent_weekday(0)
		holiday_list = frappe.db.get_value("Employee", employee, "holiday_list") or frappe.db.get_value(
			"Company", "_Test Company", "default_holiday_list"
		)
		if holiday_list and frappe.db.exists("Holiday List", holiday_list):
			from hrms.tests.test_utils import add_date_to_holiday_list

			try:
				add_date_to_holiday_list(monday, holiday_list)
			except Exception:
				pass
		ensure_floor_worker_hours(monday, monday, employee=employee)
		self.assertTrue(_attendance(employee, monday))

	def test_existing_attendance_is_not_overwritten(self):
		employee = self._floor_worker("floor.keep@example.com")
		monday = _recent_weekday(0)
		add_hours_entry(employee, monday, "09:00:00", "12:00:00")
		before = flt(_attendance(employee, monday).working_hours)
		ensure_floor_worker_hours(monday, monday, employee=employee)
		self.assertEqual(flt(_attendance(employee, monday).working_hours), before)

	def test_self_clock_in_is_blocked_and_admin_hours_are_allowed(self):
		employee = self._floor_worker("floor.clock@example.com")
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": "IN",
				"time": now_datetime(),
			}
		)
		self.assertRaises(frappe.ValidationError, checkin.insert)
		tuesday = add_days(_recent_weekday(0), 1)
		self.assertTrue(add_hours_entry(employee, tuesday, "08:00:00", "12:00:00"))

	def test_floor_worker_stays_on_payroll_and_off_client_invoice(self):
		employee = self._floor_worker("floor.pay@example.com")
		customer = self._customer("_Test Floor Billing Client")
		frappe.db.set_value(
			"Employee",
			employee,
			{"bill_to_customer": customer, "billing_rate": 20, "status": "Active"},
		)
		names = [row[0] for row in get_employees_for_client(frappe._dict(company="_Test Company"))]
		self.assertIn(employee, names)
		self.assertNotIn(customer, get_billable_customers("_Test Company"))

		invoice = frappe.new_doc("Client Invoice")
		invoice.company = "_Test Company"
		invoice.customer = customer
		invoice.from_date = add_days(getdate(), -7)
		invoice.to_date = getdate()
		self.assertRaises(frappe.ValidationError, invoice.get_agents)

	def _floor_worker(self, email: str, **overrides) -> str:
		employee = make_employee(email, company="_Test Company")
		values = {
			"is_floor_worker": 1,
			"date_of_joining": add_days(getdate(), -60),
			"status": "Active",
			"floor_worker_start_time": "09:00:00",
			"floor_worker_end_time": "17:00:00",
			**WEEKDAY_DEFAULTS,
		}
		values.update(overrides)
		frappe.db.set_value("Employee", employee, values)
		return employee

	def _customer(self, name: str) -> str:
		if frappe.db.exists("Customer", name):
			return name
		customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
		territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
		doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_type": "Company",
				"customer_group": customer_group,
				"territory": territory,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name


def _recent_weekday(weekday: int):
	day = getdate()
	while day.weekday() != weekday:
		day = add_days(day, -1)
	return day


def _attendance(employee: str, day):
	return frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": day, "docstatus": ("<", 2)},
		["name", "working_hours", "in_time", "status"],
		as_dict=True,
	)
