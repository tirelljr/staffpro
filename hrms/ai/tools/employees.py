# Copyright (c) 2026, Staff Pro BPO and Contributors

from __future__ import annotations

import frappe
from langchain_core.tools import tool

from hrms.ai.tools.common import tool_result


@tool
def find_employees(query: str = "", department: str = "", status: str = "Active", limit: int = 20) -> str:
	"""Find employees by name, employee ID, department, or designation."""
	frappe.has_permission("Employee", "read", throw=True)
	filters: dict = {}
	if department:
		filters["department"] = department
	if status:
		filters["status"] = status
	or_filters = None
	if query:
		term = f"%{query.strip()}%"
		or_filters = {
			"employee_name": ["like", term],
			"name": ["like", term],
			"designation": ["like", term],
		}
	rows = frappe.get_list(
		"Employee",
		fields=["name", "employee_name", "department", "designation", "status"],
		filters=filters,
		or_filters=or_filters,
		order_by="employee_name asc",
		limit_page_length=max(1, min(limit, 50)),
	)
	block = {
		"type": "table",
		"columns": [
			{"key": "employee_name", "label": "Employee"},
			{"key": "department", "label": "Department"},
			{"key": "designation", "label": "Designation"},
			{"key": "status", "label": "Status"},
		],
		"rows": rows,
	}
	return tool_result(f"Found {len(rows)} employees.", rows, [block] if rows else [])
