# Copyright (c) 2026, Staff Pro BPO and Contributors

from __future__ import annotations

from langchain_core.tools import tool

from hrms.ai.tools.common import tool_result

ROUTES = {
	"employees": (["List", "Employee"], "Open Employees"),
	"attendance": (["List", "Attendance"], "Open Attendance"),
	"hours": (["List", "Attendance"], "Open Hours"),
	"who_is_in": (["in-out-today"], "Open Who Is In"),
	"time_clock_adjustments": (["time-clock-adjustments"], "Open Time Clock Adjustments"),
	"paid_time_off": (["paid-time-off"], "Open Paid Time Off"),
	"overtime": (["List", "Overtime Slip"], "Open Overtime Slips"),
	"payroll": (["List", "Payroll Entry"], "Open Payroll"),
	"agent_queries": (["List", "HR Request"], "Open Employee Requests"),
	"floors": (["floor-map"], "Open Floor Map"),
}


@tool
def navigate_to_staff_pro(destination: str) -> str:
	"""Offer a button to open a Staff Pro area. Destinations: employees, attendance, hours, who_is_in, time_clock_adjustments, paid_time_off, overtime, payroll, agent_queries, floors."""
	key = destination.strip().lower().replace(" ", "_")
	route, label = ROUTES.get(key, ROUTES["employees"])
	return tool_result(
		f"Use the button to {label.lower()}.",
		{"destination": key},
		[{"type": "navigate", "label": label, "route": route}],
	)
