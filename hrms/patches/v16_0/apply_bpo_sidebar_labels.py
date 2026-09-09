import json
from pathlib import Path

import frappe

from hrms.hr.bpo_sidebar_labels import apply_bpo_labels

WORKSPACE_FIXTURES = [
	("Workforce", "hr/workspace/workforce/workforce.json"),
	("Time", "hr/workspace/time/time.json"),
	("Talent", "hr/workspace/talent/talent.json"),
	("Pay", "payroll/workspace/pay/pay.json"),
	("SS and Taxes", "payroll/workspace/ss_and_taxes/ss_and_taxes.json"),
	("Finance", "hr/workspace/finance/finance.json"),
	("Admin", "hr/workspace/admin/admin.json"),
]

SIDEBAR_FIXTURES = {
	"Workforce": "workspace_sidebar/workforce.json",
	"Time": "workspace_sidebar/time.json",
	"Talent": "workspace_sidebar/talent.json",
	"Floor": "workspace_sidebar/floor.json",
	"Pay": "workspace_sidebar/pay.json",
	"SS and Taxes": "workspace_sidebar/ss_and_taxes.json",
	"People": "workspace_sidebar/workforce.json",
	"Finance": "workspace_sidebar/finance.json",
	"Admin": "workspace_sidebar/admin.json",
}


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


def _dedupe_sidebar_rows(rows: list[dict]) -> list[dict]:
	"""Keep one Dashboard link per sidebar. URL + Dashboard rows both resolve to the same page."""
	out = []
	seen_dashboard = False
	for row in rows:
		label = (row.get("label") or "").strip()
		if label == "Dashboard":
			if seen_dashboard:
				continue
			seen_dashboard = True
		out.append(row)
	return out


def _update_child_table(doc, fieldname: str, rows: list[dict]):
	rows = _dedupe_sidebar_rows(rows)
	doctype = doc.doctype
	name = doc.name
	frappe.db.delete(
		"Workspace Sidebar Item",
		{"parent": name, "parenttype": doctype, "parentfield": fieldname},
	)
	doc = frappe.get_doc(doctype, name)
	doc.set(fieldname, [])
	for row in rows:
		doc.append(fieldname, row)
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.save(ignore_permissions=True)


def _load_fixture(relative_path: str) -> dict:
	path = Path(frappe.get_app_path("hrms", *relative_path.split("/")))
	return json.loads(path.read_text(encoding="utf-8-sig"))


def _rows_from_fixture(data: dict, fieldname: str) -> list[dict]:
	return apply_bpo_labels([dict(row) for row in (data.get(fieldname) or [])])


def _import_fixture_doc(doctype: str, fixture_path: str, rows_field: str):
	try:
		data = _load_fixture(fixture_path)
	except FileNotFoundError:
		return None
	for key in ("creation", "modified", "modified_by", "owner", "docstatus"):
		data.pop(key, None)
	if doctype == "Workspace":
		data["standard"] = 1
		data["type"] = "Workspace"
		data["is_hidden"] = 0
		data["public"] = 1
	data[rows_field] = apply_bpo_labels([dict(row) for row in (data.get(rows_field) or [])])
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


def _sync_workspace(name: str, fixture_path: str):
	if not frappe.db.exists("Workspace", name):
		_import_fixture_doc("Workspace", fixture_path, "sidebar_items")
		return
	try:
		rows = _rows_from_fixture(_load_fixture(fixture_path), "sidebar_items")
	except FileNotFoundError:
		workspace = frappe.get_doc("Workspace", name)
		rows = apply_bpo_labels([_clean_row(row) for row in (workspace.sidebar_items or [])])
	if rows:
		_update_child_table(frappe.get_doc("Workspace", name), "sidebar_items", rows)


def _sync_sidebar(name: str, fixture_path: str):
	if not frappe.db.table_exists("Workspace Sidebar"):
		return
	if not frappe.db.exists("Workspace Sidebar", name):
		_import_fixture_doc("Workspace Sidebar", fixture_path, "items")
		return
	try:
		rows = _rows_from_fixture(_load_fixture(fixture_path), "items")
	except FileNotFoundError:
		sidebar = frappe.get_doc("Workspace Sidebar", name)
		rows = apply_bpo_labels([_clean_row(row) for row in sidebar.items])
	if rows:
		_update_child_table(frappe.get_doc("Workspace Sidebar", name), "items", rows)


def _remove_broken_ss_and_taxes_workspace():
	"""Drop a half-imported SS and Taxes workspace so it can be re-imported from fixture."""
	if not frappe.db.exists("Workspace", "SS and Taxes"):
		return
	try:
		doc = frappe.get_doc("Workspace", "SS and Taxes")
		doc.flags.ignore_links = True
		doc.flags.ignore_validate = True
		doc.save(ignore_permissions=True)
	except (frappe.MandatoryError, frappe.LinkValidationError, frappe.ValidationError):
		frappe.delete_doc("Workspace", "SS and Taxes", force=1, ignore_permissions=True)


def execute():
	_remove_broken_ss_and_taxes_workspace()

	for workspace_name, fixture_path in WORKSPACE_FIXTURES:
		_sync_workspace(workspace_name, fixture_path)

	for sidebar_name, fixture_path in SIDEBAR_FIXTURES.items():
		_sync_sidebar(sidebar_name, fixture_path)
