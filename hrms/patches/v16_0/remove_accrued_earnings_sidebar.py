"""Remove Accrued Earnings from the SS and Taxes sidebar."""

import frappe

from hrms.hr.bpo_sidebar_labels import apply_bpo_labels
from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars
from hrms.patches.v16_0.apply_bpo_sidebar_labels import _clean_row, _update_child_table

REMOVED_LINKS = frozenset({"Accrued Earnings Report"})
REMOVED_LABELS = frozenset({"Accrued Earnings"})


def _filter_rows(rows: list[dict]) -> list[dict]:
	filtered = [
		row
		for row in rows
		if (row.get("link_to") or "").strip() not in REMOVED_LINKS
		and (row.get("label") or "").strip() not in REMOVED_LABELS
	]
	return apply_bpo_labels(filtered)


def _sync_doc_rows(doctype: str, name: str, fieldname: str):
	if not frappe.db.exists(doctype, name):
		return
	doc = frappe.get_doc(doctype, name)
	if not doc.meta.has_field(fieldname):
		return
	rows = _filter_rows([_clean_row(row) for row in doc.get(fieldname) or []])
	_update_child_table(doc, fieldname, rows)


def execute():
	if frappe.db.table_exists("Sidebar"):
		_sync_doc_rows("Sidebar", "SS and Taxes", "items")

	if frappe.db.table_exists("Workspace Sidebar"):
		_sync_doc_rows("Workspace Sidebar", "SS and Taxes", "items")

	workspace_meta = frappe.get_meta("Workspace")
	if workspace_meta.has_field("sidebar_items") and frappe.db.exists("Workspace", "SS and Taxes"):
		_sync_doc_rows("Workspace", "SS and Taxes", "sidebar_items")

	if frappe.db.table_exists("Sidebar Item"):
		frappe.db.delete("Sidebar Item", {"link_to": ("in", list(REMOVED_LINKS))})
		frappe.db.delete("Sidebar Item", {"label": ("in", list(REMOVED_LABELS))})

	if frappe.db.table_exists("Workspace Sidebar Item"):
		frappe.db.delete("Workspace Sidebar Item", {"link_to": ("in", list(REMOVED_LINKS))})
		frappe.db.delete("Workspace Sidebar Item", {"label": ("in", list(REMOVED_LABELS))})

	try:
		sync_staff_pro_sidebars()
	except Exception:
		frappe.log_error(title="Accrued Earnings sidebar sync")

	frappe.db.commit()
