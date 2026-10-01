# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Add Ask AI payroll, agent query, floor, and export capabilities."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import get_custom_fields

NEW_FIELDS = (
	"ask_ai_allow_agent_queries",
	"ask_ai_allow_floors",
	"ask_ai_allow_run_payroll",
	"ask_ai_allow_respond_queries",
	"ask_ai_allow_floor_settings",
	"ask_ai_allow_export",
)


def execute():
	create_custom_fields({"System Settings": get_custom_fields().get("System Settings", [])}, ignore_validate=True)
	frappe.clear_cache(doctype="System Settings")
	if not frappe.get_meta("System Settings").has_field("enable_ask_ai"):
		return
	values = {fieldname: 1 for fieldname in NEW_FIELDS if frappe.get_meta("System Settings").has_field(fieldname)}
	if values:
		frappe.db.set_single_value("System Settings", values)
	frappe.clear_cache(doctype="System Settings")
