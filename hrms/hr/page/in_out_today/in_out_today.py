# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import defaultdict
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, get_time, getdate


@frappe.whitelist()
def get_in_out_today(department: str | None = None):
	frappe.only_for(["HR Manager", "HR User", "System Manager"])
	today = getdate()
	all_employees = _get_active_employees(today)
	departments = sorted({row.department for row in all_employees if row.department})

	employees = all_employees
	if department:
		employees = [row for row in all_employees if row.department == department]

	details = _build_details(employees, today)
	summary = _build_summary(details)
	totals = _totals_from_rows(details)

	return {
		"date": str(today),
		"departments": departments,
		"totals": totals,
		"summary": summary,
		"details": details,
	}


def _get_active_employees(today):
	employees = frappe.get_list(
		"Employee",
		fields=["name", "employee_name", "department", "default_shift", "date_of_joining", "relieving_date"],
		filters={"status": "Active"},
		order_by="employee_name",
	)
	active = []
	for row in employees:
		if row.date_of_joining and getdate(row.date_of_joining) > today:
			continue
		if row.relieving_date and getdate(row.relieving_date) < today:
			continue
		active.append(row)
	return active


def _build_details(employees, today):
	if not employees:
		return []

	employee_ids = [row.name for row in employees]
	punches_by_employee = _get_todays_punches(employee_ids, today)
	leave_by_employee = _get_todays_leave(employee_ids, today)
	shift_map = _get_shift_map(employees, punches_by_employee)

	details = []
	for employee in employees:
		punches = punches_by_employee.get(employee.name) or []
		latest = punches[-1] if punches else None
		first_in = next((punch for punch in punches if (punch.log_type or "IN") == "IN"), None)
		status = "IN" if latest and (latest.log_type or "IN") != "OUT" else "OUT"
		late = status == "IN" and first_in and _is_late(first_in, employee.default_shift, shift_map)

		punch_dt = get_datetime(latest.time) if latest and latest.time else None
		leave = leave_by_employee.get(employee.name)

		details.append(
			{
				"employee": employee.name,
				"employee_name": employee.employee_name or employee.name,
				"department": employee.department or "",
				"status": status,
				"late": bool(late),
				"date": punch_dt.date().isoformat() if punch_dt else str(today),
				"time": _format_time(punch_dt) if punch_dt else "",
				"pto_code": _pto_code(leave),
				"device_id": (latest.device_id or "") if latest else "",
			}
		)

	details.sort(key=lambda row: (row["employee_name"] or "").lower())
	return details


def _get_todays_punches(employee_ids, today):
	start = get_datetime(today)
	end = get_datetime(add_days(today, 1))
	rows = frappe.get_all(
		"Employee Checkin",
		fields=["employee", "log_type", "time", "device_id", "shift", "shift_start"],
		filters=[
			["employee", "in", employee_ids],
			["time", ">=", start],
			["time", "<", end],
		],
		order_by="time asc",
	)
	by_employee = defaultdict(list)
	for row in rows:
		by_employee[row.employee].append(row)
	return by_employee


def _get_todays_leave(employee_ids, today):
	rows = frappe.get_all(
		"Leave Application",
		fields=["employee", "leave_type", "description"],
		filters=[
			["employee", "in", employee_ids],
			["status", "=", "Approved"],
			["docstatus", "=", 1],
			["from_date", "<=", today],
			["to_date", ">=", today],
		],
		order_by="modified desc",
	)
	by_employee = {}
	for row in rows:
		by_employee.setdefault(row.employee, row)
	return by_employee


def _get_shift_map(employees, punches_by_employee):
	names = {row.default_shift for row in employees if row.default_shift}
	for punches in punches_by_employee.values():
		for punch in punches:
			if punch.shift:
				names.add(punch.shift)
	if not names:
		return {}
	rows = frappe.get_all(
		"Shift Type",
		fields=["name", "start_time", "enable_late_entry_marking", "late_entry_grace_period"],
		filters={"name": ["in", list(names)]},
	)
	return {row.name: row for row in rows}


def _is_late(first_in, default_shift, shift_map):
	shift_name = first_in.shift or default_shift
	shift = shift_map.get(shift_name)
	if not first_in or not shift or not cint(shift.enable_late_entry_marking):
		return False

	baseline = get_datetime(first_in.shift_start) if first_in.shift_start else None
	if not baseline and shift.start_time is not None:
		baseline = datetime.combine(getdate(first_in.time), get_time(shift.start_time))
	if not baseline:
		return False

	grace = timedelta(minutes=cint(shift.late_entry_grace_period))
	return get_datetime(first_in.time) > baseline + grace


def _pto_code(leave):
	if not leave:
		return ""
	leave_type = (leave.leave_type or "").strip()
	description = (leave.description or "").strip()
	if leave_type and description:
		return f"{leave_type} {description}"
	return leave_type or description


def _format_time(value):
	return get_datetime(value).strftime("%I:%M %p")


def _build_summary(details):
	grouped = defaultdict(lambda: {"employees": 0, "in_count": 0, "out_count": 0, "late": 0})
	for row in details:
		bucket = grouped[row["department"] or _("No Department")]
		bucket["employees"] += 1
		if row["status"] == "IN":
			bucket["in_count"] += 1
		else:
			bucket["out_count"] += 1
		if row["late"]:
			bucket["late"] += 1

	summary = [
		{
			"department": department,
			"employees": counts["employees"],
			"in_count": counts["in_count"],
			"out_count": counts["out_count"],
			"late": counts["late"],
		}
		for department, counts in grouped.items()
	]
	summary.sort(key=lambda row: (row["department"] or "").lower())
	return summary


def _totals_from_rows(rows):
	return {
		"total": len(rows),
		"in_count": sum(1 for row in rows if row["status"] == "IN"),
		"out_count": sum(1 for row in rows if row["status"] == "OUT"),
		"late": sum(1 for row in rows if row["late"]),
	}
