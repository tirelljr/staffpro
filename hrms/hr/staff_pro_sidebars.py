"""Ship Staff Pro navigation as Frappe v17 Sidebar + Dock documents.

Older workspace_sidebar/*.json files are no longer imported. Desk now reads
the Sidebar doctype (module folder exports) and the Dock rail for the hrms app.
"""

from __future__ import annotations

import json
from pathlib import Path

import frappe

from hrms.hr.bpo_sidebar_labels import apply_bpo_labels

SIDEBAR_ITEM_FIELDS = (
	"type",
	"label",
	"link_type",
	"link_to",
	"icon",
	"child",
	"indent",
	"collapsible",
	"keep_closed",
	"url",
	"show_arrow",
	"filters",
	"route_options",
	"navigate_to_tab",
	"open_in_new_tab",
)

# Source fixtures still live in the v16 folder. Title is the v17 Sidebar name
# unless it collides with a Module Def (Payroll).
SIDEBAR_SOURCES = (
	{
		"source": "workspace_sidebar/workforce.json",
		"title": "People",
		"module": "HR",
		"header_icon": "user",
		"dock_title": "People",
		"dock_icon": "user",
	},
	{
		"source": "workspace_sidebar/time.json",
		"title": "Time",
		"module": "HR",
		"header_icon": "clock",
		"dock_title": "Time",
		"dock_icon": "clock",
	},
	{
		"source": "workspace_sidebar/pay.json",
		"title": "Pay",
		"module": "HR",
		"header_icon": "wallet",
		"dock_title": "Payroll",
		"dock_icon": "coins",
	},
	{
		"source": "workspace_sidebar/talent.json",
		"title": "Talent",
		"module": "HR",
		"header_icon": "users",
		"dock_title": "Talent",
		"dock_icon": "user-plus",
	},
	{
		"source": "workspace_sidebar/floor.json",
		"title": "Floor",
		"module": "HR",
		"header_icon": "layout-grid",
		"dock_title": "Floor",
		"dock_icon": "layout-grid",
	},
	{
		"source": "workspace_sidebar/ss_and_taxes.json",
		"title": "SS and Taxes",
		"module": "Payroll",
		"header_icon": "shield-check",
		"dock_title": "SS and Taxes",
		"dock_icon": "shield",
	},
	{
		"source": "workspace_sidebar/finance.json",
		"title": "Finance",
		"module": "HR",
		"header_icon": "receipt",
		"dock_title": "Finance",
		"dock_icon": "receipt",
	},
	{
		"source": "workspace_sidebar/admin.json",
		"title": "Admin",
		"module": "HR",
		"header_icon": "settings",
		"dock_title": "Admin",
		"dock_icon": "settings",
	},
)


def _app_path(*parts: str) -> Path:
	return Path(frappe.get_app_path("hrms", *parts))


def _load_json(relative_path: str) -> dict:
	path = _app_path(*relative_path.split("/"))
	return json.loads(path.read_text(encoding="utf-8-sig"))


def _clean_item(row: dict) -> dict:
	item = {key: row.get(key) for key in SIDEBAR_ITEM_FIELDS if row.get(key) not in (None, "")}
	item.setdefault("type", "Link")
	item.setdefault("child", 0)
	item.setdefault("indent", 0)
	item.setdefault("collapsible", 1)
	item.setdefault("keep_closed", 0)
	item.setdefault("show_arrow", 0)
	item.setdefault("open_in_new_tab", 0)
	item["hidden"] = 0
	item["added"] = 0
	item["is_default_module"] = 0
	return item


def sidebar_doc_from_source(spec: dict) -> dict:
	data = _load_json(spec["source"])
	items = apply_bpo_labels([_clean_item(dict(row)) for row in (data.get("items") or [])])
	return {
		"doctype": "Sidebar",
		"name": spec["title"],
		"title": spec["title"],
		"module": spec["module"],
		"app": "hrms",
		"header_icon": spec.get("header_icon") or data.get("header_icon") or "file-text",
		"standard": 1,
		"items": items,
	}


