import frappe

from hrms.hr.workspace_sidebar_icons import apply_icons_to_rows


HRMS_WORKSPACES = [
	"Workforce",
	"Time",
	"Pay",
	"Talent",
	"Finance",
	"Admin",
	"HR Setup",
	"Shift & Attendance",
	"Leaves",
	"Expenses",
	"Recruitment",
	"Tenure",
	"Payroll",
	"Performance",
	"Tax & Benefits",
]


def _clean_row(row) -> dict:
	data = row.as_dict() if hasattr(row, "as_dict") else dict(row)
	for key in (
		"name",
		"idx",
		"parent",
		"parenttype",
		"parentfield",
		"creation",
		"modified",
		"modified_by",
		"owner",
		"docstatus",
	):
		data.pop(key, None)
	return data


def _update_child_table(doc, fieldname: str, rows: list[dict]):
	doc.set(fieldname, [])
	for row in rows:
		doc.append(fieldname, row)
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.save(ignore_permissions=True)


def execute():
	"""Ensure every workspace sidebar row has an appropriate Lucide icon."""
	for workspace_name in HRMS_WORKSPACES:
		if not frappe.db.exists("Workspace", workspace_name):
			continue
		workspace = frappe.get_doc("Workspace", workspace_name)
		rows = apply_icons_to_rows([_clean_row(row) for row in (workspace.sidebar_items or [])])
		_update_child_table(workspace, "sidebar_items", rows)

	if frappe.db.table_exists("Workspace Sidebar"):
		for sidebar_name in frappe.get_all("Workspace Sidebar", filters={"app": "hrms"}, pluck="name"):
			if sidebar_name == "SS and Taxes":
				continue
			sidebar = frappe.get_doc("Workspace Sidebar", sidebar_name)
			rows = apply_icons_to_rows([_clean_row(row) for row in sidebar.items])
			_update_child_table(sidebar, "items", rows)
