# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Belize timezone default and Ask AI fields on System Settings."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.branding import apply_branding, ensure_belize_timezone
from hrms.setup import get_custom_fields


def execute():
	create_custom_fields({"System Settings": get_custom_fields().get("System Settings", [])}, ignore_validate=True)
	apply_branding()
	ensure_belize_timezone()
	_migrate_legacy_ai_settings()
	frappe.clear_cache(doctype="System Settings")


def _migrate_legacy_ai_settings():
	if not frappe.db.exists("DocType", "AI Settings"):
		return
	if not frappe.get_meta("System Settings").has_field("enable_ask_ai"):
		return
	legacy = frappe.get_single("AI Settings")
	values = {
		"enable_ask_ai": legacy.enabled,
		"ask_ai_provider": "DeepSeek",
		"ask_ai_model": legacy.model or "deepseek-chat",
		"ask_ai_api_base": legacy.api_base or "https://api.deepseek.com",
		"ask_ai_temperature": legacy.temperature or 0,
		"ask_ai_max_tool_rounds": legacy.max_tool_rounds or 6,
	}
	for fieldname, value in values.items():
		if frappe.get_meta("System Settings").has_field(fieldname):
			frappe.db.set_single_value("System Settings", fieldname, value)

	api_key = legacy.get_password("deepseek_api_key", raise_exception=False)
	if api_key and frappe.get_meta("System Settings").has_field("ask_ai_api_key"):
		settings = frappe.get_doc("System Settings")
		settings.ask_ai_api_key = api_key
		settings.save(ignore_permissions=True)
