"""Point leftover Attendance DocType links at Day View; the list is no longer a destination."""

import frappe

from hrms.patches.v16_0.apply_bpo_sidebar_labels import execute as reload_sidebars


def execute():
	reload_sidebars()
	if not frappe.db.table_exists("Workspace Link"):
		return
	for name in frappe.get_all(
		"Workspace Link",
		filters={"link_type": "DocType", "link_to": "Attendance"},
		pluck="name",
	):
		frappe.db.set_value(
			"Workspace Link",
			name,
			{"link_type": "Page", "link_to": "day-view", "label": "Day View"},
			update_modified=False,
		)
