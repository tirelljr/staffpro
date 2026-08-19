import frappe


def execute():
	"""Turn off Frappe/ERPNext module onboarding for every desk portal."""
	_disable_system_setting()
	_clear_workspace_onboarding()
	_clear_sidebar_onboarding()


def _disable_system_setting():
	if not frappe.get_meta("System Settings").has_field("enable_onboarding"):
		return
	frappe.db.set_single_value("System Settings", "enable_onboarding", 0)


def _clear_workspace_onboarding():
	if not frappe.db.table_exists("Workspace"):
		return
	if not frappe.get_meta("Workspace").has_field("onboarding"):
		return
	frappe.db.sql(
		"""
		update `tabWorkspace`
		set onboarding = ''
		where ifnull(onboarding, '') != ''
		"""
	)


def _clear_sidebar_onboarding():
	if not frappe.db.table_exists("Workspace Sidebar"):
		return
	if not frappe.get_meta("Workspace Sidebar").has_field("module_onboarding"):
		return
	frappe.db.sql(
		"""
		update `tabWorkspace Sidebar`
		set module_onboarding = ''
		where ifnull(module_onboarding, '') != ''
		"""
	)
