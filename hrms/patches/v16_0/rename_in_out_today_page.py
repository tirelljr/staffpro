"""Keep the Who Is In page title in sync with the dashboard panel."""

import frappe


def execute():
	if frappe.db.exists("Page", "in-out-today"):
		frappe.db.set_value("Page", "in-out-today", "title", "Who Is In", update_modified=False)
