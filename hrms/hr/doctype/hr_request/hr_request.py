# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

from hrms.mixins.pwa_notifications import PWANotificationsMixin

HR_ROLES = frozenset({"HR User", "HR Manager", "System Manager"})
EMPLOYEE_ALLOWED_STATUSES = frozenset({"Open", "Cancelled"})
CLOSED_STATUSES = frozenset({"Resolved", "Rejected"})


def is_hr_user(user: str | None = None) -> bool:
	return bool(HR_ROLES.intersection(frappe.get_roles(user or frappe.session.user)))


def flt_changed(previous, current) -> bool:
	if previous in (None, "") and current in (None, ""):
		return False
	return flt(previous) != flt(current)


class HRRequest(Document, PWANotificationsMixin):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		addressed_to: DF.Data | None
		assigned_to: DF.Link | None
		assigned_to_name: DF.Data | None
		company: DF.Link | None
		date_of_joining: DF.Date | None
		department: DF.Link | None
		description: DF.Text
		designation: DF.Link | None
		employee: DF.Link
		employee_name: DF.Data | None
		letter_purpose: DF.SmallText | None
		priority: DF.Literal["Low", "Medium", "High"]
		request_type: DF.Link
		resolution: DF.Text | None
		resolved_on: DF.Date | None
		status: DF.Literal[
			"Open", "In Progress", "Waiting on Employee", "Resolved", "Rejected", "Cancelled"
		]
		subject: DF.Data
	# end: auto-generated types

	def validate(self):
		self._set_defaults()
		self._set_resolved_on()
		from hrms.hr.job_letter import prepare_request

		prepare_request(self)
		self._restrict_employee_updates()

	def after_insert(self):
		self.notify_hr_request_created()

	def on_update(self):
		if self.flags.in_insert:
			return
		self.notify_hr_request_assignee()
		self.notify_hr_request_status()
		if self.request_type == "Job Letter" and self.status == "Resolved" and self.has_value_changed("status"):
			from hrms.hr.job_letter import file_approved_letter

			file_approved_letter(self)

	def _lock_letter_fields(self, previous):
		if self.request_type not in {"Job Letter", "Office Print"}:
			return
		locked = (
			"addressed_to",
			"recipient_address",
			"honorific",
			"letter_html",
			"letter_paragraphs",
			"letter_custom",
			"source_request",
			"letter_document",
		)
		for fieldname in locked:
			if (previous.get(fieldname) or "") != (self.get(fieldname) or ""):
				frappe.throw(_("You cannot change this letter after it is submitted"))
		if flt_changed(previous.get("annual_salary"), self.get("annual_salary")) or flt_changed(
			previous.get("biweekly_salary"), self.get("biweekly_salary")
		):
			frappe.throw(_("You cannot change this letter after it is submitted"))

	def _set_defaults(self):
		if not self.priority:
			self.priority = "Medium"
		if not self.status:
			self.status = "Open"
		if not self.subject and self.request_type:
			self.subject = _("{0} Request").format(self.request_type)

	def _restrict_employee_updates(self):
		if is_hr_user():
			return

		if self.status not in EMPLOYEE_ALLOWED_STATUSES:
			frappe.throw(_("You cannot set this request to {0}").format(_(self.status)))

		if self.is_new() and self.assigned_to:
			frappe.throw(_("You cannot assign this request"))

		if not self.is_new():
			previous = self.get_doc_before_save()
			if previous:
				if previous.assigned_to != self.assigned_to:
					frappe.throw(_("You cannot assign this request"))
				if previous.resolution != self.resolution or previous.resolved_on != self.resolved_on:
					frappe.throw(_("You cannot update the resolution"))
				if previous.status not in EMPLOYEE_ALLOWED_STATUSES and previous.status != self.status:
					frappe.throw(_("You cannot change the status of this request"))
				self._lock_letter_fields(previous)

	def _set_resolved_on(self):
		if self.status in CLOSED_STATUSES and not self.resolved_on:
			self.resolved_on = today()
		elif self.status not in CLOSED_STATUSES:
			self.resolved_on = None
