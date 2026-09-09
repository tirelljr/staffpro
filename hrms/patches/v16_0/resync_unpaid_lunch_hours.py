# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Recompute days with a lunch/break punch so working_hours excludes unpaid time."""

import frappe


def execute():
	if not frappe.db.table_exists("Attendance") or not frappe.db.table_exists("Employee Checkin"):
		return

	days = frappe.db.sql(
		"""
		SELECT employee, DATE(`time`) AS attendance_date
		FROM `tabEmployee Checkin`
		WHERE employee IS NOT NULL AND `time` IS NOT NULL
		GROUP BY employee, DATE(`time`)
		HAVING COUNT(*) >= 3
		""",
		as_dict=True,
	)
	if not days:
		return

	from hrms.payroll.daily_pay import allocate_week_deductions, resync_attendance_from_day_logs

	touched = set()
	for row in days:
		if not row.employee or not row.attendance_date:
			continue
		existing = frappe.db.get_value(
			"Attendance",
			{"employee": row.employee, "attendance_date": row.attendance_date, "docstatus": ("<", 2)},
			["name", "status"],
			as_dict=True,
		)
		if not existing or existing.status in ("On Leave", "Absent"):
			continue
		try:
			resync_attendance_from_day_logs(
				row.employee, row.attendance_date, attendance_name=existing.name
			)
		except Exception:
			frappe.log_error(title=f"Unpaid lunch resync failed: {existing.name}")
			continue
		touched.add((row.employee, row.attendance_date))

	for employee, on_date in touched:
		try:
			allocate_week_deductions(employee, on_date)
		except Exception:
			frappe.log_error(title=f"Unpaid lunch pay alloc failed: {employee} {on_date}")
