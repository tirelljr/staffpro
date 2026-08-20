# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Weekly / 2 Weeks / Monthly stay at 0 until an admin sets them in Payroll Days."""

import frappe


def execute():
	frappe.reload_doc("payroll", "doctype", "payroll_settings", force=True)
	frappe.db.set_single_value(
		"Payroll Settings",
		{
			"automatic_payroll_weekly_days": 0,
			"automatic_payroll_fortnightly_days": 0,
			"automatic_payroll_monthly_days": 0,
		},
		update_modified=False,
	)
