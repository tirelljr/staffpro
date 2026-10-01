# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Desk visibility for Staff Pro: sidebar links, dock areas, and employee profile stats."""

from __future__ import annotations

import frappe

from hrms.hr.bpo_sidebar_labels import apply_bpo_labels, _drop_empty_sections
from hrms.hr.staff_pro_roles import is_staff_pro_hr_desk_user
from hrms.hr.staff_pro_sidebars import filter_removed_sidebar_items

USER_STAT_RESTRICTION_FIELDS = {
	"agent_profit": "sp_restrict_agent_profit",
	"total_billed": "sp_restrict_billed_to_client",
	"payroll_totals": "sp_restrict_payroll_totals",
}


def _session_user(user=None) -> str:
	return user or frappe.session.user


def _user_restriction_flag(user: str, fieldname: str) -> bool:
	meta = frappe.get_meta("User")
	if not meta.has_field(fieldname):
		return False
	return bool(frappe.db.get_value("User", user, fieldname))


def get_profile_stat_visibility(user=None) -> dict[str, bool]:
	"""Which employee sidebar totals the signed-in user may see."""
	from hrms.hr.role_access import can_see

	user = _session_user(user)
	if user == "Guest":
		return {key: False for key in USER_STAT_RESTRICTION_FIELDS}

	sees_salary = can_see("see_agent_salary", user)
	sees_billing = can_see("see_bill_to_client", user) or can_see("see_client_invoices", user)
	sees_ss = can_see("see_social_security", user)
	flags = {
		"agent_profit": sees_salary and sees_billing,
		"total_billed": sees_billing,
		"payroll_totals": sees_salary,
		"ss_totals": sees_ss,
	}
	for stat_key, fieldname in USER_STAT_RESTRICTION_FIELDS.items():
		if _user_restriction_flag(user, fieldname):
			flags[stat_key] = False

	# Always allow operational stats when Employee is readable.
	can_read_employee = frappe.has_permission("Employee", "read", user=user)
	flags["total_hours"] = can_read_employee and frappe.has_permission("Attendance", "read", user=user)
	flags["leave_remaining"] = can_read_employee and frappe.has_permission("Leave Application", "read", user=user)
	return flags


def filter_profile_stats_payload(stats: dict, user=None) -> dict:
	"""Remove sensitive totals from API responses."""
	visibility = dict(get_profile_stat_visibility(user))
	out = dict(stats)
	if not out.get("has_client_billing", True):
		visibility["total_billed"] = False
		visibility["agent_profit"] = False
	if not visibility.get("payroll_totals"):
		out.pop("total_income", None)
	if not visibility.get("ss_totals"):
		for key in ("total_ss", "total_tax"):
			out.pop(key, None)
	if not visibility.get("total_billed"):
		out.pop("total_billed", None)
		out.pop("billing_currency", None)
	if not visibility.get("agent_profit"):
		out.pop("agent_profit", None)
	out["visibility"] = visibility
	return out


def can_access_sidebar_link(link_type: str | None, link_to: str | None, user=None) -> bool:
	user = _session_user(user)
	if user == "Guest":
		return False
	if user == "Administrator":
		return True

	link_type = (link_type or "").strip()
	link_to = (link_to or "").strip()
	if not link_to:
		return True

	if link_type == "DocType":
		if not frappe.db.exists("DocType", link_to):
			return False
		return frappe.has_permission(link_to, "read", user=user)

	if link_type == "Report":
		if not frappe.db.exists("Report", link_to):
			return False
		return frappe.has_permission(link_to, "report", user=user)

	if link_type == "Page":
		if not frappe.db.exists("Page", link_to):
			return False
		roles = frappe.get_roles(user)
		page_roles = frappe.get_all("Has Role", filters={"parent": link_to, "parenttype": "Page"}, pluck="role")
		if not page_roles:
			return True
		return bool(set(page_roles) & set(roles))

	if link_type == "Dashboard":
		if not frappe.db.exists("Dashboard", link_to):
			return False
		return frappe.has_permission("Dashboard", "read", user=user)

	return True


def filter_sidebar_rows(rows: list | None, user=None) -> list:
	"""Drop sidebar links the user cannot open; remove empty section headers."""
	if not rows:
		return []

	user = _session_user(user)
	rows = filter_removed_sidebar_items([dict(row) for row in rows if isinstance(row, dict)])
	if is_staff_pro_hr_desk_user(user):
		return _drop_empty_sections(apply_bpo_labels(rows))

	filtered: list[dict] = []
	for row in rows:
		if not isinstance(row, dict):
			continue
		item = dict(row)
		if item.get("type") == "Section Break":
			filtered.append(item)
			continue
		link_type = item.get("link_type")
		link_to = item.get("link_to")
		if link_to and not can_access_sidebar_link(link_type, link_to, user=user):
			continue
		filtered.append(item)

	return _drop_empty_sections(apply_bpo_labels(filtered))


def filter_boot_sidebar_payload(sidebars, user=None):
	"""Filter workspace_sidebar_item / module_sidebars dicts in bootinfo."""
	if not sidebars:
		return sidebars

	if isinstance(sidebars, dict):
		for key, value in list(sidebars.items()):
			if isinstance(value, list):
				sidebars[key] = filter_sidebar_rows(value, user=user)
			elif isinstance(value, dict) and isinstance(value.get("items"), list):
				value["items"] = filter_sidebar_rows(value["items"], user=user)
		return sidebars

	if isinstance(sidebars, list):
		return filter_sidebar_rows(sidebars, user=user)

	return sidebars


def filter_dock_entries(entries: list | None, user=None) -> list:
	user = _session_user(user)
	if not entries:
		return []
	out = []
	for entry in entries:
		if not isinstance(entry, dict):
			continue
		link_type = entry.get("link_type") or "Sidebar"
		link_to = entry.get("link_to") or entry.get("title") or entry.get("name")
		if link_type == "Sidebar" and link_to:
			if not frappe.db.exists("DocType", "Sidebar") or not frappe.db.exists("Sidebar", link_to):
				out.append(entry)
				continue
			doc = frappe.get_doc("Sidebar", link_to)
			if filter_sidebar_rows([dict(row.as_dict()) for row in doc.items], user=user):
				out.append(entry)
			continue
		if can_access_sidebar_link(link_type, link_to, user=user):
			out.append(entry)
	return out
