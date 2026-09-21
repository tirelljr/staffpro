# Copyright (c) 2026, Staff Pro BPO and Contributors

from hrms.ai.settings import allowed_tool_names, assert_tool_allowed
from hrms.ai.tools.actions import WRITE_TOOLS, execute_write_action
from hrms.ai.tools.adjustments import pending_clock_adjustments
from hrms.ai.tools.attendance import attendance_hours, who_is_in
from hrms.ai.tools.employees import find_employees
from hrms.ai.tools.floors import floor_map
from hrms.ai.tools.navigation import navigate_to_staff_pro
from hrms.ai.tools.overtime import overtime_summary
from hrms.ai.tools.payroll import upcoming_payroll
from hrms.ai.tools.queries import list_agent_queries

READ_TOOLS = [
	find_employees,
	who_is_in,
	attendance_hours,
	overtime_summary,
	list_agent_queries,
	upcoming_payroll,
	pending_clock_adjustments,
	navigate_to_staff_pro,
	floor_map,
]

ALL_TOOLS = [*READ_TOOLS, *WRITE_TOOLS]


def get_enabled_tools():
	allowed = allowed_tool_names()
	write_names = {tool.name for tool in WRITE_TOOLS}
	return [tool for tool in ALL_TOOLS if tool.name in write_names or tool.name in allowed]


def get_enabled_read_tools():
	write_names = {tool.name for tool in WRITE_TOOLS}
	return [tool for tool in get_enabled_tools() if tool.name not in write_names]


__all__ = [
	"ALL_TOOLS",
	"READ_TOOLS",
	"WRITE_TOOLS",
	"assert_tool_allowed",
	"execute_write_action",
	"get_enabled_read_tools",
	"get_enabled_tools",
]
