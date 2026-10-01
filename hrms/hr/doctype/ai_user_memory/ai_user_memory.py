# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class AIUserMemory(Document):
	def before_insert(self):
		self.user = self.user or frappe.session.user
		self.owner = self.user
		if self.user != frappe.session.user:
			frappe.throw(_("You can only create Ask AI memory for yourself."), frappe.PermissionError)

	def validate(self):
		self.user = self.user or frappe.session.user
		self.owner = self.user
		if self.user != frappe.session.user:
			frappe.throw(_("You can only update your own Ask AI memory."), frappe.PermissionError)


def get_permission_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	return f"`tabAI User Memory`.user = {frappe.db.escape(user)}"


def has_permission(doc, ptype: str | None = None, user: str | None = None, debug: bool = False) -> bool:
	user = user or frappe.session.user
	return (doc.user or doc.owner) == user
