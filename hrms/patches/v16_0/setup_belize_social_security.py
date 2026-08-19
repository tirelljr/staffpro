# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import json
from pathlib import Path

import frappe

from hrms.hr.workspace_sidebar_icons import apply_icons_to_rows
from hrms.payroll.social_security import (
	ensure_employee_ss_fields,
	ensure_ss_salary_components,
	seed_belize_ssb_2022_table,
)

try:
	from hrms.regional.belize.setup import setup as setup_belize_payroll
except ImportError:
	setup_belize_payroll = None


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
		data["sidebar_items"] = apply_icons_to_rows(
			[dict(row) for row in data.get("sidebar_items") or []]
		)
	elif doctype == "Workspace Sidebar":
		data["items"] = apply_icons_to_rows([dict(row) for row in data.get("items") or []])

	_import_doc(data, doctype)


def _create_employee_ss_field():
	ensure_employee_ss_fields()


def execute():
	_create_employee_ss_field()
	ensure_ss_salary_components()
	seed_belize_ssb_2022_table()
	if setup_belize_payroll:
		setup_belize_payroll()

	if frappe.db.exists("Workspace", "SS and Taxes"):
		frappe.delete_doc("Workspace", "SS and Taxes", force=1, ignore_permissions=True)
	if frappe.db.table_exists("Workspace Sidebar") and frappe.db.exists("Workspace Sidebar", "SS and Taxes"):
		frappe.delete_doc("Workspace Sidebar", "SS and Taxes", force=1, ignore_permissions=True)

	_sync_from_fixture("Workspace", "payroll/workspace/ss_and_taxes/ss_and_taxes.json")
	if frappe.db.table_exists("Workspace Sidebar"):
		_sync_from_fixture("Workspace Sidebar", "workspace_sidebar/ss_and_taxes.json")

	if frappe.db.exists("Workspace", "SS and Taxes"):
		frappe.db.set_value(
			"Workspace",
			"SS and Taxes",
			{"is_hidden": 0, "public": 1},
			update_modified=False,
		)
	if frappe.db.exists("Desktop Icon", "SS and Taxes"):
		frappe.db.set_value("Desktop Icon", "SS and Taxes", "hidden", 0, update_modified=False)
