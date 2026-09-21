# Copyright (c) 2026, Staff Pro BPO and Contributors

from __future__ import annotations

import frappe
from langchain_core.tools import tool

from hrms.ai.tools.common import tool_result
from hrms.hr.clock_format import parse_work_date


@tool
def overtime_summary(
	from_date: str = "",
	to_date: str = "",
	department: str = "",
	employee: str = "",
) -> str:
	"""Summarize submitted and draft overtime slips and overtime duration."""
	frappe.has_permission("Overtime Slip", "read", throw=True)
	filters: dict = {}
	if from_date:
		filters["posting_date"] = [">=", from_date]
	if to_date:
		if "posting_date" in filters:
			filters["posting_date"] = ["between", [from_date, to_date]]
		else:
			filters["posting_date"] = ["<=", to_date]
	if department:
		filters["department"] = department
	if employee:
		filters["employee"] = employee
	rows = frappe.get_list(
		"Overtime Slip",
		fields=[
			"name",
			"posting_date",
			"employee",
			"employee_name",
			"department",
			"total_overtime_duration",
			"docstatus",
		],
		filters=filters,
		order_by="posting_date desc",
		limit_page_length=100,
	)
	total = sum(float(row.total_overtime_duration or 0) for row in rows)
	by_department: dict[str, float] = {}
	for row in rows:
		label = row.department or "No Department"
		by_department[label] = by_department.get(label, 0) + float(row.total_overtime_duration or 0)
	blocks = [
		{
			"type": "chart",
			"title": "Overtime hours by department",
			"chart_type": "bar",
			"labels": list(by_department),
			"datasets": [{"name": "Hours", "values": list(by_department.values())}],
		},
		{
			"type": "table",
			"columns": [
				{"key": "employee_name", "label": "Employee"},
				{"key": "posting_date", "label": "Date"},
				{"key": "department", "label": "Department"},
				{"key": "total_overtime_duration", "label": "Hours"},
			],
			"rows": rows[:25],
		},
		{"type": "navigate", "label": "Open Overtime Slips", "route": ["List", "Overtime Slip"]},
	]
	period = f" from {from_date}" if from_date else f" through {to_date or str(parse_work_date())}"
	return tool_result(f"{len(rows)} overtime slips total {total:.2f} hours{period}.", rows, blocks)
