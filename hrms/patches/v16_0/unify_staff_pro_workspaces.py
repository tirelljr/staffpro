import frappe

from hrms.boot import hide_unused_erpnext_workspaces

OLD_WORKSPACES = [
	"HR Setup",
	"Tenure",
	"Recruitment",
	"Shift & Attendance",
	"Leaves",
	"Expenses",
	"Performance",
	"Payroll",
	"Tax & Benefits",
]

NEW_WORKSPACES = [
	"Workforce",
	"Time",
	"Pay",
	"SS and Taxes",
	"Talent",
	"Finance",
	"Admin",
]

OLD_DESKTOP_ICONS = OLD_WORKSPACES[:]

NEW_DESKTOP_ICONS = [
	"People",
	"Time",
	"Pay",
	"SS and Taxes",
	"Talent",
	"Finance",
	"Admin",
]


def execute():
	"""Hide legacy 9 HR dock items and unused ERPNext workspaces; keep new unified nav."""
	for name in OLD_WORKSPACES:
		if frappe.db.exists("Workspace", name):
			frappe.db.set_value(
				"Workspace",
				name,
				{"is_hidden": 1, "public": 0},
				update_modified=False,
			)

	for name in OLD_DESKTOP_ICONS:
		if frappe.db.exists("Desktop Icon", name):
			frappe.db.set_value("Desktop Icon", name, "hidden", 1, update_modified=False)

	for name in NEW_WORKSPACES:
		if frappe.db.exists("Workspace", name):
			frappe.db.set_value(
				"Workspace",
				name,
				{"is_hidden": 0, "public": 1},
				update_modified=False,
			)

	for name in NEW_DESKTOP_ICONS:
		if frappe.db.exists("Desktop Icon", name):
			frappe.db.set_value("Desktop Icon", name, "hidden", 0, update_modified=False)

	# Root Staff Pro BPO icon should open the People dashboard, not a workspace page
	from hrms.boot import STAFF_PRO_DESK_HOME

	if frappe.db.exists("Desktop Icon", "Staff Pro BPO"):
		frappe.db.set_value(
			"Desktop Icon",
			"Staff Pro BPO",
			"link",
			f"/{STAFF_PRO_DESK_HOME}",
			update_modified=False,
		)

	hide_unused_erpnext_workspaces()
