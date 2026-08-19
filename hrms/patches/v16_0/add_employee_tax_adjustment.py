# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import json
from pathlib import Path

import frappe

from hrms.hr.workspace_sidebar_icons import apply_icons_to_rows


def _load_fixture(relative_path: str) -> dict:
	path = Path(frappe.get_app_path("hrms", *relative_path.split("/")))
	return json.loads(path.read_text(encoding="utf-8"))


def _import_doc(data: dict, doctype: str):
	data = dict(data)
	for key in ("creation", "modified", "modified_by", "owner", "docstatus"):
		data.pop(key, None)

	if frappe.db.exists(doctype, data["name"]):
		doc = frappe.get_doc(doctype, data["name"])
		doc.update(data)
	else:
		doc = frappe.new_doc(doctype)
		doc.update(data)
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.save(ignore_permissions=True)


def execute():
	workspace = _load_fixture("payroll/workspace/ss_and_taxes/ss_and_taxes.json")
	workspace["sidebar_items"] = apply_icons_to_rows(
		[dict(row) for row in workspace.get("sidebar_items") or []]
	)
	if frappe.db.exists("Workspace", "SS and Taxes"):
		frappe.delete_doc("Workspace", "SS and Taxes", force=1, ignore_permissions=True)
	_import_doc(workspace, "Workspace")

	if frappe.db.table_exists("Workspace Sidebar"):
		sidebar = _load_fixture("workspace_sidebar/ss_and_taxes.json")
		sidebar["items"] = apply_icons_to_rows([dict(row) for row in sidebar.get("items") or []])
		if frappe.db.exists("Workspace Sidebar", "SS and Taxes"):
			frappe.delete_doc("Workspace Sidebar", "SS and Taxes", force=1, ignore_permissions=True)
		_import_doc(sidebar, "Workspace Sidebar")
