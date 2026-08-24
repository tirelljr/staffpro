# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Seed connected BPO demo data: floor hours, payroll, SS deductions, and client invoices."""

import frappe


def execute():
	try:
		from hrms.import_hr_demo_data import seed_connected_bpo_demo

		seed_connected_bpo_demo()
	except Exception:
		frappe.log_error(title="Connected BPO demo seed failed")
