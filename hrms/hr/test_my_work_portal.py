# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.hr.my_work_portal import consume_handoff, create_handoff
from hrms.hr.staff_pro_roles import MY_WORK_PORTAL_PATH, ensure_hr_assistant_role
from hrms.tests.utils import HRMSTestSuite
from hrms.www.hrms import get_boot


class TestMyWorkPortal(HRMSTestSuite):
	def setUp(self):
		super().setUp()
		ensure_hr_assistant_role()

	def _assistant_with_employee(self) -> str:
		from erpnext.setup.doctype.employee.test_employee import make_employee

		user = "test_my_work_assistant@example.com"
		if not frappe.db.exists("User", user):
			doc = frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "My",
					"last_name": "Work",
					"enabled": 1,
					"user_type": "System User",
					"send_welcome_email": 0,
					"roles": [{"role": "HR Assistant"}],
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert()
		else:
			frappe.get_doc("User", user).add_roles("HR Assistant")

		employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
		if not employee:
			employee = make_employee(user, company="_Test Company")
			frappe.db.set_value("Employee", employee, "user_id", user, update_modified=False)
			frappe.db.set_value("Employee", employee, "status", "Active", update_modified=False)
		return user

	def test_handoff_opens_portal_without_password(self):
		user = self._assistant_with_employee()
		original = frappe.session.user
		try:
			frappe.set_user(user)
			token = create_handoff()["token"]
			frappe.set_user("Guest")
			result = consume_handoff(token)
			self.assertEqual(result["user"], user)
			self.assertTrue(result["my_work"])
			self.assertEqual(result["home"], MY_WORK_PORTAL_PATH)
			self.assertEqual(frappe.session.user, user)
			self.assertRaises(frappe.PermissionError, consume_handoff, token)
		finally:
			frappe.set_user(original)

	def test_desk_admin_cannot_mint_my_work_handoff(self):
		frappe.set_user("Administrator")
		self.assertRaises(frappe.PermissionError, create_handoff)

	def test_agents_boot_marks_my_work_session(self):
		user = self._assistant_with_employee()
		original = frappe.session.user
		try:
			frappe.set_user(user)
			boot = get_boot()
			self.assertEqual(boot.session_user, user)
			self.assertTrue(boot.staff_pro_my_work)
			frappe.set_user("Guest")
			guest_boot = get_boot()
			self.assertFalse(guest_boot.session_user)
			self.assertFalse(guest_boot.staff_pro_my_work)
		finally:
			frappe.set_user(original)

	def test_invalid_token_is_rejected(self):
		self.assertRaises(frappe.PermissionError, consume_handoff, "not-a-real-token")
		self.assertRaises(frappe.PermissionError, consume_handoff, "a" * 32)
