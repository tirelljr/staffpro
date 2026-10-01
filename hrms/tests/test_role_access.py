# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import json
import unittest
from pathlib import Path

from hrms.hr.role_access import (
	FLAG_NAMES,
	blocked_routes,
	flag_enabled,
	merge_access_rows,
	redact_hours_payload,
	redact_profile_stats,
	drop_empty_sections,
	sidebar_item_allowed,
	sidebar_item_has_switch,
	switch_grant_targets,
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

	def test_removed_nav_is_gone_from_sidebar_fixtures(self):
		removed = {
			"Data Analytics",
			"Email Account",
			"Customization",
			"Customize Form",
			"Print Format",
			"Error Log",
		}
		root = Path(__file__).resolve().parents[1]
		found = []
		paths = (
			list(root.glob("**/sidebar/**/*.json"))
			+ list(root.glob("**/workspace_sidebar/*.json"))
			+ list(root.glob("**/workspace/**/*.json"))
		)
		for path in paths:
			data = json.loads(path.read_text(encoding="utf-8"))
			for item in data.get("items") or data.get("sidebar_items") or []:
				label = (item.get("label") or "").strip()
				link_to = (item.get("link_to") or "").strip()
				if label in removed or link_to in removed:
					found.append(f"{path.name}: {label or link_to}")
		self.assertEqual(found, [])

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

	def test_blocked_routes_follow_a_switched_off_area(self):
		access = {name: True for name in FLAG_NAMES}
		access["see_attendance"] = False
		blocks = blocked_routes(access)
		self.assertIn("Attendance", blocks["doctypes"])
		self.assertIn("day-view", blocks["pages"])
		self.assertNotIn("Time", blocks["workspaces"])
		for name in FLAG_NAMES:
			if name.startswith("see_") and name in {
				"see_attendance",
				"see_time_clock",
				"see_holiday_work",
				"see_time_off",
				"see_time_approvals",
				"see_overtime",
				"see_time_reports",
				"see_schedules",
			}:
				access[name] = False
		self.assertIn("Time", blocked_routes(access)["workspaces"])

	def test_role_switch_change_uses_on_off_meaning(self):
		from hrms.hr.role_access import _role_access_changed

		class _Role:
			def __init__(self, values, before=None):
				self._values = values
				self._before = before

			def get(self, name):
				return self._values.get(name)

			def get_doc_before_save(self):
				return self._before

		before = _Role({"see_attendance": 1, "see_agents": None})
		unchanged = _Role({"see_attendance": 1, "see_agents": None}, before)
		self.assertFalse(_role_access_changed(unchanged))
		turned_off = _Role({"see_attendance": 0, "see_agents": None}, before)
		self.assertTrue(_role_access_changed(turned_off))
		from_default_off = _Role({"see_attendance": 1, "see_agents": 0}, before)
		self.assertTrue(_role_access_changed(from_default_off))

	def test_people_and_time_links_stay_when_switches_are_on(self):
		access = {name: True for name in FLAG_NAMES}
		people = {"type": "Link", "label": "Agents", "link_to": "Employee", "link_type": "DocType"}
		time = {"type": "Link", "label": "Day View", "link_to": "day-view", "link_type": "Page"}
		self.assertTrue(sidebar_item_has_switch(people))
		self.assertTrue(sidebar_item_has_switch(time))
		self.assertTrue(sidebar_item_allowed(people, access))
		self.assertTrue(sidebar_item_allowed(time, access))
		access["see_agents"] = False
		self.assertFalse(sidebar_item_allowed(people, access))
		self.assertTrue(sidebar_item_allowed(time, access))

	def test_hours_payload_omits_pay_when_switches_are_off(self):
		payload = {
			"rows": [
				{
					"hour_rate": 12,
					"daily_pay": 96,
					"net_daily_pay": 88,
					"ss_deduction": 8,
					"tax_deduction": 0,
					"week_ss": 8,
					"week_tax": 0,
					"total": 8,
				}
			],
			"totals": {
				"daily_pay": 96,
				"net_daily_pay": 88,
				"ss_deduction": 8,
				"total": 8,
			},
		}
		access = {name: True for name in FLAG_NAMES}
		access["see_agent_salary"] = False
		access["see_social_security"] = False
		redacted = redact_hours_payload(payload, access)
		self.assertNotIn("daily_pay", redacted["rows"][0])
		self.assertNotIn("hour_rate", redacted["rows"][0])
		self.assertNotIn("net_daily_pay", redacted["rows"][0])
		self.assertNotIn("ss_deduction", redacted["rows"][0])
		self.assertNotIn("week_ss", redacted["rows"][0])
		self.assertEqual(redacted["rows"][0]["total"], 8)
		self.assertNotIn("daily_pay", redacted["totals"])
		self.assertEqual(redacted["totals"]["total"], 8)

	def test_grant_targets_follow_on_switches(self):
		access = {name: False for name in FLAG_NAMES}
		access["see_agents"] = True
		access["see_attendance"] = True
		targets = switch_grant_targets(access)
		self.assertIn("Employee", targets["doctypes"])
		self.assertIn("Attendance", targets["doctypes"])
		self.assertIn("day-view", targets["pages"])
		self.assertNotIn("Salary Slip", targets["doctypes"])
		self.assertNotIn("Client Invoice", targets["doctypes"])

	def test_master_key_link_is_hidden_without_system_manager(self):
		access = {name: True for name in FLAG_NAMES}
		link = {"type": "Link", "label": "Master Key", "link_to": "master-key", "link_type": "Page"}
		section = {"type": "Section Break", "label": "Master Key"}
		self.assertFalse(sidebar_item_allowed(link, access, is_system_manager=False))
		self.assertTrue(sidebar_item_allowed(link, access, is_system_manager=True))
		rows = [section, link]
		visible = [row for row in rows if sidebar_item_allowed(row, access, is_system_manager=False)]
		self.assertEqual(drop_empty_sections(visible), [])
