import json
from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.hr.workspace_sidebar_icons import apply_icons_to_rows
from hrms.setup import get_custom_fields

BPO_AGENT_HOURS_ITEM = "BPO Agent Hours"


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
	doc.flags.ignore_mandatory = True
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


def _ensure_item_group() -> str:
	for name in ("Services", "All Item Groups"):
		if frappe.db.exists("Item Group", name):
			return name
	# Minimal fallback if ERPNext fixtures were never loaded
	doc = frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": "Services",
			"parent_item_group": "All Item Groups",
			"is_group": 0,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_if_duplicate=True)
	return "Services"


def _ensure_uom() -> str:
	if frappe.db.exists("UOM", "Hour"):
		return "Hour"
	if frappe.db.exists("UOM", "Nos"):
		return "Nos"
	doc = frappe.get_doc({"doctype": "UOM", "uom_name": "Hour"})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_if_duplicate=True)
	return "Hour"


def ensure_bpo_agent_hours_item():
	"""Create the non-stock sales item used by Client Invoice."""
	if not frappe.db.exists("DocType", "Item"):
		return None

	item_group = _ensure_item_group()
	uom = _ensure_uom()

	if not frappe.db.exists("Item", BPO_AGENT_HOURS_ITEM):
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": BPO_AGENT_HOURS_ITEM,
				"item_name": BPO_AGENT_HOURS_ITEM,
				"item_group": item_group,
				"stock_uom": uom,
				"is_stock_item": 0,
				"include_item_in_manufacturing": 0,
				"is_sales_item": 1,
				"is_purchase_item": 0,
			}
		)
		item.flags.ignore_permissions = True
		item.insert()

	frappe.db.set_single_value("Payroll Settings", "client_invoice_item", BPO_AGENT_HOURS_ITEM)
	return BPO_AGENT_HOURS_ITEM


def execute():
	# Ensure Employee / Customer billing fields exist on this migrate
	create_custom_fields(get_custom_fields(), ignore_validate=True)

	ensure_bpo_agent_hours_item()

	# Take over any existing Invoicing workspace / icon (ERPNext leftover or prior custom)
	if frappe.db.exists("Workspace", "Invoicing"):
		frappe.delete_doc("Workspace", "Invoicing", force=1, ignore_permissions=True)

	if frappe.db.table_exists("Workspace Sidebar") and frappe.db.exists("Workspace Sidebar", "Invoicing"):
		frappe.delete_doc("Workspace Sidebar", "Invoicing", force=1, ignore_permissions=True)

	_sync_from_fixture("Workspace", "payroll/workspace/invoicing/invoicing.json")
	_sync_from_fixture("Workspace Sidebar", "workspace_sidebar/invoicing.json")
	_import_doc(_load_fixture("desktop_icon/invoicing.json"), "Desktop Icon")

	# Dock order: People(0) Time(1) Pay(2) Invoicing(3) SS and Taxes(4) Talent(5) Finance & Admin(6)
	for name, idx in (
		("Invoicing", 3),
		("SS and Taxes", 4),
		("Talent", 5),
		("Finance & Admin", 6),
	):
		if frappe.db.exists("Desktop Icon", name):
			frappe.db.set_value("Desktop Icon", name, "idx", idx, update_modified=False)

	if frappe.db.exists("Workspace", "Invoicing"):
		frappe.db.set_value(
			"Workspace",
			"Invoicing",
			{"is_hidden": 0, "public": 1},
			update_modified=False,
		)

	if frappe.db.exists("Desktop Icon", "Invoicing"):
		frappe.db.set_value("Desktop Icon", "Invoicing", "hidden", 0, update_modified=False)

	# Migrate's orphan Desktop Icon cleanup can drop Staff Pro fixtures; restore them.
	if not frappe.db.exists("Desktop Icon", "Staff Pro BPO"):
		_import_doc(_load_fixture("desktop_icon/frappe_hr.json"), "Desktop Icon")
	if not frappe.db.exists("Desktop Icon", "Finance & Admin"):
		_import_doc(_load_fixture("desktop_icon/finance_and_admin.json"), "Desktop Icon")

	if frappe.db.exists("Desktop Icon", "Staff Pro BPO"):
		frappe.db.set_value(
			"Desktop Icon",
			"Staff Pro BPO",
			{"hidden": 0, "link": "/desk/workforce"},
			update_modified=False,
		)
