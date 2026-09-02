"""Hide ERPNext workspaces/sidebars so Desk stays call-center BPO focused."""

import frappe

STANDARD_ROLES = frozenset(
	{
		"Administrator",
		"All",
		"Guest",
		"Accounts Manager",
		"Accounts User",
		"Projects User",
		"Projects Manager",
		"Blogger",
		"Dashboard Manager",
		"Inbox User",
		"Newsletter Manager",
		"Prepared Report User",
		"Report Manager",
		"Script Manager",
		"System Manager",
		"Website Manager",
		"Workspace Manager",
	}
)


def update_erpnext_workspaces(disable: bool = True):
	"""Hide ERPNext (and leftover HR) workspaces/sidebars so Desk stays call-center BPO focused."""
	erpnext_workspaces = [
		"Home",
		"Assets",
		"Asset",
		"Accounting",
		"Accounts",
		"Buying",
		"CRM",
		"Manufacturing",
		"Quality",
		"Selling",
		"Stock",
		"Support",
		"Invoicing",
		"Payments",
		"Financial Reports",
		"Payables",
		"Receivables",
		"Project",
		"Projects",
		"Website",
		# Legacy HR workspaces replaced by Workforce / Time / Pay / Talent
		"Expense Claims",
		"Employee Lifecycle",
		"Performance",
		"Leaves",
		"Recruitment",
		"Payroll",
		"HR Setup",
		"Tenure",
		"Shift & Attendance",
		"Expenses",
		"Tax & Benefits",
	]

	for workspace in erpnext_workspaces:
		_set_workspace_visibility(workspace, hidden=disable)
		_set_workspace_sidebar_visibility(workspace, hidden=disable)
		_set_desktop_icon_hidden(workspace, hidden=disable)

	for icon in ("Stock", "Buying", "Selling", "CRM", "Accounts", "Assets", "Manufacturing", "Project", "Projects"):
		_set_desktop_icon_hidden(icon, hidden=disable)


def _set_workspace_visibility(name: str, hidden: bool = True):
	if not frappe.db.exists("Workspace", name):
		return
	try:
		workspace_doc = frappe.get_doc("Workspace", name)
		workspace_doc.flags.ignore_links = True
		workspace_doc.flags.ignore_validate = True
		workspace_doc.public = 0 if hidden else 1
		if workspace_doc.meta.has_field("is_hidden"):
			workspace_doc.is_hidden = 1 if hidden else 0
		workspace_doc.save()
	except Exception:
		frappe.clear_messages()


def _set_workspace_sidebar_visibility(name: str, hidden: bool = True):
	if not frappe.db.table_exists("Workspace Sidebar"):
		return
	if not frappe.db.exists("Workspace Sidebar", name):
		return
	try:
		values = {}
		meta = frappe.get_meta("Workspace Sidebar")
		if meta.has_field("public"):
			values["public"] = 0 if hidden else 1
		if meta.has_field("is_hidden"):
			values["is_hidden"] = 1 if hidden else 0
		if values:
			frappe.db.set_value("Workspace Sidebar", name, values, update_modified=False)
	except Exception:
		frappe.clear_messages()


def _set_desktop_icon_hidden(name: str, hidden: bool = True):
	if not frappe.db.exists("Desktop Icon", name):
		return
	try:
		frappe.db.set_value("Desktop Icon", name, "hidden", 1 if hidden else 0, update_modified=False)
	except Exception:
		frappe.clear_messages()
