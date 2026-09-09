"""Add Time Clock Adjustment to the Time sidebar under Who Is In."""

import frappe

from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars


def execute():
	try:
		sync_staff_pro_sidebars()
	except Exception:
		frappe.log_error(title="Time Clock Adjustment sidebar sync")
