# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import add_employee_hours_note
from hrms.hr.doctype.attendance.attendance import add_hours_entry, cancel_hours_entry
from hrms.hr.page.time_clock_adjustments.time_clock_adjustments import (
	get_adjustments,
	review_adjustment,
)
from hrms.tests.utils import HRMSTestSuite


class TestTimeClockAdjustmentsPage(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_page_lists_pending_and_reviews(self):
		employee = make_employee("tca.page@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		name = add_hours_entry(employee, nowdate(), "09:00:00", "17:00:00")
		frappe.set_user(user)
		created = add_employee_hours_note(name, "Please change out to 6pm")
		adjustment_name = created["adjustment"]["name"]

		frappe.set_user("Administrator")
		payload = get_adjustments(status="Pending")
		self.assertTrue(any(row["name"] == adjustment_name for row in payload["rows"]))

		review_adjustment(adjustment_name, "reject")
		payload = get_adjustments(status="Rejected")
		self.assertTrue(
			any(
				row["name"] == adjustment_name and row["status"] == "Rejected"
				for row in payload["rows"]
			)
		)

		history = get_adjustments(history=1)
		self.assertTrue(history.get("history"))
		self.assertTrue(
			any(
				row["name"] == adjustment_name and row["status"] == "Rejected"
				for row in history["rows"]
			)
		)
		self.assertFalse(any(row["status"] == "Pending" for row in history["rows"]))

		pending_in_history = get_adjustments(status="Pending", history=1)
		self.assertFalse(any(row["name"] == adjustment_name for row in pending_in_history["rows"]))

	def test_manual_add_and_delete_appear_in_history(self):
		frappe.reload_doc("hr", "doctype", "time_clock_adjustment")
		employee = make_employee("tca.manual.page@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		day = nowdate()
		attendance = add_hours_entry(employee, day, "09:00:00", "17:00:00")

		added = [
			row
			for row in get_adjustments(history=1)["rows"]
			if row["employee"] == employee and row["action"] == "Add"
		]
		self.assertEqual(len(added), 1)
		self.assertEqual(added[0]["status"], "Approved")
		self.assertEqual(added[0]["hours_change"], 8.0)
		self.assertEqual(added[0]["hours_change_label"], "+8 hours")

		frappe.set_user(user)
		created = add_employee_hours_note(attendance, "Please change out to 6pm")
		adjustment_name = created["adjustment"]["name"]
		frappe.set_user("Administrator")
		before = [
			row["name"]
			for row in get_adjustments(history=1)["rows"]
			if row["employee"] == employee
		]
		review_adjustment(adjustment_name, "approve")
		after = [
			row
			for row in get_adjustments(history=1)["rows"]
			if row["employee"] == employee
		]
		self.assertEqual(len(after), len(before) + 1)
		approved = next(row for row in after if row["name"] == adjustment_name)
		self.assertEqual(approved["hours_change"], 1.0)
		self.assertEqual(approved["hours_change_label"], "+1 hour")

		other = make_employee("tca.manual.delete@example.com", company="_Test Company")
		other_attendance = add_hours_entry(other, day, "09:00:00", "17:00:00")
		logs = frappe.get_all(
			"Employee Checkin",
			filters={"employee": other, "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
			fields=["name", "log_type"],
			order_by="time asc",
		)
		in_log = next(row.name for row in logs if row.log_type == "IN")
		out_log = next(row.name for row in logs if row.log_type == "OUT")
		cancel_hours_entry(other_attendance, in_log, out_log)
		deleted = next(
			row
			for row in get_adjustments(history=1)["rows"]
			if row["employee"] == other and row["action"] == "Delete"
		)
		self.assertEqual(deleted["hours_change"], -8.0)
		self.assertEqual(deleted["hours_change_label"], "-8 hours")

	def test_page_api_is_hr_only(self):
		employee = make_employee("tca.page.deny@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		frappe.set_user(user)
		self.assertRaises(frappe.PermissionError, get_adjustments)
