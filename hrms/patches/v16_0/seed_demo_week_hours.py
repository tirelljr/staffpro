# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Seed this week's demo punches and backfill SS on existing salary slips."""

import frappe


def execute():
	try:
		from hrms.import_hr_demo_data import seed_week_hours

		seed_week_hours()
	except Exception:
		frappe.log_error(title="Demo week hours seed failed")
