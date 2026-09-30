# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from hrms.boot import is_staff_pro_desk_admin
from hrms.hr.staff_pro_desk_permissions import can_access_sidebar_link, filter_sidebar_rows
from hrms.hr.staff_pro_roles import (
	can_use_my_work_portal,
	is_agent_portal_user,
	is_staff_pro_hr_desk_user,
)
from hrms.tests.test_utils import HRMSTestSuite


class TestStaffProRoles(HRMSTestSuite):
	def test_hr_assistant_is_desk_admin_not_agent_portal(self):
		user = "test_hr_assistant@example.com"
		if not frappe.db.exists("User", user):
			doc = frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "HR",
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

		self.assertTrue(is_staff_pro_hr_desk_user(user))
		self.assertFalse(is_agent_portal_user(user))
		self.assertTrue(is_staff_pro_desk_admin(user))

	def test_agent_system_user_is_not_desk_admin(self):
		user = "test_agent_portal@example.com"
		if not frappe.db.exists("User", user):
			doc = frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Agent",
					"enabled": 1,
					"user_type": "System User",
					"send_welcome_email": 0,
					"roles": [{"role": "Employee Self Service"}],
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert()
		self.assertTrue(is_agent_portal_user(user))
		self.assertFalse(is_staff_pro_desk_admin(user))

	def test_hr_assistant_my_work_requires_linked_employee(self):
		user = "test_hr_assistant@example.com"
		self.assertFalse(can_use_my_work_portal(user))

	def test_hr_assistant_keeps_employee_sidebar_link(self):
		user = "test_hr_assistant@example.com"
		rows = [{"type": "Link", "link_type": "DocType", "link_to": "Employee", "label": "Agents"}]
		filtered = filter_sidebar_rows(rows, user=user)
		self.assertEqual(len(filtered), 1)
		self.assertTrue(can_access_sidebar_link("DocType", "Employee", user=user) or is_staff_pro_hr_desk_user(user))
