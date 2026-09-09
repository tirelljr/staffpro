"""Add the Floor dock module, seed office floors, and sync navigation."""

import json
from pathlib import Path

import frappe

from hrms.hr.doctype.office_floor.office_floor import seed_office_floors
from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars


def _load_fixture(relative_path: str) -> dict:
	path = Path(frappe.get_app_path("hrms", *relative_path.split("/")))
	return json.loads(path.read_text(encoding="utf-8-sig"))


def _import_desktop_icon(data: dict):
	data = dict(data)
	for key in ("creation", "modified", "modified_by", "owner", "docstatus"):
		data.pop(key, None)

	if frappe.db.exists("Desktop Icon", data["name"]):
		doc = frappe.get_doc("Desktop Icon", data["name"])
		doc.update(data)
	else:
		doc = frappe.new_doc("Desktop Icon")
		doc.update(data)
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.save(ignore_permissions=True)


def execute():
	if frappe.db.table_exists("Office Floor"):
		seed_office_floors()

	if frappe.db.exists("DocType", "Desktop Icon"):
		_import_desktop_icon(_load_fixture("desktop_icon/floor.json"))
		for name, idx in (("Finance", 6), ("Admin", 7)):
			if frappe.db.exists("Desktop Icon", name):
				frappe.db.set_value("Desktop Icon", name, "idx", idx, update_modified=False)

	try:
		sync_staff_pro_sidebars()
	except Exception:
		frappe.log_error(title="Floor sidebar sync")
