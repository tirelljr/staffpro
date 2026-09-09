# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Keep the User Roles & Permissions tab on Staff Pro BPO roles and modules."""

from __future__ import annotations

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint

# Roles that belong on the User form for this call-center HR / payroll desk.
BPO_ROLES = frozenset(
	{
		"System Manager",
		"HR Manager",
		"HR User",
		"Leave Approver",
		"Expense Approver",
		"Employee",
		"Employee Self Service",
		"Accounts Manager",
		"Accounts User",
		"Interviewer",
		"Workspace Manager",
		"Payroll Manager",
		"Payroll User",
	}
)

# Framework roles must stay enabled even though they are hidden from the picker.
NEVER_DISABLE_ROLES = frozenset(
	{
		"Administrator",
		"All",
		"Guest",
		"Desk User",
	}
)

# Sidebar modules shown on the User form, in dock / left-nav order.
BPO_SIDEBAR_MODULES = (
	("people", "People"),
	("time", "Time"),
	("pay", "Pay"),
	("talent", "Talent"),
	("floor", "Floor"),
	("ss and taxes", "SS and Taxes"),
	("finance", "Finance"),
	("admin", "Admin"),
)

BPO_SIDEBAR_KEYS = frozenset(key for key, _label in BPO_SIDEBAR_MODULES)

SIDEBAR_KEY_ALIASES = {
	"workforce": "people",
	"payroll": "pay",
	"ss and taxes": "ss and taxes",
	"floor plan": "floor",
	"floorplan": "floor",
}

# Module Defs kept unblocked so HR / payroll / finance doctypes still load.
BPO_MODULE_DEFS = frozenset(
	{
		"HR",
		"Payroll",
		"Accounts",
	}
)

BPO_MODULE_LABELS = {
	"HR": "People",
	"Payroll": "Pay",
	"Accounts": "Finance",
}

# Keep desk / email / setup available even when hidden from the User picker.
NEVER_BLOCK_MODULES = frozenset(
	{
		"Core",
		"Desk",
		"Email",
		"Workflow",
		"Custom",
		"Printing",
		"Contacts",
		"Setup",
	}
)

BLOCKED_BPO_MODULES_FIELD = "blocked_bpo_modules"


@frappe.whitelist()
def get_all_roles():
	"""User and Role Profile pickers: only Staff Pro BPO roles."""
	from frappe.core.doctype.user.user import get_all_roles as _get_all_roles

	return [role for role in _get_all_roles() if role in BPO_ROLES]


def canonical_sidebar_key(name) -> str:
	key = str(name or "").strip().lower().replace("-", " ").replace("_", " ")
	key = " ".join(key.split())
	return SIDEBAR_KEY_ALIASES.get(key, key)


def parse_blocked_bpo_modules(raw) -> set[str]:
	if not raw:
		return set()
	if isinstance(raw, (list, tuple, set)):
		data = list(raw)
	else:
		try:
			data = json.loads(raw)
		except (TypeError, ValueError):
			data = [part.strip() for part in str(raw).split(",") if part.strip()]
	if not isinstance(data, list):
		return set()
	return {canonical_sidebar_key(item) for item in data if item}


def get_blocked_bpo_modules(user=None) -> set[str]:
	user = user or frappe.session.user
	if not user or user in {"Guest", "Administrator"}:
		return set()
	if not frappe.get_meta("User").has_field(BLOCKED_BPO_MODULES_FIELD):
		return set()
	return parse_blocked_bpo_modules(frappe.db.get_value("User", user, BLOCKED_BPO_MODULES_FIELD))


def get_allowed_bpo_sidebar_keys(user=None) -> frozenset[str] | None:
	"""None means every Staff Pro sidebar is allowed."""
	blocked = get_blocked_bpo_modules(user)
	if not blocked:
		return None
	return frozenset(key for key in BPO_SIDEBAR_KEYS if key not in blocked)


def sidebar_module_boot_list() -> list[dict]:
	return [{"value": key, "label": label} for key, label in BPO_SIDEBAR_MODULES]


def filter_user_modules_onload(doc, method=None):
	"""Hide ERPNext Module Defs. The User form renders Staff Pro sidebars instead."""
	if getattr(doc, "doctype", None) == "User":
		doc.set_onload("all_modules", [])
		return

	modules = doc.get_onload("all_modules")
	if not modules:
		return
	visible = [module for module in modules if module in BPO_MODULE_DEFS]
	if visible:
		doc.set_onload("all_modules", visible)


def enforce_bpo_block_modules(doc, method=None):
	"""Keep ERPNext modules blocked when a User is saved."""
	if getattr(doc, "doctype", None) != "User":
		return
	if not doc.meta.has_field("block_modules"):
		return

	blocked = {row.module for row in doc.get("block_modules") or [] if row.module}
	for module in get_auto_blocked_modules():
		if module not in blocked:
			doc.append("block_modules", {"module": module})
			blocked.add(module)


def apply_bpo_user_permissions():
	"""Disable leftover ERPNext roles and hide Module Profile on User."""
	ensure_user_fields()
	disable_unused_erpnext_roles()
	hide_user_module_profile_field()
	block_unused_modules_for_all_users()


def ensure_user_fields():
	if not frappe.db.exists("DocType", "User"):
		return
	create_custom_fields(
		{
			"User": [
				{
					"fieldname": BLOCKED_BPO_MODULES_FIELD,
					"label": "Blocked BPO Modules",
					"fieldtype": "Small Text",
					"hidden": 1,
					"insert_after": "block_modules",
				}
			]
		},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="User")


def disable_unused_erpnext_roles():
	if not frappe.db.exists("DocType", "Role"):
		return
	if not frappe.get_meta("Role").has_field("disabled"):
		return

	for role in frappe.get_all("Role", fields=["name", "disabled"]):
		name = role.name
		if name in NEVER_DISABLE_ROLES:
			continue
		should_disable = 0 if name in BPO_ROLES else 1
		if cint(role.disabled) == should_disable:
			continue
		frappe.db.set_value("Role", name, "disabled", should_disable, update_modified=False)


def hide_user_module_profile_field():
	if not frappe.db.exists("DocType", "User"):
		return
	if not frappe.get_meta("User").has_field("module_profile"):
		return

	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	make_property_setter(
		"User",
		"module_profile",
		"hidden",
		1,
		"Check",
		validate_fields_for_doctype=False,
	)
	frappe.clear_cache(doctype="User")


def get_auto_blocked_modules() -> list[str]:
	try:
		from frappe.utils.modules import get_modules_from_all_apps
	except ImportError:
		return []

	names = {row.get("module_name") for row in get_modules_from_all_apps() if row.get("module_name")}
	return sorted(name for name in names if name not in BPO_MODULE_DEFS and name not in NEVER_BLOCK_MODULES)


def block_unused_modules_for_all_users():
	if not frappe.db.exists("DocType", "User") or not frappe.db.exists("DocType", "Block Module"):
		return

	unused = get_auto_blocked_modules()
	if not unused:
		return

	existing = {
		(row.parent, row.module)
		for row in frappe.get_all("Block Module", fields=["parent", "module"], filters={"parenttype": "User"})
	}
	for user in frappe.get_all("User", pluck="name"):
		for module in unused:
			if (user, module) in existing:
				continue
			child = frappe.new_doc("Block Module")
			child.parent = user
			child.parenttype = "User"
			child.parentfield = "block_modules"
			child.module = module
			child.db_insert()
			existing.add((user, module))
