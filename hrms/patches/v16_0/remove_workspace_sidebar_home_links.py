import frappe


# Workspace name -> (dashboard name, extra row fields)
DASHBOARD_FIRST = {
	"HR Setup": ("Human Resource", {}),
	"Shift & Attendance": ("Attendance", {}),
	"Expenses": ("Expense Claims", {}),
	"Recruitment": ("Recruitment", {}),
	"Tenure": ("Employee Lifecycle", {}),
	"Payroll": ("Payroll", {"open_in_new_tab": 1}),
	"Leaves": ("Leaves", {}),
	"Performance": ("Performance", {}),
	# Unified Staff Pro BPO workspaces
	"Workforce": ("Human Resource", {}),
	"Time": ("Attendance", {}),
	"Pay": ("Payroll", {}),
	"Talent": ("Recruitment", {}),
}

HRMS_WORKSPACES = list(DASHBOARD_FIRST) + ["Tax & Benefits", "Finance & Admin"]


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


def _reorder_sidebar_rows(rows: list[dict], workspace_name: str) -> list[dict]:
	rows = [
		row
		for row in rows
		if not (row.get("label") == "Home" and row.get("link_type") == "Workspace")
	]

	if workspace_name not in DASHBOARD_FIRST:
		return rows

	dashboard_name, extras = DASHBOARD_FIRST[workspace_name]
	dashboard_row = next(
		(
			row
			for row in rows
			if row.get("label") == "Dashboard" and row.get("link_type") == "Dashboard"
		),
		None,
	)
	if dashboard_row:
		rows = [row for row in rows if row is not dashboard_row]
		dashboard_row = dict(dashboard_row)
		dashboard_row["link_to"] = dashboard_name
	else:
		dashboard_row = {
			"type": "Link",
			"label": "Dashboard",
			"icon": "layout-dashboard",
			"link_type": "Dashboard",
			"link_to": dashboard_name,
			"child": 0,
			"indent": 0,
			"collapsible": 1,
			"keep_closed": 0,
			"show_arrow": 0,
		}
	dashboard_row.update(extras)
	rows.insert(0, dashboard_row)
	return rows


def _update_child_table(doc, fieldname: str, rows: list[dict]):
	doc.set(fieldname, [])
	for row in rows:
		doc.append(fieldname, row)
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.save(ignore_permissions=True)


def execute():
	"""Remove Home sidebar links. Desk reads Workspace.sidebar_items (source of truth)."""
	# Primary: Workspace.sidebar_items (used by bootinfo / body sidebar)
	for workspace_name in HRMS_WORKSPACES:
		if not frappe.db.exists("Workspace", workspace_name):
			continue
		workspace = frappe.get_doc("Workspace", workspace_name)
		rows = _reorder_sidebar_rows([_clean_row(row) for row in (workspace.sidebar_items or [])], workspace_name)
		_update_child_table(workspace, "sidebar_items", rows)

	# Legacy Workspace Sidebar doctype (kept in sync for older tools)
	if frappe.db.table_exists("Workspace Sidebar"):
		for sidebar_name in frappe.get_all("Workspace Sidebar", filters={"app": "hrms"}, pluck="name"):
			sidebar = frappe.get_doc("Workspace Sidebar", sidebar_name)
			rows = _reorder_sidebar_rows([_clean_row(row) for row in sidebar.items], sidebar_name)
			_update_child_table(sidebar, "items", rows)