def dock_doc() -> dict:
	return {
		"doctype": "Dock",
		"name": "hrms",
		"app": "hrms",
		"standard": 1,
		"user": "",
		"items": [
			{
				"idx": index + 1,
				"link_type": "Sidebar",
				"link_to": spec["title"],
				"title": spec["dock_title"],
				"icon": spec["dock_icon"],
				"hidden": 0,
				"added": 0,
			}
			for index, spec in enumerate(SIDEBAR_SOURCES)
		],
	}


def _filter_child_rows(doctype: str, fieldname: str, rows: list[dict]) -> list[dict]:
	df = frappe.get_meta(doctype).get_field(fieldname)
	allowed = None
	if df and df.options:
		allowed = {field.fieldname for field in frappe.get_meta(df.options).fields}
	cleaned = []
	for row in rows:
		row = {key: value for key, value in row.items() if key not in {
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
		}}
		if allowed:
			row = {key: value for key, value in row.items() if key in allowed}
		cleaned.append(row)
	return cleaned


def _save_doc(doctype: str, data: dict, rows_field: str):
	payload = dict(data)
	for key in ("creation", "modified", "modified_by", "owner", "docstatus"):
		payload.pop(key, None)
	payload[rows_field] = _filter_child_rows(doctype, rows_field, payload.get(rows_field) or [])

	if frappe.db.exists(doctype, payload["name"]):
		doc = frappe.get_doc(doctype, payload["name"])
		doc.update(payload)
	else:
		doc = frappe.new_doc(doctype)
		doc.update(payload)

	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.flags.in_patch = True
	doc.save(ignore_permissions=True)
	return doc


def sync_staff_pro_sidebars():
	"""Create or refresh Staff Pro Sidebar shells and the hrms dock rail."""
	if frappe.db.table_exists("Sidebar"):
		for spec in SIDEBAR_SOURCES:
			_save_doc("Sidebar", sidebar_doc_from_source(spec), "items")

	if frappe.db.table_exists("Dock"):
		_save_doc("Dock", dock_doc(), "items")

	# Older Workspace Sidebar docs are unused on Frappe v17; keep them if the table still exists.
	try:
		from hrms.patches.v16_0.apply_bpo_sidebar_labels import execute as sync_legacy_sidebars

		if frappe.db.table_exists("Workspace Sidebar"):
			sync_legacy_sidebars()
	except Exception:
		frappe.log_error(title="Staff Pro legacy workspace sidebar sync")


def verify_staff_pro_navigation():
	"""Print the Staff Pro shells and dock so a fresh site can be checked quickly."""
	from frappe.boot import get_module_sidebars
	from frappe.desk.doctype.dock.dock import get_app_entry_set

	shells = get_module_sidebars()
	print("shells", sorted(shells))
	print("dock")
	for row in get_app_entry_set("hrms"):
		print(row.get("title") or row.get("link_to"), row.get("link_to"), row.get("link_type"))
	return {
		"shells": sorted(shells),
		"dock": get_app_entry_set("hrms"),
	}


def after_setup_wizard(user_input: dict | None = None):
	"""Apply Staff Pro branding and navigation after the setup wizard finishes."""
	from hrms.boot import hide_unused_erpnext_workspaces
	from hrms.branding import apply_branding
	from hrms.subscription_utils import update_erpnext_workspaces

	from hrms.hr.doctype.office_floor.office_floor import seed_office_floors
	from hrms.hr.staff_pro_holiday_list import ensure_staff_pro_holiday_list
	from hrms.hr.staff_pro_shift_locations import ensure_staff_pro_shift_locations
	from hrms.payroll.doctype.bonus_type.bonus_type import seed_bonus_types

	apply_branding()
	sync_staff_pro_sidebars()
	ensure_staff_pro_holiday_list()
	ensure_staff_pro_shift_locations()
	seed_office_floors()
	seed_bonus_types()
	hide_unused_erpnext_workspaces()
	update_erpnext_workspaces(disable=True)
