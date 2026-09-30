# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Turn on late entry marking site-wide and backfill Shift Types + recent attendance."""

import frappe
from frappe.utils import add_days, cint, getdate, nowdate

from hrms.hr.late_entry import DEFAULT_LATE_GRACE_MINUTES


def execute():
	if frappe.db.exists("DocType", "HR Settings"):
		if frappe.db.get_single_value("HR Settings", "enable_late_entry_marking") in (None, ""):
			frappe.db.set_single_value("HR Settings", "enable_late_entry_marking", 1)
		grace = cint(frappe.db.get_single_value("HR Settings", "late_entry_grace_period"))
		if not grace:
			frappe.db.set_single_value("HR Settings", "late_entry_grace_period", DEFAULT_LATE_GRACE_MINUTES)

	if not frappe.db.table_exists("tabShift Type"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabShift Type`
		SET enable_late_entry_marking = 1
		WHERE IFNULL(enable_late_entry_marking, 0) = 0
		"""
	)
	frappe.db.sql(
		"""
		UPDATE `tabShift Type`
		SET late_entry_grace_period = %s
		WHERE IFNULL(late_entry_grace_period, 0) = 0
		""",
		DEFAULT_LATE_GRACE_MINUTES,
	)

	_resync_recent_attendance_late()


def _resync_recent_attendance_late():
	if not frappe.db.table_exists("tabAttendance"):
		return

	from hrms.payroll.daily_pay import resync_attendance_from_day_logs

	cutoff = add_days(getdate(nowdate()), -90)
	rows = frappe.get_all(
		"Attendance",
		filters={
			"docstatus": ("<", 2),
			"attendance_date": (">=", cutoff),
			"status": ("in", ["Present", "Work From Home", "Half Day"]),
		},
		fields=["name", "employee", "attendance_date"],
		limit=5000,
	)
	for row in rows:
		if not row.employee or not row.attendance_date:
			continue
		try:
			resync_attendance_from_day_logs(row.employee, row.attendance_date, attendance_name=row.name)
		except Exception:
			frappe.log_error(title=f"Late entry resync failed: {row.name}")
