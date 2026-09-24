# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.hr.bpo_user_permissions import (
	BPO_ROLES,
	BPO_SIDEBAR_KEYS,
	PORTAL_ONLY_ROLES,
	apply_bpo_user_permissions,
	canonical_sidebar_key,
	convert_agent_users_to_website_users,
	enforce_agent_portal_user,
	filter_user_modules_onload,
	get_all_roles,
	get_allowed_bpo_sidebar_keys,
	is_agent_account,
	lock_portal_roles_without_desk_access,
	parse_blocked_bpo_modules,
)
from hrms.tests.utils import HRMSTestSuite


class TestBpoUserPermissions(HRMSTestSuite):
	def test_get_all_roles_is_staff_pro_only(self):
		roles = get_all_roles()
		for role in roles:
			self.assertIn(role, BPO_ROLES)
		self.assertNotIn("Academics User", roles)
		self.assertNotIn("Fleet Manager", roles)
		self.assertNotIn("Fulfillment User", roles)
		if frappe.db.exists("Role", "HR Manager"):
			self.assertIn("HR Manager", roles)

	def test_unused_erpnext_roles_are_removed(self):
		if not frappe.db.exists("Role", "Academics User"):
			frappe.get_doc({"doctype": "Role", "role_name": "Academics User"}).insert(ignore_permissions=True)
		apply_bpo_user_permissions()
		self.assertFalse(frappe.db.exists("Role", "Academics User"))
		if frappe.db.exists("Role", "HR Manager"):
			self.assertTrue(frappe.db.exists("Role", "HR Manager"))

	def test_user_onload_hides_frappe_module_defs(self):
		user = frappe.get_doc("User", "Administrator")
		user.set_onload("all_modules", ["HR", "Payroll", "Accounts", "Assets", "Buying", "Stock"])
		filter_user_modules_onload(user)
		self.assertEqual(user.get_onload("all_modules"), [])

	def test_sidebar_modules_match_desk_nav(self):
		self.assertEqual(
			BPO_SIDEBAR_KEYS,
			{"people", "time", "pay", "talent", "floor", "ss and taxes", "finance", "admin"},
		)
		self.assertEqual(canonical_sidebar_key("Floor Plan"), "floor")
		self.assertEqual(canonical_sidebar_key("Payroll"), "pay")
		self.assertEqual(canonical_sidebar_key("Workforce"), "people")

	def test_blocked_sidebars_leave_the_rest_allowed(self):
		blocked = parse_blocked_bpo_modules(["floor", "admin", "ss and taxes"])
		self.assertEqual(blocked, {"floor", "admin", "ss and taxes"})
		allowed = BPO_SIDEBAR_KEYS - blocked
		self.assertIn("people", allowed)
		self.assertIn("time", allowed)
		self.assertIn("finance", allowed)
		self.assertNotIn("floor", allowed)

	def test_administrator_keeps_every_sidebar(self):
		self.assertIsNone(get_allowed_bpo_sidebar_keys("Administrator"))

	def test_portal_roles_have_no_desk_access(self):
		lock_portal_roles_without_desk_access()
		for role in PORTAL_ONLY_ROLES:
			if frappe.db.exists("Role", role):
				self.assertFalse(cint_desk_access(role))

	def test_agent_user_is_website_user(self):
		email = "agent.portal.only@example.com"
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Agent",
				"last_name": "Portal",
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		)
		user.append("roles", {"role": "Employee"})
		enforce_agent_portal_user(user)
		self.assertEqual(user.user_type, "Website User")
		self.assertTrue(is_agent_account(email, {"Employee", "All"}))

	def test_staff_user_stays_system_user(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "hr.staff.desk@example.com",
				"first_name": "HR",
				"send_welcome_email": 0,
				"user_type": "Website User",
			}
		)
		user.append("roles", {"role": "HR User"})
		enforce_agent_portal_user(user)
		self.assertEqual(user.user_type, "System User")
		self.assertFalse(is_agent_account("hr.staff.desk@example.com", {"HR User", "Employee"}))

	def test_sidebar_hides_unreadable_doctypes(self):
		from hrms.boot import _can_open_sidebar_item

		self.assertTrue(_can_open_sidebar_item({"type": "Section Break", "label": "Setup"}))
		self.assertTrue(_can_open_sidebar_item({"link_type": "DocType", "link_to": "User"}))

		email = "agent.sidebar.hide@example.com"
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Sidebar",
				"send_welcome_email": 0,
				"user_type": "Website User",
			}
		)
		user.flags.ignore_permissions = True
		user.insert()
		user.add_roles("Employee Self Service")
		frappe.set_user(email)
		try:
			self.assertFalse(_can_open_sidebar_item({"link_type": "DocType", "link_to": "User"}))
			self.assertTrue(_can_open_sidebar_item({"type": "Section Break"}))
		finally:
			frappe.set_user("Administrator")

	def test_convert_existing_agent_system_users(self):
		email = "agent.convert.desk@example.com"
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Convert",
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		)
		user.flags.ignore_permissions = True
		user.insert()
		user.add_roles("Employee")
		frappe.db.set_value("User", email, "user_type", "System User", update_modified=False)
		self.assertGreaterEqual(convert_agent_users_to_website_users(), 1)
		self.assertEqual(frappe.db.get_value("User", email, "user_type"), "Website User")


def cint_desk_access(role: str) -> int:
	from frappe.utils import cint

	return cint(frappe.db.get_value("Role", role, "desk_access"))
