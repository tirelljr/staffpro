"""Remove travel and fleet DocTypes not used in call-center BPO operations."""

import frappe

TRAVEL_FLEET_DOCTYPES = (
	"Travel Request Costing",
	"Travel Itinerary",
	"Travel Request",
	"Purpose of Travel",
	"Vehicle Service Item",
	"Vehicle Service",
	"Vehicle Log",
)

TRAVEL_FLEET_REPORTS = ("Vehicle Expenses",)


def execute():
	for report in TRAVEL_FLEET_REPORTS:
		_delete_doc("Report", report)

	for doctype in TRAVEL_FLEET_DOCTYPES:
		_delete_doc("DocType", doctype)

	strip_missing_travel_fleet_links()


def strip_missing_travel_fleet_links():
	"""Drop workspace, chart, and Expense Claim links to doctypes this patch removed.

	Saving a workspace validates every link. A leftover Vehicle Log link raises
	DoesNotExistError while Desk exports Workspace Home.
	"""
	missing = [
		name
		for name in (*TRAVEL_FLEET_DOCTYPES, *TRAVEL_FLEET_REPORTS, "Vehicle", "Driver")
		if not _target_exists(name)
	]
	if missing:
		number_cards = _names_for("Number Card", missing)
		charts = _names_for("Dashboard Chart", missing)
		_delete_where("Workspace Number Card", {"number_card_name": ("in", number_cards)})
		_delete_where("Workspace Chart", {"chart_name": ("in", charts)})
		for doctype, fieldname in (
			("Workspace Link", "link_to"),
			("Workspace Shortcut", "link_to"),
			("Workspace Sidebar Item", "link_to"),
			("Sidebar Item", "link_to"),
			("Desktop Icon", "link_to"),
			("Number Card", "document_type"),
			("Dashboard Chart", "document_type"),
		):
			_delete_where(doctype, {fieldname: ("in", missing)})

	_delete_where("DocField", {"parent": "Expense Claim", "fieldname": "vehicle_log"})
	_delete_where("Custom Field", {"dt": "Expense Claim", "fieldname": "vehicle_log"})
	_delete_where("Property Setter", {"doc_type": "Expense Claim", "field_name": "vehicle_log"})
	if frappe.db.table_exists("Expense Claim") and frappe.db.has_column("Expense Claim", "vehicle_log"):
		frappe.db.sql_ddl("alter table `tabExpense Claim` drop column `vehicle_log`")
	frappe.clear_cache(doctype="Expense Claim")


def _target_exists(name: str) -> bool:
	return bool(
		frappe.db.exists("DocType", name)
		or frappe.db.exists("Report", name)
		or frappe.db.exists("Page", name)
	)


def _names_for(doctype: str, document_types: list[str]) -> list[str]:
	if not frappe.db.table_exists(doctype) or not frappe.db.has_column(doctype, "document_type"):
		return []
	return frappe.get_all(doctype, filters={"document_type": ("in", document_types)}, pluck="name")


def _delete_where(doctype: str, filters: dict):
	if not frappe.db.table_exists(doctype):
		return
	for fieldname, values in filters.items():
		if not frappe.db.has_column(doctype, fieldname):
			return
		if isinstance(values, tuple) and values and values[0] == "in" and not values[1]:
			return
	frappe.db.delete(doctype, filters)


def _delete_doc(doctype: str, name: str):
	if frappe.db.exists(doctype, name):
		frappe.delete_doc(doctype, name, ignore_missing=True, force=True, ignore_permissions=True)
