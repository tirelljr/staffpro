# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import add_employee_hours_note, get_employee_hours
from hrms.hr.doctype.attendance.attendance import add_hours_entry, get_hours_rows
from hrms.hr.doctype.time_clock_adjustment.time_clock_adjustment import (
	get_time_clock_adjustments,
	parse_requested_times,
	review_time_clock_adjustment,
	time_to_str,
)
from hrms.hr.page.in_out_today.in_out_today import get_in_out_today
from hrms.tests.utils import HRMSTestSuite


class TestTimeClockAdjustment(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_parse_requested_times_from_note(self):
		self.assertEqual(
			parse_requested_times("Forgot to clock out, left at 5", current_in="09:00:00"),
			{"in_time": None, "out_time": "17:00:00"},
		)
		self.assertEqual(
			parse_requested_times("Please change my in time to 8:15"),
			{"in_time": "08:15:00", "out_time": None},
		)
		self.assertEqual(
			parse_requested_times("clocked in at 9am and out at 6pm"),
			{"in_time": "09:00:00", "out_time": "18:00:00"},
		)
		self.assertEqual(
			parse_requested_times("I need 8 hours of overtime"),
			{"in_time": None, "out_time": None},
		)

	def test_note_creates_pending_adjustment(self):
		employee = make_employee("tca.note.create@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		name = add_hours_entry(employee, nowdate(), "09:00:00", "17:00:00")

		frappe.set_user(user)
		result = add_employee_hours_note(name, "Forgot to clock out, left at 6")

		self.assertTrue(result.get("adjustment"))
		self.assertEqual(result["adjustment"]["status"], "Pending")
		self.assertEqual(time_to_str(result["adjustment"]["requested_out_time"])[:5], "18:00")

		frappe.set_user("Administrator")
		hours = get_hours_rows(from_date=nowdate(), to_date=nowdate(), employee=employee)
		row = next(item for item in hours["rows"] if item.get("name") == name)
		self.assertTrue(any("left at 6" in (comment.get("content") or "") for comment in row.get("comments") or []))
		self.assertEqual(row.get("adjustment", {}).get("name"), result["adjustment"]["name"])

	def test_explicit_requested_times_create_adjustment(self):
		employee = make_employee("tca.note.explicit@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		name = add_hours_entry(employee, nowdate(), "09:00:00", "17:00:00")

		frappe.set_user(user)
		result = add_employee_hours_note(
			name,
			"Please fix my punches",
			requested_in_time="08:15:00",
			requested_out_time="17:30:00",
		)
		self.assertEqual(time_to_str(result["adjustment"]["requested_in_time"])[:5], "08:15")
		self.assertEqual(time_to_str(result["adjustment"]["requested_out_time"])[:5], "17:30")

	def test_approve_applies_edit_like_day_view(self):
		employee = make_employee("tca.approve@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		name = add_hours_entry(employee, nowdate(), "09:00:00", "17:00:00")

		frappe.set_user(user)
		result = add_employee_hours_note(name, "Forgot to clock out, left at 6")
		adjustment_name = result["adjustment"]["name"]

		frappe.set_user("Administrator")
		review_time_clock_adjustment(adjustment_name, "approve")

		hours = get_hours_rows(from_date=nowdate(), to_date=nowdate(), employee=employee)
		row = next(item for item in hours["rows"] if item.get("name") == name or item.get("employee") == employee)
		self.assertEqual(time_to_str(row.get("out_time"))[:5], "18:00")
		self.assertFalse(row.get("adjustment"))
		doc = frappe.get_doc("Time Clock Adjustment", adjustment_name)
		self.assertEqual(doc.status, "Approved")

	def test_reject_leaves_times_unchanged(self):
		employee = make_employee("tca.reject@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		name = add_hours_entry(employee, nowdate(), "09:00:00", "17:00:00")

		frappe.set_user(user)
		result = add_employee_hours_note(name, "Please change out to 6pm")
		adjustment_name = result["adjustment"]["name"]

		frappe.set_user("Administrator")
		review_time_clock_adjustment(adjustment_name, "reject")

		hours = get_hours_rows(from_date=nowdate(), to_date=nowdate(), employee=employee)
		row = next(item for item in hours["rows"] if item.get("name") == name or item.get("employee") == employee)
		self.assertEqual(time_to_str(row.get("out_time"))[:5], "17:00")
		doc = frappe.get_doc("Time Clock Adjustment", adjustment_name)
		self.assertEqual(doc.status, "Rejected")

	def test_who_is_in_includes_note_and_pending_change(self):
		employee = make_employee("tca.inout@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		name = add_hours_entry(employee, nowdate(), "09:00:00", working_now=1)
		frappe.set_user(user)
		add_employee_hours_note(name, "Forgot to clock out, left at 5")

		frappe.set_user("Administrator")
		payload = get_in_out_today()
		row = next(item for item in payload["details"] if item["employee"] == employee)
		self.assertTrue(any("Forgot to clock out" in (comment.get("content") or "") for comment in row.get("comments") or []))
		self.assertEqual(row.get("adjustment", {}).get("status"), "Pending")
		self.assertEqual(time_to_str(row["adjustment"]["requested_out_time"])[:5], "17:00")

	def test_list_api_is_hr_only(self):
		employee = make_employee("tca.list.deny@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		name = add_hours_entry(employee, nowdate(), "09:00:00", "17:00:00")
		frappe.set_user(user)
		add_employee_hours_note(name, "left at 6")
		self.assertRaises(frappe.PermissionError, get_time_clock_adjustments)

		frappe.set_user("Administrator")
		payload = get_time_clock_adjustments(status="Pending")
		self.assertTrue(any(row["employee"] == employee for row in payload["rows"]))

	def test_employee_hours_include_pending_adjustment(self):
		employee = make_employee("tca.pwa.rows@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		name = add_hours_entry(employee, nowdate(), "09:00:00", "17:00:00")
		frappe.set_user(user)
		add_employee_hours_note(name, "Please change out to 6pm")
		data = get_employee_hours(from_date=nowdate(), to_date=nowdate())
		self.assertTrue(any(row.get("adjustment") for row in data["rows"]))
