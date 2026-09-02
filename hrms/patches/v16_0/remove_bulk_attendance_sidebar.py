"""Remove Bulk Attendance from the Time workspace sidebar."""

import frappe

from hrms.hr.bpo_sidebar_labels import apply_bpo_labels
from hrms.patches.v16_0.apply_bpo_sidebar_labels import _clean_row, _update_child_table

REMOVED_LINKS = frozenset({"Employee Attendance Tool"})
REMOVED_LABELS = frozenset({"Bulk Attendance", "Employee Attendance Tool"})


def _filter_rows(rows: list[dict]) -> list[dict]:
	filtered = [
		row
		for row in rows
		if (row.get("link_to") or "").strip() not in REMOVED_LINKS
		and (row.get("label") or "").strip() not in REMOVED_LABELS
	]
	return apply_bpo_labels(filtered)


def _sync_doc_rows(doctype: str, name: str, fieldname: str):
	doc = frappe.get_doc(doctype, name)
	if not doc.meta.has_field(fieldname):
		return
	rows = _filter_rows([_clean_row(row) for row in doc.get(fieldname) or []])
	_update_child_table(doc, fieldname, rows)


def execute():
	if frappe.db.table_exists("Workspace Sidebar"):
		for sidebar_name in frappe.get_all(
			"Workspace Sidebar",
			filters={"app": "hrms", "name": ["in", ["Time", "Shift & Attendance"]]},
			pluck="name",
		):
			_sync_doc_rows("Workspace Sidebar", sidebar_name, "items")

	workspace_meta = frappe.get_meta("Workspace")
	if workspace_meta.has_field("sidebar_items"):
		for workspace_name in ("Time", "Shift & Attendance"):
			if frappe.db.exists("Workspace", workspace_name):
				_sync_doc_rows("Workspace", workspace_name, "sidebar_items")

	if frappe.db.table_exists("Workspace Sidebar Item"):
		frappe.db.delete(
			"Workspace Sidebar Item",
			{
				"link_to": ("in", list(REMOVED_LINKS)),
			},
		)
		frappe.db.delete(
			"Workspace Sidebar Item",
			{
				"label": ("in", list(REMOVED_LABELS)),
			},
		)

	frappe.db.commit()
