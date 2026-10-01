# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Paste overtime thresholds on demo agents and seed hours that show OT + holiday pay."""

import frappe


def execute():
	try:
		from hrms.import_hr_demo_data import seed_overtime_and_holiday_demo

		seed_overtime_and_holiday_demo()
	except Exception:
		frappe.log_error(title="Overtime and holiday pay demo seed failed")
