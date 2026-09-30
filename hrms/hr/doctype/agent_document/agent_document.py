# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

HR_ROLES = frozenset({"HR User", "HR Manager", "System Manager", "Administrator"})


class AgentDocument(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		category: DF.Link
		employee: DF.Link
		employee_name: DF.Data | None
		file: DF.Attach
		file_name: DF.Data | None
		notes: DF.SmallText | None
		uploaded_by: DF.Link | None
		uploaded_on: DF.Datetime | None
	# end: auto-generated types

	def validate(self):
		if self.employee and not self.employee_name:
			self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")
		if not self.uploaded_by:
			self.uploaded_by = frappe.session.user
		if not self.uploaded_on:
			self.uploaded_on = now_datetime()
		if not self.file_name and self.file:
			self.file_name = self.file.rsplit("/", 1)[-1]
		if not self.flags.ignore_permissions:
			assert_can_store(self.employee)
			if not self.is_new() and self.uploaded_by and self.uploaded_by != frappe.session.user and not is_hr_user():
				frappe.throw(_("You can only change files you uploaded."), frappe.PermissionError)

	def on_trash(self):
		if not self.flags.ignore_permissions and not has_permission(self, "delete"):
			frappe.throw(_("You can only delete files you uploaded."), frappe.PermissionError)
		for name in frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Agent Document", "attached_to_name": self.name},
			pluck="name",
		):
			frappe.delete_doc("File", name, ignore_permissions=True, force=True)


def is_hr_user(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(HR_ROLES.intersection(frappe.get_roles(user)))


def get_session_employee(user: str | None = None) -> str | None:
	return frappe.db.get_value(
		"Employee",
		{"user_id": user or frappe.session.user, "status": "Active"},
		"name",
	)


def assert_can_store(employee: str, user: str | None = None) -> None:
	user = user or frappe.session.user
	if is_hr_user(user):
		return
	if get_session_employee(user) == employee:
		return
	frappe.throw(_("You can only store files in your own folder."), frappe.PermissionError)


def get_permission_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_hr_user(user):
		return ""
	employee = get_session_employee(user)
	if not employee:
		return "1=0"
	return f"`tabAgent Document`.employee = {frappe.db.escape(employee)}"


def has_permission(doc, ptype=None, user=None, debug=False) -> bool:
	user = user or frappe.session.user
	if is_hr_user(user):
		return True
	employee = get_session_employee(user)
	if not employee or doc.employee != employee:
		return False
	if ptype in ("delete", "write"):
		return doc.uploaded_by == user
	return True
