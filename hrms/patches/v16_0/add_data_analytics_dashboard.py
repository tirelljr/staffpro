"""Move People KPIs and charts onto a Data Analytics dashboard below Agents."""

import json
from pathlib import Path

import frappe

from hrms.patches.v16_0.apply_bpo_sidebar_labels import execute as sync_sidebars


def _load_fixture(relative_path: str) -> dict:
	path = Path(frappe.get_app_path("hrms", *relative_path.split("/")))
	return json.loads(path.read_text(encoding="utf-8"))


def _import_dashboard(relative_path: str):
	data = _load_fixture(relative_path)
	for key in ("creation", "modified", "modified_by", "owner", "docstatus"):
		data.pop(key, None)

	cards = list(data.pop("cards", None) or [])
	charts = list(data.pop("charts", None) or [])

	if frappe.db.exists("Dashboard", data["name"]):
		doc = frappe.get_doc("Dashboard", data["name"])
		doc.update(data)
	else:
		doc = frappe.new_doc("Dashboard")
		doc.update(data)

	doc.set("cards", [])
	for row in cards:
		doc.append("cards", row)

	doc.set("charts", [])
	for row in charts:
		doc.append("charts", row)

	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.save(ignore_permissions=True)


def execute():
	_import_dashboard("hr/hr_dashboard/data_analytics/data_analytics.json")
	_import_dashboard("hr/hr_dashboard/human_resource/human_resource.json")
	sync_sidebars()
