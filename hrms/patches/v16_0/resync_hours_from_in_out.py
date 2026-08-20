# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Fill Attendance.working_hours from IN/OUT clocks where it was left at 0."""

import frappe
from frappe.utils import flt


def execute():
	if not frappe.db.table_exists("Attendance"):
		return

	rows = frappe.get_all(
		"Attendance",
		filters={
			"docstatus": ("<", 2),
			"working_hours": 0,
			"status": ("in", ["Present", "Work From Home", "Half Day"]),
		},
		fields=["name", "employee", "attendance_date", "in_time", "out_time", "working_hours"],
	)
	from hrms.payroll.daily_pay import (
		_hours_between,
		allocate_week_deductions,
		resync_attendance_from_day_logs,
	)

	touched = set()
	for row in rows:
		if flt(row.working_hours):
			continue
		if not row.employee or not row.attendance_date:
			continue
		try:
			resync_attendance_from_day_logs(
				row.employee, row.attendance_date, attendance_name=row.name
			)
		except Exception:
			frappe.log_error(title=f"Hours resync failed: {row.name}")
			continue

		hours = flt(frappe.db.get_value("Attendance", row.name, "working_hours"))
		if not hours and row.in_time and row.out_time:
			hours = _hours_between(row.in_time, row.out_time)
			if hours:
				frappe.db.set_value(
					"Attendance", row.name, "working_hours", hours, update_modified=False
				)
		if hours:
			touched.add((row.employee, row.attendance_date))

	for employee, on_date in touched:
		try:
			allocate_week_deductions(employee, on_date)
		except Exception:
			frappe.log_error(title=f"Hours pay alloc failed: {employee} {on_date}")
