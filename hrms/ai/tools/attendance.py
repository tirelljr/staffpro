# Copyright (c) 2026, Staff Pro BPO and Contributors

from __future__ import annotations

from langchain_core.tools import tool

from hrms.ai.tools.common import tool_result
from hrms.hr.clock_format import parse_work_date
from hrms.hr.doctype.attendance.attendance import get_hours_rows
from hrms.hr.page.in_out_today.in_out_today import get_in_out_today


def _who_is_in_status(value: str) -> str:
	wanted = (value or "").strip().lower().replace("_", " ").replace("-", " ")
	if wanted in {"in", "clocked in", "present"}:
		return "in"
	if wanted in {"out", "not in", "not in today", "notin", "absent", "not clocked in", "clocked out"}:
		return "out"
	return "all"


def _compact_who_is_in_row(person: dict) -> dict:
	status = str(person.get("status") or "OUT").strip().upper()
	return {
		"employee": person.get("employee") or "",
		"employee_name": person.get("employee_name") or person.get("employee") or "",
		"department": person.get("department") or "",
		"status": "in" if status == "IN" else "out",
		"in_time": person.get("in_time") or "",
		"out_time": person.get("out_time") or "",
	}


@tool
def who_is_in(department: str = "", attendance_date: str = "", status: str = "") -> str:
	"""Who is clocked in or not in. status: in, out, or all. Use out for people not clocked in that day."""
	result = get_in_out_today(department=department or None, attendance_date=str(parse_work_date(attendance_date)))
	wanted = _who_is_in_status(status)
	rows = []
	for person in result.get("details") or []:
		row = _compact_who_is_in_row(person)
		if wanted in {"in", "out"} and row["status"] != wanted:
			continue
		rows.append(row)
	totals = result.get("totals") or {}
	when = attendance_date or result.get("date") or "today"
	where = f" in {department}" if department else ""
	if wanted == "out":
		summary = f"{len(rows)} employee(s) not in {when}{where}."
	elif wanted == "in":
		summary = f"{len(rows)} employee(s) clocked in {when}{where}."
	else:
		summary = (
			f"{totals.get('in_count', 0)} of {totals.get('total', 0)} employees are in; "
			f"{totals.get('late', 0)} are late."
		)
	data = {
		"attendance_date": result.get("date") or when,
		"status": wanted,
		"counts": totals,
		"employees": [row["employee"] for row in rows if row.get("employee")],
		"rows": rows,
	}
	blocks = []
	summary_rows = result.get("summary") or []
	if wanted == "all" and summary_rows:
		blocks.append(
			{
				"type": "chart",
				"title": f"Attendance by department — {result.get('date')}",
				"chart_type": "bar",
				"labels": [row.get("department") for row in summary_rows],
				"datasets": [
					{"name": "In", "values": [row.get("in_count", 0) for row in summary_rows]},
					{"name": "Out", "values": [row.get("out_count", 0) for row in summary_rows]},
					{"name": "Late", "values": [row.get("late", 0) for row in summary_rows]},
				],
			}
		)
	blocks.append(
		{
			"type": "table",
			"columns": [
				{"key": "employee_name", "label": "Employee"},
				{"key": "department", "label": "Department"},
				{"key": "status", "label": "Status"},
				{"key": "in_time", "label": "Check In"},
				{"key": "out_time", "label": "Check Out"},
			],
			"rows": [
				{
					"employee_name": row["employee_name"],
					"department": row["department"],
					"status": row["status"],
					"in_time": row["in_time"] or "—",
					"out_time": row["out_time"] or "—",
				}
				for row in rows[:80]
			],
		}
	)
	blocks.append(
		{
			"type": "navigate",
			"label": "Open Who Is In",
			"route": ["in-out-today"],
		}
	)
	return tool_result(summary, data, blocks)


@tool
def attendance_hours(
	from_date: str = "",
	to_date: str = "",
	employee: str = "",
	department: str = "",
) -> str:
	"""Get regular, overtime, paid, unpaid, and total attendance hours for a date range."""
	today = str(parse_work_date(None))
	result = get_hours_rows(
		from_date=from_date or today,
		to_date=to_date or today,
		employee=employee or None,
		department=department or None,
	)
	rows = result.get("rows", [])
	columns = [
		{"key": "employee_name", "label": "Employee"},
		{"key": "attendance_date", "label": "Date"},
		{"key": "working_hours", "label": "Hours"},
		{"key": "overtime_hours", "label": "Overtime"},
	]
	blocks = [
		{"type": "table", "columns": columns, "rows": rows[:25]},
		{"type": "navigate", "label": "Open Hours", "route": ["List", "Attendance"]},
	]
	return tool_result(f"Found {len(rows)} attendance hour entries.", result, blocks)
