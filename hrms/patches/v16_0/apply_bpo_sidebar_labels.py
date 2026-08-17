import json
from pathlib import Path

import frappe

from hrms.hr.bpo_sidebar_labels import apply_bpo_labels

WORKSPACE_FIXTURES = [
	("Workforce", "hr/workspace/workforce/workforce.json"),
	("People", "hr/workspace/people/people.json"),
	("Time", "hr/workspace/time/time.json"),
	("Talent", "hr/workspace/talent/talent.json"),
	("Pay", "payroll/workspace/pay/pay.json"),
	("Finance & Admin", "hr/workspace/finance_and_admin/finance_and_admin.json"),
]

SIDEBAR_FIXTURES = {
	"Workforce": "workspace_sidebar/workforce.json",
	"Time": "workspace_sidebar/time.json",
	"Talent": "workspace_sidebar/talent.json",
	"Pay": "workspace_sidebar/pay.json",
	"People": "workspace_sidebar/workforce.json",
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


def _update_child_table(doc, fieldname: str, rows: list[dict]):
	doc.set(fieldname, [])
	for row in rows:
		doc.append(fieldname, row)
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.save(ignore_permissions=True)


def _load_fixture(relative_path: str) -> dict:
	path = Path(frappe.get_app_path("hrms", *relative_path.split("/")))
	return json.loads(path.read_text(encoding="utf-8"))


def _rows_from_fixture(data: dict, fieldname: str) -> list[dict]:
	return apply_bpo_labels([dict(row) for row in (data.get(fieldname) or [])])


def _sync_workspace(name: str, fixture_path: str):
	if not frappe.db.exists("Workspace", name):
		return
	try:
		rows = _rows_from_fixture(_load_fixture(fixture_path), "sidebar_items")
	except FileNotFoundError:
		workspace = frappe.get_doc("Workspace", name)
		rows = apply_bpo_labels([_clean_row(row) for row in (workspace.sidebar_items or [])])
	if rows:
		_update_child_table(frappe.get_doc("Workspace", name), "sidebar_items", rows)


def _sync_sidebar(name: str, fixture_path: str):
	if not frappe.db.table_exists("Workspace Sidebar") or not frappe.db.exists("Workspace Sidebar", name):
		return
	try:
		rows = _rows_from_fixture(_load_fixture(fixture_path), "items")
	except FileNotFoundError:
		sidebar = frappe.get_doc("Workspace Sidebar", name)
		rows = apply_bpo_labels([_clean_row(row) for row in sidebar.items])
	if rows:
		_update_child_table(frappe.get_doc("Workspace Sidebar", name), "items", rows)


def _remove_broken_ss_and_taxes_workspace():
	"""Drop a half-imported SS and Taxes workspace so other patches can save workspaces."""
	if not frappe.db.exists("Workspace", "SS and Taxes"):
		return
	try:
		frappe.get_doc("Workspace", "SS and Taxes").save(ignore_permissions=True)
	except frappe.MandatoryError:
		frappe.delete_doc("Workspace", "SS and Taxes", force=1, ignore_permissions=True)


def execute():
	_remove_broken_ss_and_taxes_workspace()

	for workspace_name, fixture_path in WORKSPACE_FIXTURES:
		_sync_workspace(workspace_name, fixture_path)

	for sidebar_name, fixture_path in SIDEBAR_FIXTURES.items():
		_sync_sidebar(sidebar_name, fixture_path)
