# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""System-wide defaults for late entry marking (shift + HR Settings)."""

from __future__ import annotations

import frappe
from frappe.utils import cint

DEFAULT_LATE_GRACE_MINUTES = 10


def system_late_entry_defaults() -> tuple[bool, int]:
	"""Org defaults from HR Settings (used when shift is missing or grace is unset)."""
	if not frappe.db.table_exists("tabHR Settings"):
		return True, DEFAULT_LATE_GRACE_MINUTES

	enabled = frappe.db.get_single_value("HR Settings", "enable_late_entry_marking")
	grace = frappe.db.get_single_value("HR Settings", "late_entry_grace_period")
	if enabled in (None, ""):
		enabled = 1
	if not cint(grace):
		grace = DEFAULT_LATE_GRACE_MINUTES
	return bool(cint(enabled)), cint(grace)


def late_entry_grace_for_shift(shift_name: str | None) -> tuple[bool, int]:
	"""Whether late marking applies and grace minutes after shift start."""
	sys_enabled, sys_grace = system_late_entry_defaults()
	if not shift_name or not frappe.db.exists("Shift Type", shift_name):
		return sys_enabled, sys_grace

	enabled, grace = frappe.db.get_value(
		"Shift Type",
		shift_name,
		["enable_late_entry_marking", "late_entry_grace_period"],
	)
	if not cint(enabled):
		return False, 0
	return True, cint(grace) or sys_grace
