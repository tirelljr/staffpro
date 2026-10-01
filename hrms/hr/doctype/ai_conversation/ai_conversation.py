# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


def conversation_user(doc) -> str:
	return getattr(doc, "user", None) or doc.owner


class AIConversation(Document):
	def before_insert(self):
		self.user = frappe.session.user
		self.owner = frappe.session.user
		self.last_message_at = self.last_message_at or now_datetime()

	def validate(self):
		self.user = self.user or frappe.session.user
		if not self.is_new() and conversation_user(self) != frappe.session.user:
			frappe.throw(_("You can only update your own Ask AI conversations."), frappe.PermissionError)


def get_permission_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	escaped = frappe.db.escape(user)
	if frappe.get_meta("AI Conversation").has_field("user"):
		return f"`tabAI Conversation`.user = {escaped}"
	return f"`tabAI Conversation`.owner = {escaped}"


def has_permission(doc, ptype: str | None = None, user: str | None = None, debug: bool = False) -> bool:
	user = user or frappe.session.user
	return conversation_user(doc) == user
