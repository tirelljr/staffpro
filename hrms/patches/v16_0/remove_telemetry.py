"""Remove telemetry DocType after stripping usage analytics."""

import frappe


def execute():
	frappe.delete_doc("DocType", "HR Telemetry Milestone", ignore_missing=True, force=True)
