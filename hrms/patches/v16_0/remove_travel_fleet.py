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
		frappe.delete_doc("Report", report, ignore_missing=True, force=True)

	for doctype in TRAVEL_FLEET_DOCTYPES:
		frappe.delete_doc("DocType", doctype, ignore_missing=True, force=True)
