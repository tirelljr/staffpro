# Copyright (c) 2026, Staff Pro BPO and Contributors

from __future__ import annotations

from langchain_core.tools import tool

from hrms.ai.tools.common import tool_result
from hrms.hr.page.time_clock_adjustments.time_clock_adjustments import get_adjustments


@tool
def pending_clock_adjustments(
	department: str = "",
	from_date: str = "",
	to_date: str = "",
) -> str:
	"""List pending time clock adjustment requests for HR review."""
	result = get_adjustments(
		status="Pending",
		department=department or None,
		from_date=from_date or None,
		to_date=to_date or None,
	)
	rows = result.get("rows", result.get("adjustments", []))
	columns = [
		{"key": "name", "label": "Request"},
		{"key": "employee_name", "label": "Employee"},
		{"key": "attendance_date", "label": "Date"},
		{"key": "action", "label": "Change"},
	]
	blocks = [
		{"type": "table", "columns": columns, "rows": rows[:25]},
		{
			"type": "navigate",
			"label": "Review Time Clock Adjustments",
			"route": ["time-clock-adjustments"],
		},
	]
	return tool_result(f"There are {len(rows)} pending time clock adjustments.", result, blocks)
