# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Vacation is usable after 1 year. Cancel unused grants given before that."""

import frappe


def execute():
	if not frappe.db.table_exists("Employee"):
		return

	_fill_vacation_defaults()

	from hrms.hr.pto_anniversary import (
		cancel_premature_vacation_allocations,
		ensure_paid_holiday_leave_type,
	)

	if frappe.db.table_exists("Leave Type"):
		ensure_paid_holiday_leave_type()
	cancel_premature_vacation_allocations()


def _fill_vacation_defaults():
	defaults = {
		"vacation_accrual_wait_days": 14,
		"vacation_minutes_per_hours_worked": 15,
		"vacation_hours_per_accrual_unit": 8,
		"vacation_max_days": 10,
	}
	if not frappe.db.exists("DocType", "HR Settings"):
		return
	meta = frappe.get_meta("HR Settings")
	settings = frappe.get_single("HR Settings")
	changed = False
	for fieldname, default in defaults.items():
		if not meta.has_field(fieldname):
			continue
		if settings.get(fieldname) in (None, ""):
			settings.set(fieldname, default)
			changed = True
	if changed:
		settings.flags.ignore_permissions = True
		settings.save()
