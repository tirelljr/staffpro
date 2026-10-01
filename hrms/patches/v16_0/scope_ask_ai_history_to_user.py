# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Scope Ask AI conversations and memory to the signed-in user."""

import frappe


def execute():
	if frappe.db.exists("DocType", "AI Conversation") and frappe.get_meta("AI Conversation").has_field("user"):
		frappe.db.sql(
			"""
			update `tabAI Conversation`
			set `user` = owner
			where ifnull(`user`, '') = ''
			"""
		)
	frappe.clear_cache(doctype="AI Conversation")
	if frappe.db.exists("DocType", "AI User Memory"):
		frappe.clear_cache(doctype="AI User Memory")
