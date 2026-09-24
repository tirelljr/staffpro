# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Drop Company, Branch, expense-claim, and unused report links from sidebars."""

import frappe

from hrms.hr.staff_pro_sidebars import (
	REMOVED_SIDEBAR_LABELS,
	REMOVED_SIDEBAR_LINKS,
	filter_removed_sidebar_items,
	sync_staff_pro_sidebars,
)
from hrms.patches.v16_0.apply_bpo_sidebar_labels import _clean_row, _update_child_table


def _sync_doc_rows(doctype: str, name: str, fieldname: str):
	if not frappe.db.exists(doctype, name):
		return
	doc = frappe.get_doc(doctype, name)
	if not doc.meta.has_field(fieldname):
		return
	rows = filter_removed_sidebar_items([_clean_row(row) for row in doc.get(fieldname) or []])
	_update_child_table(doc, fieldname, rows)


def execute():
	for doctype, names, fieldname in (
		("Sidebar", ("People", "Pay", "Finance"), "items"),
		("Workspace Sidebar", ("Workforce", "People", "Pay", "Finance"), "items"),
		("Workspace", ("People", "Workforce", "Pay", "Finance"), "sidebar_items"),
	):
		if not frappe.db.table_exists(doctype):
			continue
		if fieldname == "sidebar_items" and not frappe.get_meta(doctype).has_field(fieldname):
			continue
		for name in names:
			_sync_doc_rows(doctype, name, fieldname)

	if frappe.db.table_exists("Sidebar Item"):
		frappe.db.delete("Sidebar Item", {"link_to": ("in", list(REMOVED_SIDEBAR_LINKS))})
		frappe.db.delete("Sidebar Item", {"label": ("in", list(REMOVED_SIDEBAR_LABELS))})

	if frappe.db.table_exists("Workspace Sidebar Item"):
		frappe.db.delete("Workspace Sidebar Item", {"link_to": ("in", list(REMOVED_SIDEBAR_LINKS))})
		frappe.db.delete("Workspace Sidebar Item", {"label": ("in", list(REMOVED_SIDEBAR_LABELS))})

	sync_staff_pro_sidebars()
	frappe.db.commit()
