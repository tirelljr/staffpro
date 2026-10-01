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

	def test_delete_employee_linked_to_leave_ledger(self):
		from hrms.hr.doctype.leave_allocation.test_leave_allocation import create_leave_allocation
		from hrms.hr.doctype.leave_type.test_leave_type import create_leave_type

		employee = make_employee("cleanup_leave_ledger@example.com", company="_Test Company")
		leave_type = create_leave_type(leave_type_name="_Test Cleanup Leave")
		allocation = create_leave_allocation(
			employee=employee,
			leave_type=leave_type.name,
			from_date=nowdate(),
			to_date=add_days(nowdate(), 365),
			new_leaves_allocated=10,
		)
		allocation.submit()

		self.assertTrue(frappe.db.exists("Leave Ledger Entry", {"employee": employee}))

		result = delete_employee_with_unlink(employee)

		self.assertEqual(result["employee"], employee)
		self.assertFalse(frappe.db.exists("Employee", employee))
		self.assertFalse(frappe.db.exists("Leave Allocation", allocation.name))
		self.assertFalse(frappe.db.exists("Leave Ledger Entry", {"employee": employee}))

	def test_standard_delete_unlinks_leave_ledger(self):
		from hrms.hr.doctype.leave_allocation.test_leave_allocation import create_leave_allocation
		from hrms.hr.doctype.leave_type.test_leave_type import create_leave_type

		employee = make_employee("cleanup_standard_lle@example.com", company="_Test Company")
		leave_type = create_leave_type(leave_type_name="_Test Cleanup Leave Standard")
		allocation = create_leave_allocation(
			employee=employee,
			leave_type=leave_type.name,
			from_date=nowdate(),
			to_date=add_days(nowdate(), 365),
			new_leaves_allocated=8,
		)
		allocation.submit()

		frappe.delete_doc("Employee", employee, ignore_permissions=True)

		self.assertFalse(frappe.db.exists("Employee", employee))
		self.assertFalse(frappe.db.exists("Leave Ledger Entry", {"employee": employee}))
