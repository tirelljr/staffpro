"""Ensure HR Settings overtime defaults are populated on existing sites."""

import frappe


def execute():
	threshold = frappe.db.get_single_value("HR Settings", "overtime_threshold_hours")
	if threshold in (None, "", 0):
		frappe.db.set_single_value("HR Settings", "overtime_threshold_hours", 80)

	multiplier = frappe.db.get_single_value("HR Settings", "overtime_pay_multiplier")
	if multiplier in (None, "", 0):
		frappe.db.set_single_value("HR Settings", "overtime_pay_multiplier", 1.5)
