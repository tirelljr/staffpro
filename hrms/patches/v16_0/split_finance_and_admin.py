import json
from pathlib import Path

import frappe

from hrms.hr.workspace_sidebar_icons import apply_icons_to_rows

FINANCE_WORKSPACE = "hr/workspace/finance/finance.json"
FINANCE_SIDEBAR = "workspace_sidebar/finance.json"
FINANCE_ICON = "desktop_icon/finance.json"
ADMIN_WORKSPACE = "hr/workspace/admin/admin.json"
ADMIN_SIDEBAR = "workspace_sidebar/admin.json"
ADMIN_ICON = "desktop_icon/admin.json"

ERPNEXT_FINANCE_DOCK = (
	"Invoicing",
	"Payments",
	"Financial Reports",
	"Payables",
	"Receivables",
)


def _clean_row(row) -> dict:
	data = row.as_dict() if hasattr(row, "as_dict") else dict(row)
	for key in (
		"name",
		"idx",
		"parent",
		"parenttype",
		"parentfield",
		"creation",
		"modified",
		"modified_by",
		"owner",
		"docstatus",
	):
		data.pop(key, None)
	return data


def _load_fixture(relative_path: str) -> dict:
	path = Path(frappe.get_app_path("hrms", *relative_path.split("/")))
	return json.loads(path.read_text(encoding="utf-8-sig"))


def _filter_child_rows(parenttype: str, fieldname: str, rows: list[dict]) -> list[dict]:
	df = frappe.get_meta(parenttype).get_field(fieldname)
	allowed = None
	if df and df.options:
		allowed = {field.fieldname for field in frappe.get_meta(df.options).fields}
	cleaned = []
	for row in rows:
		row = _clean_row(row)
		if allowed:
			row = {key: value for key, value in row.items() if key in allowed}
		cleaned.append(row)
	return apply_icons_to_rows(cleaned)


def _import_doc(data: dict, doctype: str):
	data = dict(data)
	for key in ("creation", "modified", "modified_by", "owner", "docstatus"):
		data.pop(key, None)

	if doctype == "Workspace":
		data["sidebar_items"] = _filter_child_rows(
			"Workspace", "sidebar_items", data.get("sidebar_items") or []
		)
	elif doctype == "Workspace Sidebar":
		data["items"] = _filter_child_rows("Workspace Sidebar", "items", data.get("items") or [])

	if frappe.db.exists(doctype, data["name"]):
		doc = frappe.get_doc(doctype, data["name"])
		doc.update(data)
	else:
		doc = frappe.new_doc(doctype)
		doc.update(data)
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.save(ignore_permissions=True)
	return doc


def _rename_if_needed(doctype: str, old_name: str, new_name: str):
	if old_name == new_name:
		return
	if not frappe.db.exists(doctype, old_name):
		return
	if frappe.db.exists(doctype, new_name):
		return
	frappe.rename_doc(doctype, old_name, new_name, force=True)


def _hide_doc(doctype: str, name: str, values: dict):
	if not frappe.db.exists(doctype, name):
		return
	frappe.db.set_value(doctype, name, values, update_modified=False)


def execute():
	"""Split Finance & Admin into Finance (invoicing) and Admin dock workspaces."""
	_rename_if_needed("Workspace", "Finance & Admin", "Finance")
	if frappe.db.table_exists("Workspace Sidebar"):
		_rename_if_needed("Workspace Sidebar", "Finance & Admin", "Finance")
	_rename_if_needed("Desktop Icon", "Finance & Admin", "Finance")

	_import_doc(_load_fixture(FINANCE_WORKSPACE), "Workspace")
	_import_doc(_load_fixture(ADMIN_WORKSPACE), "Workspace")
	_import_doc(_load_fixture(FINANCE_ICON), "Desktop Icon")
	_import_doc(_load_fixture(ADMIN_ICON), "Desktop Icon")

	if frappe.db.table_exists("Workspace Sidebar"):
		_import_doc(_load_fixture(FINANCE_SIDEBAR), "Workspace Sidebar")
		_import_doc(_load_fixture(ADMIN_SIDEBAR), "Workspace Sidebar")

	_hide_doc("Workspace", "Finance & Admin", {"is_hidden": 1, "public": 0})
	_hide_doc("Desktop Icon", "Finance & Admin", {"hidden": 1})
	if (
		frappe.db.table_exists("Workspace Sidebar")
		and frappe.db.exists("Workspace Sidebar", "Finance & Admin")
		and frappe.db.exists("Workspace Sidebar", "Finance")
	):
		frappe.delete_doc("Workspace Sidebar", "Finance & Admin", force=1, ignore_permissions=True)

	for name in ERPNEXT_FINANCE_DOCK:
		_hide_doc("Workspace", name, {"is_hidden": 1, "public": 0})
		_hide_doc("Desktop Icon", name, {"hidden": 1})

	for name, idx in (("Talent", 4), ("Finance", 5), ("Admin", 6)):
		if frappe.db.exists("Desktop Icon", name):
			frappe.db.set_value("Desktop Icon", name, "idx", idx, update_modified=False)

	for name in ("Finance", "Admin"):
		if frappe.db.exists("Workspace", name):
			frappe.db.set_value(
				"Workspace",
				name,
				{"is_hidden": 0, "public": 1},
				update_modified=False,
			)
		if frappe.db.exists("Desktop Icon", name):
			frappe.db.set_value("Desktop Icon", name, "hidden", 0, update_modified=False)
