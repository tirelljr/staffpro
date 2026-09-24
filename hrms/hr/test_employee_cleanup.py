# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.attendance.attendance import mark_attendance
from hrms.hr.employee_cleanup import delete_employee_with_unlink, unlink_employee_records
from hrms.tests.utils import HRMSTestSuite


class TestEmployeeCleanup(HRMSTestSuite):
	def test_delete_employee_linked_to_attendance(self):
		employee = make_employee("cleanup_attendance@example.com", company="_Test Company")
		date = add_days(nowdate(), -3)
		attendance = mark_attendance(employee, date, "Present")

		self.assertTrue(frappe.db.exists("Attendance", attendance))

		result = delete_employee_with_unlink(employee)

		self.assertEqual(result["employee"], employee)
		self.assertFalse(frappe.db.exists("Employee", employee))
		self.assertFalse(frappe.db.exists("Attendance", attendance))
		self.assertGreaterEqual(result["deleted"].get("Attendance", 0), 1)

	def test_standard_delete_unlinks_attendance(self):
		employee = make_employee("cleanup_standard_delete@example.com", company="_Test Company")
		date = add_days(nowdate(), -4)
		attendance = mark_attendance(employee, date, "Present")

		frappe.delete_doc("Employee", employee, ignore_permissions=True)

		self.assertFalse(frappe.db.exists("Employee", employee))
		self.assertFalse(frappe.db.exists("Attendance", attendance))

	def test_unlink_removes_attendance_without_deleting_employee(self):
		employee = make_employee("cleanup_unlink_only@example.com", company="_Test Company")
		date = add_days(nowdate(), -5)
		attendance = mark_attendance(employee, date, "Present")

		deleted = unlink_employee_records(employee)

		self.assertTrue(frappe.db.exists("Employee", employee))
		self.assertFalse(frappe.db.exists("Attendance", attendance))
		self.assertGreaterEqual(deleted.get("Attendance", 0), 1)
