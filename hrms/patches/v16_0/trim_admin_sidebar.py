"""Sync trimmed Admin workspace sidebar (no platform integrations, with App Settings)."""

import frappe

from hrms.patches.v16_0.split_finance_and_admin import _import_doc, _load_fixture

ADMIN_SIDEBAR = "workspace_sidebar/admin.json"


def execute():
	if not frappe.db.table_exists("Workspace Sidebar"):
		return

	_import_doc(_load_fixture(ADMIN_SIDEBAR), "Workspace Sidebar")
