# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from hrms.hr.staff_pro_desk_permissions import (
	filter_profile_stats_payload,
	get_profile_stat_visibility,
)
from hrms.tests.test_utils import HRMSTestSuite


class TestStaffProDeskPermissions(HRMSTestSuite):
	def test_user_restriction_hides_agent_profit(self):
		user = "test_sp_hide_profit@example.com"
		if not frappe.db.exists("User", user):
			doc = frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Test",
					"enabled": 1,
					"user_type": "System User",
					"send_welcome_email": 0,
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert()
		if frappe.get_meta("User").has_field("sp_restrict_agent_profit"):
			frappe.db.set_value("User", user, "sp_restrict_agent_profit", 1, update_modified=False)

		visibility = get_profile_stat_visibility(user)
		if frappe.get_meta("User").has_field("sp_restrict_agent_profit"):
			self.assertFalse(visibility["agent_profit"])

		payload = filter_profile_stats_payload(
			{"agent_profit": 100, "total_billed": 50, "total_income": 10},
			user=user,
		)
		if frappe.get_meta("User").has_field("sp_restrict_agent_profit"):
			self.assertNotIn("agent_profit", payload)
