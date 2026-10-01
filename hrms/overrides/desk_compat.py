# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Compatibility shims for Frappe desk methods this site's assets still call."""

from __future__ import annotations

import frappe


@frappe.whitelist()
def get_workspace_sidebar_items():
	"""Alias for Frappe builds that renamed this to get_workspaces."""
	from frappe.desk.desktop import get_workspaces

	pages = get_workspaces() or []
	if isinstance(pages, dict):
		return pages
	return {"pages": pages, "has_access": True}


def install_desk_compat() -> None:
	import frappe.desk.desktop as desktop

	if getattr(desktop, "get_workspace_sidebar_items", None):
		return
	desktop.get_workspace_sidebar_items = get_workspace_sidebar_items
