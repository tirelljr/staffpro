"""Add Paid Time Off to People and remove PTO Cash-out from Time."""

import frappe

from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars


def execute():
	if frappe.db.table_exists("Sidebar Item"):
		frappe.db.delete("Sidebar Item", {"link_to": "Leave Encashment"})
		frappe.db.delete("Sidebar Item", {"label": "PTO Cash-out"})

	if frappe.db.table_exists("Workspace Sidebar Item"):
		frappe.db.delete("Workspace Sidebar Item", {"link_to": "Leave Encashment"})
		frappe.db.delete("Workspace Sidebar Item", {"label": "PTO Cash-out"})

	try:
		sync_staff_pro_sidebars()
	except Exception:
		frappe.log_error(title="Paid Time Off sidebar sync")
