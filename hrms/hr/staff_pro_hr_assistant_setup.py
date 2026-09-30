# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Provision HR Assistant users with desk permissions and a linked Employee."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.permissions import add_permission, update_permission_property
from frappe.utils import getdate, today

from hrms.hr.staff_pro_roles import (
	HR_ASSISTANT_ROLE,
	clear_employee_user_permissions_for_users,
	sync_hr_assistant_permissions,
)

# Emails that should always be HR Assistants with an Employee record (My Work + desk).
STAFF_PRO_HR_ASSISTANT_USER_EMAILS = (
	"zeeprez@staffpro.com",
)

HR_ASSISTANT_CORE_DOCTYPES: dict[str, tuple[str, ...]] = {
	"Employee": ("read", "write", "select", "create", "report", "export", "print", "email"),
	"Attendance": ("read", "write", "select", "create", "submit", "cancel", "amend", "report", "export"),
	"Employee Checkin": ("read", "write", "select", "create"),
	"Department": ("read", "select"),
	"Shift Type": ("read", "select"),
	"Designation": ("read", "select"),
	"Leave Application": ("read", "write", "select", "create", "submit", "cancel", "delete"),
	"Leave Type": ("read", "select"),
	"Holiday List": ("read", "select"),
	"HR Request": ("read", "write", "select", "create", "delete"),
	"Expense Claim": ("read", "write", "select", "create", "delete", "submit", "cancel"),
	"Salary Slip": ("read", "select", "print", "email"),
}


def apply_hr_assistant_core_permissions() -> None:
	for doctype, ptypes in HR_ASSISTANT_CORE_DOCTYPES.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		add_permission(doctype, HR_ASSISTANT_ROLE, permlevel=0)
		for ptype in ptypes:
			update_permission_property(doctype, HR_ASSISTANT_ROLE, permlevel=0, ptype=ptype, value=1)


def _resolve_user(email: str) -> str | None:
	email = (email or "").strip()
	if not email:
		return None
	if frappe.db.exists("User", email):
		return email
	return frappe.db.get_value("User", {"email": email}, "name")


def _ensure_system_user(email: str) -> str:
	user_name = _resolve_user(email)
	if user_name:
		user = frappe.get_doc("User", user_name)
	else:
		local = email.split("@", 1)[0]
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": local.replace(".", " ").replace("_", " ").title() or "HR",
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		)
		user.flags.ignore_permissions = True
		user.insert()
		user_name = user.name

	user = frappe.get_doc("User", user_name)
	user.enabled = 1
	user.user_type = "System User"
	user.send_welcome_email = 0
	if user.meta.has_field("default_app"):
		user.default_app = "hrms"
	user.flags.ignore_permissions = True
	user.save()

	for role in (HR_ASSISTANT_ROLE, "Employee Self Service"):
		if frappe.db.exists("Role", role):
			user.add_roles(role)

	return user_name


def _default_company() -> str:
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if company:
		return company
	companies = frappe.get_all("Company", pluck="name", limit=1)
	if not companies:
		frappe.throw(_("No Company found. Create a company before provisioning HR Assistants."))
	return companies[0]


def _ensure_employee_for_user(user: str) -> str:
	existing = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if existing:
		frappe.db.set_value("Employee", existing, "status", "Active", update_modified=False)
		return existing

	user_doc = frappe.get_doc("User", user)
	first = (user_doc.first_name or "").strip() or "HR"
	last = (user_doc.last_name or "").strip() or "Assistant"
	employee_name = f"{first} {last}".strip()

	emp = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": first,
			"last_name": last,
			"employee_name": employee_name,
			"company": _default_company(),
			"status": "Active",
			"gender": "Other",
			"date_of_birth": "1990-01-01",
			"date_of_joining": today(),
			"user_id": user,
		}
	)
	emp.flags.ignore_mandatory = True
	emp.flags.ignore_permissions = True
	emp.insert()
	return emp.name


def ensure_hr_assistant_user(email: str) -> dict:
	sync_hr_assistant_permissions()
	apply_hr_assistant_core_permissions()
	user = _ensure_system_user(email)
	frappe.db.delete("User Permission", {"user": user, "allow": "Employee"})
	employee = _ensure_employee_for_user(user)
	frappe.clear_cache(user=user)
	return {"user": user, "employee": employee}


def ensure_staff_pro_hr_assistant_users() -> list[dict]:
	out = []
	for email in STAFF_PRO_HR_ASSISTANT_USER_EMAILS:
		out.append(ensure_hr_assistant_user(email))
	frappe.clear_cache()
	return out
