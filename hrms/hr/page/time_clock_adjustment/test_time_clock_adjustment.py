# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import add_employee_hours_note
from hrms.hr.doctype.attendance.attendance import add_hours_entry
from hrms.hr.page.time_clock_adjustment.time_clock_adjustment import get_adjustments, review_adjustment
from hrms.tests.utils import HRMSTestSuite


class TestTimeClockAdjustmentPage(HRMSTestSuite):
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
		self.assertTrue(any(row["name"] == adjustment_name and row["status"] == "Rejected" for row in payload["rows"]))

	def test_page_api_is_hr_only(self):
		employee = make_employee("tca.page.deny@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		frappe.set_user(user)
		self.assertRaises(frappe.PermissionError, get_adjustments)
