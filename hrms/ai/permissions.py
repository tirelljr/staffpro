# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe
from frappe import _

AI_ROLES = frozenset({"HR User", "HR Manager", "System Manager", "Administrator"})


def ensure_ai_access(user: str | None = None) -> None:
	from hrms.ai.settings import is_ask_ai_enabled

	user = user or frappe.session.user
	if user == "Guest" or not AI_ROLES.intersection(frappe.get_roles(user)):
		frappe.throw(_("You do not have permission to use Ask AI."), frappe.PermissionError)
	if not is_ask_ai_enabled():
		frappe.throw(_("Ask AI is turned off. Enable it in System Settings > AI."))


def ensure_conversation_access(name: str):
	from hrms.hr.doctype.ai_conversation.ai_conversation import conversation_user

	ensure_ai_access()
	doc = frappe.get_doc("AI Conversation", name)
	if conversation_user(doc) != frappe.session.user:
		frappe.throw(_("You do not have permission to access this conversation."), frappe.PermissionError)
	return doc
