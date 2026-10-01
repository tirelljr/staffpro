# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Seed Paid Holiday leave and the PTO Payout earning used on work anniversaries."""

import frappe


def execute():
	if not frappe.db.table_exists("Leave Type"):
		return

	from hrms.hr.pto_anniversary import ensure_paid_holiday_leave_type

	ensure_paid_holiday_leave_type()
