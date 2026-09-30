# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Keep TD4 Forms on Filesystem only — remove it from People."""

import frappe

from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars

REMOVED_LINKS = frozenset({"TD4 Form"})
REMOVED_LABELS = frozenset({"TD4 Forms", "TD4 Form"})


def _strip_rows(rows) -> list:
	return [
		row
		for row in rows
		if (getattr(row, "link_to", None) or "").strip() not in REMOVED_LINKS
		and (getattr(row, "label", None) or "").strip() not in REMOVED_LABELS
	]


def _strip_sidebar(doctype: str, name: str):
	if not frappe.db.exists(doctype, name):
		return
	doc = frappe.get_doc(doctype, name)
	if not doc.meta.has_field("items"):
		return
	kept = _strip_rows(doc.items or [])
	if len(kept) == len(doc.items or []):
		return
	doc.set("items", [])
	for row in kept:
		doc.append("items", row.as_dict() if hasattr(row, "as_dict") else row)
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.save(ignore_permissions=True)


def execute():
	_strip_sidebar("Sidebar", "People")
	if frappe.db.table_exists("Workspace Sidebar"):
		_strip_sidebar("Workspace Sidebar", "People")
		_strip_sidebar("Workspace Sidebar", "Workforce")
	try:
		sync_staff_pro_sidebars()
	except Exception:
		frappe.log_error(title="TD4 People sidebar sync")
