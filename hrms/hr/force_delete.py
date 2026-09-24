# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Let desk deletes succeed by clearing leftover links first."""

from __future__ import annotations

import frappe
from frappe.utils import cint

PROTECTED_DOCS = frozenset(
	{
		("User", "Administrator"),
		("User", "Guest"),
		("Role", "Administrator"),
		("Role", "All"),
		("Role", "Guest"),
		("Role", "Desk User"),
		("Role", "System Manager"),
	}
)

NO_HARD_DELETE = frozenset(
	{
		"DocType",
		"DocField",
		"DocPerm",
		"Module Def",
		"Patch Log",
		"Installed Application",
	}
)

NO_CASCADE_DELETE = NO_HARD_DELETE | frozenset(
	{
		"User",
		"Company",
		"Account",
		"Cost Center",
		"Warehouse",
		"Currency",
		"Fiscal Year",
		"Role",
	}
)

ROLE_CHILD_TABLES = (
	("Has Role", "role"),
	("DocPerm", "role"),
	("Custom DocPerm", "role"),
	("Custom Role", "role"),
	("User Document Type", "role"),
	("Notification Recipient", "role"),
	("Auto Email Report", "role"),
	("Workspace Sidebar", "role"),
)

_LINK_CACHE: dict[str, list[tuple[str, str]]] = {}
_PATCHED = False


def is_protected(doctype: str, name: str) -> bool:
	return (doctype, name) in PROTECTED_DOCS


def _link_fields_to(doctype: str) -> list[tuple[str, str]]:
	cached = _LINK_CACHE.get(doctype)
	if cached is not None:
		return cached

	seen: set[tuple[str, str]] = set()
	if frappe.db.exists("DocType", "DocField"):
		for row in frappe.get_all(
			"DocField",
			filters={"fieldtype": "Link", "options": doctype},
			fields=["parent", "fieldname"],
		):
			if row.parent and row.fieldname:
				seen.add((row.parent, row.fieldname))
	if frappe.db.exists("DocType", "Custom Field"):
		for row in frappe.get_all(
			"Custom Field",
			filters={"fieldtype": "Link", "options": doctype},
			fields=["dt as parent", "fieldname"],
		):
			if row.parent and row.fieldname:
				seen.add((row.parent, row.fieldname))
	_LINK_CACHE[doctype] = list(seen)
	return _LINK_CACHE[doctype]


def _cancel_if_submitted(doctype: str, name: str) -> None:
	if not frappe.db.exists(doctype, name):
		return
	meta = frappe.get_meta(doctype)
	if not meta.is_submittable:
		return
	if cint(frappe.db.get_value(doctype, name, "docstatus")) != 1:
		return
	if doctype == "Leave Ledger Entry":
		frappe.db.set_value(doctype, name, "docstatus", 2, update_modified=False)
		return
	try:
		doc = frappe.get_doc(doctype, name)
		doc.flags.ignore_permissions = True
		doc.flags.ignore_links = True
		doc.cancel()
	except Exception:
		frappe.db.set_value(doctype, name, "docstatus", 2, update_modified=False)


def _clear_or_drop_links(doctype: str, fieldname: str, name: str) -> None:
	if doctype in NO_HARD_DELETE or not frappe.db.exists("DocType", doctype):
		return
	if not frappe.db.table_exists(doctype):
		return
	meta = frappe.get_meta(doctype)
	if not meta.has_field(fieldname):
		return
	if meta.istable:
		frappe.db.delete(doctype, {fieldname: name})
		return
	field = meta.get_field(fieldname)
	if field and not field.reqd:
		frappe.db.set_value(doctype, {fieldname: name}, fieldname, None, update_modified=False)
		return
	if doctype in NO_CASCADE_DELETE:
		return
	for linked in frappe.get_all(doctype, filters={fieldname: name}, pluck="name"):
		if is_protected(doctype, linked):
			continue
		_cancel_if_submitted(doctype, linked)
		try:
			frappe.delete_doc(doctype, linked, force=True, ignore_permissions=True)
		except Exception:
			_hard_delete(doctype, linked)


