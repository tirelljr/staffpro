# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import add_employee_hours_note, get_employee_hours, get_employee_upcoming_pay
from hrms.hr.doctype.attendance.attendance import add_hours_entry
from hrms.tests.utils import HRMSTestSuite


class TestEmployeeHoursAPI(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_upcoming_pay_uses_session_employee(self):
		employee = make_employee("pwa.hours.pay@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		add_hours_entry(employee, nowdate(), "09:00:00", "13:00:00")

		frappe.set_user(user)
		data = get_employee_upcoming_pay()

		self.assertEqual(data["employee_name"], frappe.db.get_value("Employee", employee, "employee_name"))
		self.assertIn("gross_pay", data)
		self.assertIn("net_pay", data)
		self.assertIn("total_hours", data)
		self.assertIn("start_date", data)
		self.assertIn("end_date", data)
		self.assertGreaterEqual(flt(data["total_hours"]), 4)

	def test_employee_hours_defaults_to_current_pay_period(self):
		employee = make_employee("pwa.hours.rows@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		add_hours_entry(employee, nowdate(), "08:00:00", "12:00:00")

		frappe.set_user(user)
		data = get_employee_hours()

		self.assertEqual(data["employee"], employee)
		self.assertIn("rows", data)
		self.assertIn("totals", data)
		self.assertIn("presets", data)
		self.assertIn("current_pay_period", data["presets"])
		self.assertEqual(data["from_date"], data["presets"]["current_pay_period"][0])
		self.assertEqual(data["to_date"], data["presets"]["current_pay_period"][1])
		self.assertTrue(any(flt(row.get("total") or row.get("working_hours")) >= 4 for row in data["rows"]))

	def test_employee_can_add_hours_note(self):
		employee = make_employee("pwa.hours.note@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		name = add_hours_entry(employee, nowdate(), "09:00:00", "17:00:00")

		frappe.set_user(user)
		add_employee_hours_note(name, "Forgot to clock out, left at 5")

		data = get_employee_hours(from_date=nowdate(), to_date=nowdate())
		notes = [comment.get("content") or "" for row in data["rows"] for comment in row.get("comments") or []]
		self.assertTrue(any("Forgot to clock out, left at 5" in note for note in notes))

	def test_employee_cannot_note_another_employees_hours(self):
		one = make_employee("pwa.hours.note.one@example.com", company="_Test Company")
		two = make_employee("pwa.hours.note.two@example.com", company="_Test Company")
		user_two = frappe.db.get_value("Employee", two, "user_id")
		name = add_hours_entry(one, nowdate(), "09:00:00", "17:00:00")

		frappe.set_user(user_two)
		with self.assertRaises(frappe.PermissionError):
			add_employee_hours_note(name, "Should not work")

	def test_hours_note_requires_text(self):
		employee = make_employee("pwa.hours.note.empty@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		name = add_hours_entry(employee, nowdate(), "09:00:00", "13:00:00")

		frappe.set_user(user)
		with self.assertRaises(frappe.ValidationError):
			add_employee_hours_note(name, "   ")
