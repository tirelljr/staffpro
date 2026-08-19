import json
from pathlib import Path

import frappe

from hrms.hr.workspace_sidebar_icons import apply_icons_to_rows

PAY_TAX_LINKS = {
	"Employee Tax Exemption Declaration",
	"Employee Tax Exemption Proof Submission",
	"Employee Benefit Application",
	"Employee Benefit Claim",
	"Income Tax Computation",
	"Income Tax Deductions",
	"Professional Tax Deductions",
	"Income Tax Slab",
	"Employee Tax Exemption Category",
	"Employee Tax Exemption Sub Category",
}

PAY_TAX_SECTIONS = {"Tax & Benefits"}


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


def _strip_pay_tax_items(rows: list[dict]) -> list[dict]:
	cleaned = []
	skip_children = False
	for row in rows:
		label = (row.get("label") or "").strip()
		link_to = (row.get("link_to") or "").strip()
		row_type = row.get("type")

		if row_type == "Section Break" and label in PAY_TAX_SECTIONS:
			skip_children = True
			continue

		if row_type == "Section Break":
			skip_children = False

		if skip_children:
			continue

		if link_to in PAY_TAX_LINKS:
			continue

		cleaned.append(row)

	return cleaned


def _sync_from_fixture(doctype: str, fixture_path: str, fieldname: str | None = None):
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


def execute():
	if frappe.db.exists("Workspace", "SS and Taxes"):
		frappe.delete_doc("Workspace", "SS and Taxes", force=1, ignore_permissions=True)

	if frappe.db.table_exists("Workspace Sidebar") and frappe.db.exists("Workspace Sidebar", "SS and Taxes"):
		frappe.delete_doc("Workspace Sidebar", "SS and Taxes", force=1, ignore_permissions=True)

	_sync_from_fixture("Workspace", "payroll/workspace/ss_and_taxes/ss_and_taxes.json")
	_sync_from_fixture("Workspace Sidebar", "workspace_sidebar/ss_and_taxes.json")
	_import_doc(_load_fixture("desktop_icon/ss_and_taxes.json"), "Desktop Icon")

	for name, idx in (("Talent", 4), ("Finance", 5), ("Admin", 6)):
		if frappe.db.exists("Desktop Icon", name):
			frappe.db.set_value("Desktop Icon", name, "idx", idx, update_modified=False)

	if frappe.db.exists("Desktop Icon", "Tax & Benefits"):
		frappe.db.set_value("Desktop Icon", "Tax & Benefits", "hidden", 1, update_modified=False)

	if frappe.db.exists("Workspace", "Pay"):
		pay = frappe.get_doc("Workspace", "Pay")
		rows = apply_icons_to_rows(
			_strip_pay_tax_items([_clean_row(row) for row in (pay.sidebar_items or [])])
		)
		_update_child_table(pay, "sidebar_items", rows)

	if frappe.db.table_exists("Workspace Sidebar") and frappe.db.exists("Workspace Sidebar", "Pay"):
		pay_sidebar = frappe.get_doc("Workspace Sidebar", "Pay")
		rows = apply_icons_to_rows(
			_strip_pay_tax_items([_clean_row(row) for row in pay_sidebar.items])
		)
		_update_child_table(pay_sidebar, "items", rows)

	if frappe.db.exists("Workspace", "SS and Taxes"):
		frappe.db.set_value(
			"Workspace",
			"SS and Taxes",
			{"is_hidden": 0, "public": 1},
			update_modified=False,
		)

	if frappe.db.exists("Desktop Icon", "SS and Taxes"):
		frappe.db.set_value("Desktop Icon", "SS and Taxes", "hidden", 0, update_modified=False)
