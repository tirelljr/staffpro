# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Keep the Ask AI tab immediately before Email on System Settings."""

import frappe

from hrms.setup import _system_settings_field_before_email


def execute():
	name = frappe.db.get_value("Custom Field", {"dt": "System Settings", "fieldname": "ask_ai_tab"})
	if not name:
		return
	insert_after = _system_settings_field_before_email()
	doc = frappe.get_doc("Custom Field", name)
	if doc.insert_after == insert_after:
		return
	doc.insert_after = insert_after
	doc.save()
	frappe.clear_cache(doctype="System Settings")
