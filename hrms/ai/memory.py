# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe
from frappe.utils import cstr, strip_html

MAX_MEMORY_CHARS = 4000
MAX_MEMORY_LINES = 25


def current_user() -> str:
	return frappe.session.user


def get_user_memory(user: str | None = None) -> str:
	user = user or current_user()
	if not user or user == "Guest" or not frappe.db.exists("DocType", "AI User Memory"):
		return ""
	return cstr(frappe.db.get_value("AI User Memory", {"user": user}, "summary"))


def get_last_conversation(user: str | None = None) -> str | None:
	user = user or current_user()
	if not user or user == "Guest" or not frappe.db.exists("DocType", "AI User Memory"):
		return None
	name = frappe.db.get_value("AI User Memory", {"user": user}, "last_conversation")
	if not name or not frappe.db.exists("AI Conversation", name):
		return None
	fields = ["owner"]
	if frappe.get_meta("AI Conversation").has_field("user"):
		fields.insert(0, "user")
	row = frappe.db.get_value("AI Conversation", name, fields, as_dict=True)
	if not row:
		return None
	owner = row.get("user") or row.get("owner")
	return name if owner == user else None


def clear_last_conversation(conversation: str, user: str | None = None) -> None:
	user = user or current_user()
	if not conversation or not user or user == "Guest" or not frappe.db.exists("DocType", "AI User Memory"):
		return
	name = frappe.db.get_value("AI User Memory", {"user": user, "last_conversation": conversation})
	if name:
		frappe.db.set_value("AI User Memory", name, "last_conversation", "", update_modified=False)


def remember_exchange(
	title: str,
	user_message: str,
	assistant_message: str,
	conversation: str | None = None,
	user: str | None = None,
) -> None:
	user = user or current_user()
	if not user or user == "Guest" or not frappe.db.exists("DocType", "AI User Memory"):
		return

	snippet = _snippet(title, user_message, assistant_message)
	name = frappe.db.get_value("AI User Memory", {"user": user})
	if name:
		doc = frappe.get_doc("AI User Memory", name)
	else:
		doc = frappe.new_doc("AI User Memory")
		doc.user = user
		doc.owner = user
	lines = [snippet, *[line for line in cstr(doc.summary).splitlines() if line.strip() and line != snippet]]
	doc.summary = "\n".join(lines[:MAX_MEMORY_LINES])[:MAX_MEMORY_CHARS]
	if conversation:
		doc.last_conversation = conversation
	doc.flags.ignore_permissions = True
	if doc.is_new():
		doc.insert()
	else:
		doc.save()


def _snippet(title: str, user_message: str, assistant_message: str) -> str:
	ask = strip_html(user_message or "").replace("\n", " ").strip()[:180]
	reply = strip_html(assistant_message or "").replace("\n", " ").strip()[:220]
	label = strip_html(title or "Chat").strip()[:80]
	return f"- {label}: {ask} → {reply}".strip(" →")
