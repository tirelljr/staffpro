# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe import bold


class PWANotificationsMixin:
	"""Mixin class for managing PWA updates"""

	def notify_approval_status(self):
		"""Send Leave Application, Expense Claim & Shift Request Approval status notification - to employees"""
		status_field = self._get_doc_status_field()
		status = self.get(status_field)

		if self.has_value_changed(status_field) and status in ["Approved", "Rejected"]:
			from_user = frappe.session.user
			from_user_name = self._get_user_name(from_user)
			to_user = self._get_employee_user()

			if from_user == to_user:
				return

			notification = frappe.new_doc("PWA Notification")
			notification.from_user = from_user
			notification.to_user = to_user

			notification.message = f"{bold('Your')} {bold(self.doctype)} {self.name} has been {bold(status)} by {bold(from_user_name)}"

			notification.reference_document_type = self.doctype
			notification.reference_document_name = self.name
			notification.insert(ignore_permissions=True)

	def notify_approver(self):
		"""Send new Leave Application, Expense Claim & Shift Request request notification - to approvers"""
		from_user = self._get_employee_user()
		to_user = self._get_doc_approver()

		if not to_user or from_user == to_user:
			return

		notification = frappe.new_doc("PWA Notification")
		notification.message = (
			f"{bold(self.employee_name)} raised a new {bold(self.doctype)} for approval: {self.name}"
		)
		notification.from_user = from_user
		notification.to_user = to_user

		notification.reference_document_type = self.doctype
		notification.reference_document_name = self.name
		notification.insert(ignore_permissions=True)

	def _get_doc_status_field(self) -> str:
		APPROVAL_STATUS_FIELD = {
			"Leave Application": "status",
			"Expense Claim": "approval_status",
			"Shift Request": "status",
		}
		return APPROVAL_STATUS_FIELD[self.doctype]

	def _get_doc_approver(self) -> str:
		APPROVER_FIELD = {
			"Leave Application": "leave_approver",
			"Expense Claim": "expense_approver",
			"Shift Request": "approver",
		}
		approver_field = APPROVER_FIELD[self.doctype]
		return self.get(approver_field)

	def notify_hr_request_created(self):
		"""Notify the assignee or HR Managers when a new HR Request is raised."""
		if self.doctype != "HR Request":
			return

		from_user = self._get_employee_user()
		recipients = []
		if self.assigned_to:
			recipients = [self.assigned_to]
		else:
			recipients = self._get_hr_manager_users()

		message = f"{bold(self.employee_name or self.employee)} raised a new {bold(self.request_type or self.doctype)}: {self.name}"
		for to_user in recipients:
			self._insert_pwa_notification(from_user, to_user, message)

	def notify_hr_request_assignee(self):
		"""Notify the newly assigned HR user."""
		if self.doctype != "HR Request" or not self.has_value_changed("assigned_to") or not self.assigned_to:
			return

		from_user = frappe.session.user
		message = f"{bold(self.employee_name or self.employee)} {bold(self.request_type or self.doctype)} {self.name} was assigned to you"
		self._insert_pwa_notification(from_user, self.assigned_to, message)

	def notify_hr_request_status(self):
		"""Notify the employee when HR updates the request status."""
		if self.doctype != "HR Request" or not self.has_value_changed("status"):
			return

		if self.status not in ["In Progress", "Waiting on Employee", "Resolved", "Rejected"]:
			return

		from_user = frappe.session.user
		from_user_name = self._get_user_name(from_user)
		to_user = self._get_employee_user()
		message = f"{bold('Your')} {bold(self.request_type or self.doctype)} {self.name} is now {bold(self.status)} by {bold(from_user_name)}"
		self._insert_pwa_notification(from_user, to_user, message)

	def _insert_pwa_notification(self, from_user, to_user, message):
		if not to_user or from_user == to_user:
			return

		notification = frappe.new_doc("PWA Notification")
		notification.from_user = from_user or frappe.session.user
		notification.to_user = to_user
		notification.message = message
		notification.reference_document_type = self.doctype
		notification.reference_document_name = self.name
		notification.insert(ignore_permissions=True)

	def _get_hr_manager_users(self) -> list[str]:
		users = frappe.get_all(
			"Has Role",
			filters={"role": "HR Manager", "parenttype": "User"},
			pluck="parent",
		)
		if not users:
			return []
		return frappe.get_all(
			"User",
			filters={"name": ["in", users], "enabled": 1, "user_type": "System User"},
			pluck="name",
		)

	def _get_employee_user(self) -> str:
		return frappe.db.get_value("Employee", self.employee, "user_id", cache=True)

	def _get_user_name(self, user) -> str:
		return frappe.db.get_value("User", user, "full_name", cache=True)
