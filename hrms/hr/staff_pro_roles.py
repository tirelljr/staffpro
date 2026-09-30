# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Staff Pro desk roles: HR desk staff vs agent portal users."""

from __future__ import annotations

import frappe
from frappe.permissions import add_permission, update_permission_property

# Full HR desk (People / Time sidebars, all employees, not agent portal).
STAFF_PRO_HR_DESK_ROLES = frozenset(
	{
		"Administrator",
		"System Manager",
		"HR Manager",
		"HR User",
		"HR Assistant",
		"Leave Approver",
		"Expense Approver",
	}
)

# Agents and ESS users stay on the employee portal even when user_type is System User.
AGENT_PORTAL_ROLES = frozenset({"Employee Self Service", "Employee"})

HR_ASSISTANT_ROLE = "HR Assistant"
HR_PERMISSION_SOURCE_ROLE = "HR User"

DOC_PERM_PTYPES = (
	"permlevel",
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
	"if_owner",
	"select",
)


def user_roles(user: str | None = None) -> set[str]:
	user = user or frappe.session.user
	return set(frappe.get_roles(user)) - {"All"}


def is_staff_pro_hr_desk_user(user: str | None = None) -> bool:
	return bool(user_roles(user) & STAFF_PRO_HR_DESK_ROLES)


def is_agent_portal_user(user: str | None = None) -> bool:
	"""True for agents/ESS — not the HR desk shell."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return False

	if is_staff_pro_hr_desk_user(user):
		return False

	if frappe.get_cached_value("User", user, "user_type") == "Website User":
		return True

	roles = user_roles(user)
	return bool(roles) and roles.issubset(AGENT_PORTAL_ROLES)


def ensure_hr_assistant_role() -> None:
	if frappe.db.exists("Role", HR_ASSISTANT_ROLE):
		if not frappe.db.get_value("Role", HR_ASSISTANT_ROLE, "desk_access"):
			frappe.db.set_value("Role", HR_ASSISTANT_ROLE, "desk_access", 1, update_modified=False)
		return

	frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": HR_ASSISTANT_ROLE,
			"desk_access": 1,
			"is_custom": 1,
		}
	).insert(ignore_permissions=True)


def _perm_rows_for_role(role: str, table: str) -> list[dict]:
	if not frappe.db.table_exists(table):
		return []
	return frappe.get_all(
		table,
		filters={"role": role},
		fields=["name", "parent", *DOC_PERM_PTYPES],
	)


def copy_role_docperms(from_role: str, to_role: str) -> None:
	for table in ("DocPerm", "Custom DocPerm"):
		for row in _perm_rows_for_role(from_role, table):
			doctype = row.pop("parent")
			row.pop("name", None)
			add_permission(doctype, to_role, permlevel=row.get("permlevel") or 0)
			for ptype in DOC_PERM_PTYPES:
				if ptype == "permlevel":
					continue
				value = row.get(ptype)
				if value is None:
					continue
				update_permission_property(
					doctype,
					to_role,
					permlevel=row.get("permlevel") or 0,
					ptype=ptype,
					value=value,
				)


def mirror_role_sidebar_tables(from_role: str, to_role: str) -> None:
	"""Copy Role sidebar child tables (People / Time grants) from HR User when present."""
	if not frappe.db.exists("Role", from_role) or not frappe.db.exists("Role", to_role):
		return

	src = frappe.get_doc("Role", from_role)
	dst = frappe.get_doc("Role", to_role)
	changed = False
	hints = ("sidebar", "desk", "module", "workspace")

	for field in frappe.get_meta("Role").fields:
		if field.fieldtype not in ("Table", "Table MultiSelect"):
			continue
		fieldname = (field.fieldname or "").lower()
		options = (field.options or "").lower()
		if not any(token in fieldname or token in options for token in hints):
			continue
		if not (src.get(field.fieldname) or []):
			continue
		dst.set(field.fieldname, [])
		for row in src.get(field.fieldname):
			dst.append(field.fieldname, row.as_dict(no_default_fields=True))
		changed = True

	if changed:
		dst.flags.ignore_links = True
		dst.flags.ignore_permissions = True
		dst.save()


def clear_employee_user_permissions_for_users(role: str) -> None:
	users = frappe.get_all(
		"Has Role",
		filters={"parenttype": "User", "role": role},
		pluck="parent",
	)
	for user in users:
		frappe.db.delete("User Permission", {"user": user, "allow": "Employee"})


def sync_hr_assistant_permissions() -> None:
	ensure_hr_assistant_role()
	if frappe.db.exists("Role", HR_PERMISSION_SOURCE_ROLE):
		copy_role_docperms(HR_PERMISSION_SOURCE_ROLE, HR_ASSISTANT_ROLE)
		mirror_role_sidebar_tables(HR_PERMISSION_SOURCE_ROLE, HR_ASSISTANT_ROLE)
	clear_employee_user_permissions_for_users(HR_ASSISTANT_ROLE)
	frappe.clear_cache()
