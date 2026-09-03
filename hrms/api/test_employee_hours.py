# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import get_employee_hours, get_employee_upcoming_pay
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
