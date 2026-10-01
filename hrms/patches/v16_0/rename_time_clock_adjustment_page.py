"""Move the Time Clock Adjustment review UI away from the DocType route."""

import frappe

from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars


def execute():
	old_name = "time-clock-adjustment"
	new_name = "time-clock-adjustments"

	old_exists = frappe.db.exists("Page", old_name)
	new_exists = frappe.db.exists("Page", new_name)
	if old_exists and not new_exists:
		frappe.rename_doc("Page", old_name, new_name, force=True)
	elif old_exists and new_exists:
		frappe.delete_doc("Page", old_name, force=True, ignore_permissions=True)

	sync_staff_pro_sidebars()
	frappe.clear_cache()
