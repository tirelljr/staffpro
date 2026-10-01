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
MY_WORK_PORTAL_PATH = "/agents/dashboard/attendance"

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


def is_hr_assistant_user(user: str | None = None) -> bool:
	return HR_ASSISTANT_ROLE in user_roles(user)


def employee_is_hr_assistant(employee: str | None = None, user_id: str | None = None) -> bool:
	user = user_id
	if not user and employee:
		user = frappe.db.get_value("Employee", employee, "user_id")
	return bool(user) and is_hr_assistant_user(user)


def employee_is_client_billable(
	employee: str | None = None,
	user_id: str | None = None,
	is_floor: int | bool | None = None,
) -> bool:
	"""Floor workers and HR Assistants are internal staff and are not billed to a client."""
	if is_floor is None and employee and frappe.get_meta("Employee").has_field("is_floor_worker"):
		is_floor = frappe.db.get_value("Employee", employee, "is_floor_worker")
	if is_floor:
		return False
	return not employee_is_hr_assistant(employee, user_id)


def employees_without_client_billing(names: list[str] | None) -> set[str]:
	if not names:
		return set()
	fields = ["name", "user_id"]
	if frappe.get_meta("Employee").has_field("is_floor_worker"):
		fields.append("is_floor_worker")
	flagged = set()
	for row in frappe.get_all("Employee", filters={"name": ("in", names)}, fields=fields):
		if not employee_is_client_billable(
			row.name, user_id=row.user_id, is_floor=row.get("is_floor_worker")
		):
			flagged.add(row.name)
	return flagged


def apply_internal_staff_billing_rules(doc) -> None:
	"""HR Assistants are never billed to a client."""
	if not employee_is_hr_assistant(doc.get("name"), user_id=doc.get("user_id")):
		return
	meta = getattr(doc, "meta", None) or frappe.get_meta("Employee")
	if meta.has_field("bill_to_customer"):
		doc.bill_to_customer = None
	if meta.has_field("billing_rate"):
		doc.billing_rate = 0


def linked_active_employee(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def can_use_my_work_portal(user: str | None = None) -> bool:
	"""HR Assistants with an active Employee record may open the agent PWA."""
	return is_hr_assistant_user(user) and bool(linked_active_employee(user))


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


def merge_ess_docperms_for_hr_assistant() -> None:
	from hrms.setup import get_user_types_data

	ess_doctypes = get_user_types_data().get("Employee Self Service", {}).get("doctypes", {})
	for doctype, perms in ess_doctypes.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		add_permission(doctype, HR_ASSISTANT_ROLE, permlevel=0)
		for ptype in perms:
			update_permission_property(doctype, HR_ASSISTANT_ROLE, permlevel=0, ptype=ptype, value=1)


def sync_hr_assistant_permissions() -> None:
	from hrms.hr.staff_pro_hr_assistant_setup import apply_hr_assistant_core_permissions

	ensure_hr_assistant_role()
	if frappe.db.exists("Role", HR_PERMISSION_SOURCE_ROLE):
		copy_role_docperms(HR_PERMISSION_SOURCE_ROLE, HR_ASSISTANT_ROLE)
		mirror_role_sidebar_tables(HR_PERMISSION_SOURCE_ROLE, HR_ASSISTANT_ROLE)
	merge_ess_docperms_for_hr_assistant()
	apply_hr_assistant_core_permissions()
	clear_employee_user_permissions_for_users(HR_ASSISTANT_ROLE)
	frappe.clear_cache()
