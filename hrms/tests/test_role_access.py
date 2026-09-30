# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import json
import unittest
from pathlib import Path

from hrms.hr.role_access import (
	FLAG_NAMES,
	flag_enabled,
	merge_access_rows,
	redact_profile_stats,
	sidebar_item_allowed,
	workspace_allowed,
)


class TestRoleAccess(unittest.TestCase):
	def test_unset_switch_stays_on(self):
		self.assertTrue(flag_enabled(None))
		self.assertTrue(flag_enabled(""))
		self.assertTrue(flag_enabled(1))
		self.assertFalse(flag_enabled(0))

	def test_any_role_can_grant_access(self):
		merged = merge_access_rows(
			[
				{
					"see_agent_salary": 0,
					"see_bill_to_client": 0,
					"see_client_invoices": 0,
					"see_social_security": 1,
					"see_bank_details": 0,
				},
				{
					"see_agent_salary": 1,
					"see_bill_to_client": 0,
					"see_client_invoices": 0,
					"see_social_security": 0,
					"see_bank_details": 0,
				},
			]
		)
		self.assertTrue(merged["see_agent_salary"])
		self.assertTrue(merged["see_social_security"])
		self.assertFalse(merged["see_bill_to_client"])
		self.assertFalse(merged["see_client_invoices"])
		self.assertFalse(merged["see_bank_details"])

	def test_missing_role_rows_keep_access(self):
		self.assertTrue(all(merge_access_rows([]).values()))
		self.assertTrue(merge_access_rows([{}])["see_agent_salary"])

	def test_salary_switch_hides_pay_and_keeps_clients(self):
		access = {name: True for name in (
			"see_agent_salary",
			"see_bill_to_client",
			"see_client_invoices",
			"see_social_security",
			"see_bank_details",
		)}
		access["see_agent_salary"] = False
		self.assertFalse(workspace_allowed("Pay", access))
		self.assertFalse(
			sidebar_item_allowed(
				{"label": "Current Pay Stubs", "link_to": "Salary Slip", "link_type": "DocType"},
				access,
			)
		)
		self.assertTrue(
			sidebar_item_allowed(
				{"label": "Clients", "link_to": "Customer", "link_type": "DocType"},
				access,
			)
		)
		self.assertTrue(workspace_allowed("Finance", access))

	def test_invoice_switch_hides_invoices_only(self):
		access = {
			"see_agent_salary": True,
			"see_bill_to_client": True,
			"see_client_invoices": False,
			"see_social_security": True,
			"see_bank_details": True,
		}
		self.assertFalse(
			sidebar_item_allowed(
				{"label": "Client Invoices", "link_to": "Client Invoice", "link_type": "DocType"},
				access,
			)
		)
		self.assertTrue(
			sidebar_item_allowed(
				{"label": "Clients", "link_to": "Customer", "link_type": "DocType"},
				access,
			)
		)

	def test_profile_stats_follow_the_switches(self):
		stats = {
			"total_income": 10,
			"total_ss": 2,
			"total_tax": 1,
			"total_billed": 30,
			"agent_profit": 20,
			"leave_money_remaining": 5,
		}
		redacted = redact_profile_stats(
			dict(stats),
			{
				"see_agent_salary": False,
				"see_bill_to_client": True,
				"see_client_invoices": True,
				"see_social_security": True,
				"see_bank_details": True,
			},
		)
		self.assertIsNone(redacted["total_income"])
		self.assertIsNone(redacted["agent_profit"])
		self.assertIsNone(redacted["leave_money_remaining"])
		self.assertEqual(redacted["total_billed"], 30)
		self.assertEqual(redacted["total_ss"], 2)

	def test_every_sidebar_link_follows_a_switch(self):
		access = {name: False for name in FLAG_NAMES}
		root = Path(__file__).resolve().parents[1]
		missing = []
		for path in root.glob("**/sidebar/**/*.json"):
			data = json.loads(path.read_text(encoding="utf-8"))
			for item in data.get("items") or []:
				if item.get("type") != "Link":
					continue
				if sidebar_item_allowed(item, access):
					missing.append(
						f"{data.get('name')}: {item.get('label')} -> {item.get('link_to') or item.get('url')}"
					)
		self.assertEqual(missing, [])

	def test_people_switch_hides_agents_and_keeps_time(self):
		access = {name: True for name in FLAG_NAMES}
		access["see_agents"] = False
		self.assertFalse(
			sidebar_item_allowed({"type": "Link", "label": "Agents", "link_to": "Employee"}, access)
		)
		self.assertTrue(
			sidebar_item_allowed({"type": "Link", "label": "Day View", "link_to": "day-view"}, access)
		)
		self.assertTrue(workspace_allowed("People", access))
		access.update({name: False for name in FLAG_NAMES if name.startswith("see_") and name in {
			"see_people_dashboard",
			"see_agents",
			"see_paid_time_off",
			"see_onboarding",
			"see_offboarding",
			"see_employee_requests",
			"see_concerns",
			"see_people_setup",
		}})
		self.assertFalse(workspace_allowed("People", access))
		self.assertTrue(workspace_allowed("Time", access))

	def test_td4_follows_its_own_switch(self):
		access = {name: True for name in FLAG_NAMES}
		access["see_agent_salary"] = False
		access["see_social_security"] = False
		self.assertTrue(
			sidebar_item_allowed({"type": "Link", "label": "TD4 Forms", "link_to": "TD4 Form"}, access)
		)
		self.assertFalse(
			sidebar_item_allowed({"type": "Link", "label": "Current Pay Stubs", "link_to": "Salary Slip"}, access)
		)
		access["see_td4_forms"] = False
		self.assertFalse(
			sidebar_item_allowed({"type": "Link", "label": "TD4 Forms", "link_to": "TD4 Form"}, access)
		)
		self.assertFalse(workspace_allowed("Filesystem", {**access, "see_agent_documents": False}))
		access["see_td4_forms"] = True
		self.assertTrue(workspace_allowed("Filesystem", {**access, "see_agent_documents": False}))
