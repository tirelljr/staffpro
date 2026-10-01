# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Drop Time Off Admin and extra leave setup links. Leave Type stays."""

import frappe

from hrms.hr.staff_pro_sidebars import REMOVED_SIDEBAR_LABELS, REMOVED_SIDEBAR_LINKS, sync_staff_pro_sidebars


def execute():
	labels = list(REMOVED_SIDEBAR_LABELS)
	links = list(REMOVED_SIDEBAR_LINKS)
	for doctype in ("Sidebar Item", "Workspace Sidebar Item"):
		if not frappe.db.table_exists(doctype):
			continue
		frappe.db.delete(doctype, {"label": ("in", labels)})
		frappe.db.delete(doctype, {"link_to": ("in", links)})

	sync_staff_pro_sidebars()
