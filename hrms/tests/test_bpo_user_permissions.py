# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.hr.bpo_user_permissions import (
	BPO_ROLES,
	BPO_SIDEBAR_KEYS,
	apply_bpo_user_permissions,
	canonical_sidebar_key,
	filter_user_modules_onload,
	get_all_roles,
	get_allowed_bpo_sidebar_keys,
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

	def test_disable_unused_erpnext_roles(self):
		apply_bpo_user_permissions()
		if frappe.get_meta("Role").has_field("disabled"):
			if frappe.db.exists("Role", "Academics User"):
				self.assertEqual(frappe.db.get_value("Role", "Academics User", "disabled"), 1)
			if frappe.db.exists("Role", "HR Manager"):
				self.assertEqual(frappe.db.get_value("Role", "HR Manager", "disabled"), 0)

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
