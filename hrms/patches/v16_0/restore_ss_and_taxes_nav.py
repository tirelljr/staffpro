# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Put SS and Taxes back on the dock after migrate skipped the non-standard fixture."""

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
	return doc


def _sync_from_fixture(doctype: str, fixture_path: str):
	data = _load_fixture(fixture_path)
	for key in ("creation", "modified", "modified_by", "owner", "docstatus"):
		data.pop(key, None)

	if doctype == "Workspace":
		data["standard"] = 1
		data["type"] = "Workspace"
		data["is_hidden"] = 0
		data["public"] = 1
		data["sidebar_items"] = apply_icons_to_rows(
			[dict(row) for row in data.get("sidebar_items") or []]
		)
	elif doctype == "Workspace Sidebar":
		data["standard"] = 1
		data["items"] = apply_icons_to_rows([dict(row) for row in data.get("items") or []])

	_import_doc(data, doctype)


def execute():
	if frappe.db.exists("Workspace", "SS and Taxes"):
		frappe.delete_doc("Workspace", "SS and Taxes", force=1, ignore_permissions=True)
	if frappe.db.table_exists("Workspace Sidebar") and frappe.db.exists("Workspace Sidebar", "SS and Taxes"):
		frappe.delete_doc("Workspace Sidebar", "SS and Taxes", force=1, ignore_permissions=True)

	_sync_from_fixture("Workspace", "payroll/workspace/ss_and_taxes/ss_and_taxes.json")
	if frappe.db.table_exists("Workspace Sidebar"):
		_sync_from_fixture("Workspace Sidebar", "workspace_sidebar/ss_and_taxes.json")
	if frappe.db.table_exists("Desktop Icon"):
		_import_doc(_load_fixture("desktop_icon/ss_and_taxes.json"), "Desktop Icon")

	if frappe.db.exists("Workspace", "SS and Taxes"):
		values = {"is_hidden": 0, "public": 1, "sequence_id": 3.5}
		meta = frappe.get_meta("Workspace")
		if meta.has_field("standard"):
			values["standard"] = 1
		if meta.has_field("type"):
			values["type"] = "Workspace"
		frappe.db.set_value("Workspace", "SS and Taxes", values, update_modified=False)

	if frappe.db.table_exists("Desktop Icon") and frappe.db.exists("Desktop Icon", "SS and Taxes"):
		frappe.db.set_value(
			"Desktop Icon",
			"SS and Taxes",
			{"hidden": 0, "idx": 3},
			update_modified=False,
		)

	for name, idx in (("People", 0), ("Time", 1), ("Pay", 2), ("Talent", 4), ("Finance", 5), ("Admin", 6)):
		if frappe.db.table_exists("Desktop Icon") and frappe.db.exists("Desktop Icon", name):
			frappe.db.set_value("Desktop Icon", name, "idx", idx, update_modified=False)
