# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Hide Error Log from the Admin sidebar. BPO users do not need it."""

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
	labels = list(REMOVED_SIDEBAR_LABELS)
	links = list(REMOVED_SIDEBAR_LINKS)
	for doctype in ("Sidebar Item", "Workspace Sidebar Item"):
		if not frappe.db.table_exists(doctype):
			continue
		frappe.db.delete(doctype, {"label": ("in", labels)})
		frappe.db.delete(doctype, {"link_to": ("in", links)})

	if frappe.db.table_exists("Workspace") and frappe.get_meta("Workspace").has_field("sidebar_items"):
		_sync_doc_rows("Workspace", "Admin", "sidebar_items")

	sync_staff_pro_sidebars()