def unlink_role(role: str) -> None:
	for doctype, fieldname in ROLE_CHILD_TABLES:
		if not frappe.db.exists("DocType", doctype) or not frappe.db.table_exists(doctype):
			continue
		if not frappe.get_meta(doctype).has_field(fieldname):
			continue
		frappe.db.delete(doctype, {fieldname: role})

	for doctype, fieldname in _link_fields_to("Role"):
		_clear_or_drop_links(doctype, fieldname, role)


def unlink_blocking_links(doctype: str, name: str) -> None:
	if doctype == "Employee":
		from hrms.hr.employee_cleanup import unlink_employee_records

		unlink_employee_records(name, skip_permission=True)
		return
	if doctype == "Role":
		unlink_role(name)
		return
	for link_dt, fieldname in _link_fields_to(doctype):
		_clear_or_drop_links(link_dt, fieldname, name)


def _hard_delete(doctype: str, name: str) -> None:
	if doctype in NO_HARD_DELETE or is_protected(doctype, name):
		return
	if frappe.db.table_exists(doctype):
		frappe.db.delete(doctype, {"name": name})


def install_force_delete_patch() -> None:
	"""Standard delete unlinks leftovers instead of failing."""
	global _PATCHED
	if _PATCHED:
		return

	import frappe.model.delete_doc as delete_mod

	original = delete_mod.delete_doc

	def patched_delete_doc(doctype=None, name=None, force=0, *args, **kwargs):
		if not doctype or not name or is_protected(doctype, name):
			return original(doctype, name, force, *args, **kwargs)

		depth = cint(frappe.flags.get("force_delete_depth"))
		frappe.flags.force_delete_depth = depth + 1
		try:
			if depth == 0:
				try:
					unlink_blocking_links(doctype, name)
				except Exception:
					frappe.log_error(title=f"Unlink before delete failed {doctype} {name}")
			_cancel_if_submitted(doctype, name)
			flags = frappe._dict(kwargs.get("flags") or {})
			flags.ignore_links = True
			kwargs["flags"] = flags
			if doctype == "Role":
				kwargs["ignore_on_trash"] = True
			try:
				return original(doctype, name, 1, *args, **kwargs)
			except Exception:
				_hard_delete(doctype, name)
		finally:
			frappe.flags.force_delete_depth = depth

	delete_mod.delete_doc = patched_delete_doc
	frappe.delete_doc = patched_delete_doc
	_PATCHED = True


@frappe.whitelist()
def bulk_delete_documents(doctype: str, names=None) -> dict:
	"""Cancel if needed, unlink leftovers, then delete every selected row."""
	install_force_delete_patch()
	if not doctype:
		frappe.throw(frappe._("No doctype"))
	if isinstance(names, str):
		names = frappe.parse_json(names)
	names = [name for name in (names or []) if name]
	if not names:
		return {"removed": [], "errors": [], "count": 0}

	if not frappe.has_permission(doctype, "delete"):
		frappe.throw(frappe._("Not permitted to delete {0}").format(doctype), frappe.PermissionError)

	removed = []
	errors = []
	for name in names:
		if is_protected(doctype, name):
			errors.append({"name": name, "error": "Protected"})
			continue
		try:
			if not frappe.db.exists(doctype, name):
				removed.append(name)
				continue
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
			removed.append(name)
		except Exception as exc:
			if frappe.db.exists(doctype, name):
				try:
					_cancel_if_submitted(doctype, name)
					_hard_delete(doctype, name)
					if not frappe.db.exists(doctype, name):
						removed.append(name)
						continue
				except Exception:
					pass
				errors.append({"name": name, "error": str(exc)})
			else:
				removed.append(name)

	if not frappe.flags.in_test:
		frappe.db.commit()
	return {"removed": removed, "errors": errors, "count": len(removed)}


@frappe.whitelist()
def delete_items(doctype=None, items=None):
	"""Replace Frappe list bulk-delete so submitted invoices and clients can go."""
	doctype = doctype or frappe.form_dict.get("doctype")
	items = items if items is not None else frappe.form_dict.get("items")
	return bulk_delete_documents(doctype, items)


try:
	install_force_delete_patch()
except Exception:
	pass
