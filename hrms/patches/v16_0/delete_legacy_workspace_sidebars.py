"""Delete legacy HR workspace sidebars superseded by unified BPO navigation."""

import frappe

LEGACY_SIDEBARS = (
	"Tenure",
	"Tax & Benefits",
	"Shift & Attendance",
	"Recruitment",
	"Performance",
	"Payroll",
	"Leaves",
	"Invoicing",
	"HR Setup",
	"Finance & Admin",
	"Expenses",
)


def execute():
	if not frappe.db.table_exists("Workspace Sidebar"):
		return

	for name in LEGACY_SIDEBARS:
		if frappe.db.exists("Workspace Sidebar", name):
			frappe.delete_doc("Workspace Sidebar", name, force=1, ignore_permissions=True)
