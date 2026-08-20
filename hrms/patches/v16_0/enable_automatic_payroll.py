# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Turn on scheduled payroll for sites that never configured the new settings."""

import frappe
from frappe.utils import cint


def execute():
	# Force-sync even if Payroll Settings was customized (newer modified timestamp).
	frappe.reload_doc("payroll", "doctype", "payroll_settings", force=True)

	settings = frappe.get_single("Payroll Settings")
	already_configured = cint(settings.get("automatic_payroll_interval_days")) or settings.get(
		"last_automatic_payroll_run"
	)
	if already_configured and cint(settings.get("enable_automatic_payroll")):
		return

	values = {}
	if not cint(settings.get("automatic_payroll_interval_days")):
		values["automatic_payroll_interval_days"] = 10
	if not settings.get("automatic_payroll_frequency"):
		values["automatic_payroll_frequency"] = "Fortnightly"
	if not already_configured:
		values["enable_automatic_payroll"] = 1
		values["automatic_payroll_submit_slips"] = 1

	if values:
		frappe.db.set_single_value("Payroll Settings", values, update_modified=False)
