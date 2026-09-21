# Copyright (c) 2026, Staff Pro BPO and Contributors

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import formatdate
from langchain_core.tools import tool

from hrms.ai.tools.common import parse_name_list, resolve_employees
from hrms.hr.clock_format import parse_work_date

BULK_ACTIONS_TOOL = "bulk_actions"


@tool
def review_time_clock_adjustment(name: str, action: str, comment: str = "") -> str:
	"""Approve or reject a pending time clock adjustment. This always requires user confirmation."""
	return "Confirmation required."


@tool
def add_hours_comment(name: str = "", names: str = "", comment: str = "") -> str:
	"""Add a comment to one or more Attendance records. Pass several IDs in names for one bulk confirmation."""
	return "Confirmation required."


@tool
def add_hours_adjustment(
	attendance_date: str,
	hours: float,
	comment: str,
	employee: str = "",
	employees: str = "",
	direction: str = "Add",
) -> str:
	"""Add or subtract hours for one or many employees on a date. Pass all employee IDs or names in employees as a comma-separated list so the whole batch uses one confirmation."""
	return "Confirmation required."


@tool
def add_hours_entries(
	employees: str,
	attendance_date: str,
	in_time: str,
	out_time: str = "",
	comment: str = "",
	employee: str = "",
) -> str:
	"""Change clock-in and clock-out times for one or many employees on a date. Replaces their punches for that day. Example: employees='Diego Lopez', in_time='10:00 AM', out_time='4:00 PM'."""
	return "Confirmation required."


@tool
def set_clock_times(
	in_time: str,
	out_time: str = "",
	attendance_date: str = "",
	employee: str = "",
	employees: str = "",
	comment: str = "",
) -> str:
	"""Change an employee's clock-in and clock-out for a date. Use this when asked to set, change, or correct punch times (for example 10 AM in and 4 PM out). Pass today as attendance_date if they said today. Replaces existing punches. One confirmation covers the whole group."""
	return "Confirmation required."


@tool
def book_time_off(employee: str, leave_type: str, from_date: str, to_date: str = "") -> str:
	"""Book approved paid time off for an employee. This always requires user confirmation."""
	return "Confirmation required."


@tool
def run_payroll(
	payroll_frequency: str = "Fortnightly",
	start_date: str = "",
	end_date: str = "",
	company: str = "",
	department: str = "",
) -> str:
	"""Create and run a new Payroll Entry for the given frequency and dates. This always requires user confirmation."""
	return "Confirmation required."


@tool
def respond_to_agent_query(name: str, response: str, status: str = "Resolved") -> str:
	"""Reply to an agent HR request/query and optionally set its status. This always requires user confirmation."""
	return "Confirmation required."


@tool
def update_floor_settings(
	action: str,
	office_floor: str = "",
	floor_name: str = "",
	work_site: str = "",
	notes: str = "",
	cubicle: str = "",
	row: str = "",
	seat_number: int = 0,
	employee: str = "",
	device_id: str = "",
	ip_address: str = "",
) -> str:
	"""Create or update a floor, or assign, clear, or add a seat. Actions: create_floor, update_floor, assign_seat, clear_seat, add_seat. assign_seat moves the agent if they already have a seat. This always requires user confirmation."""
	return "Confirmation required."


@tool
def export_information(
	dataset: str,
	file_format: str = "csv",
	from_date: str = "",
	to_date: str = "",
	department: str = "",
	employee: str = "",
	status: str = "",
	company: str = "",
	office_floor: str = "",
	period: str = "monthly",
) -> str:
	"""Export Staff Pro data as PDF, Excel, or CSV. Datasets: employees, attendance, overtime, payroll, agent_queries, floors. This always requires user confirmation."""
	return "Confirmation required."


WRITE_TOOLS = [
	review_time_clock_adjustment,
	add_hours_comment,
	add_hours_adjustment,
	add_hours_entries,
	set_clock_times,
	book_time_off,
	run_payroll,
	respond_to_agent_query,
	update_floor_settings,
	export_information,
]
WRITE_TOOL_NAMES = {item.name for item in WRITE_TOOLS} | {BULK_ACTIONS_TOOL}

ACTION_LABELS = {
	"review_time_clock_adjustment": _("Review time clock adjustment"),
	"add_hours_comment": _("Add hours comment"),
	"add_hours_adjustment": _("Adjust employee hours"),
	"add_hours_entries": _("Set clock-in and clock-out times"),
	"set_clock_times": _("Change clock-in and clock-out times"),
	"book_time_off": _("Book paid time off"),
	"run_payroll": _("Run new payroll"),
	"respond_to_agent_query": _("Respond to agent query"),
	"update_floor_settings": _("Change floor settings"),
	"export_information": _("Export information"),
	BULK_ACTIONS_TOOL: _("Apply bulk changes"),
}


def _preview_arg(key: str, value: Any) -> str | None:
	if value in (None, ""):
		return None
	if key in {"employees", "employee", "names", "name"}:
		items = parse_name_list(value)
		if not items:
			return None
		label = "employees" if key.startswith("employee") else "records"
		if len(items) > 2:
			shown = f"{len(items)} {label}"
		else:
			shown = ", ".join(items)
		return f"{key.replace('_', ' ').title()}: {shown}"
	if key == "attendance_date":
		return f"Attendance Date: {formatdate(parse_work_date(value))}"
	return f"{key.replace('_', ' ').title()}: {value}"


def action_preview(name: str, arguments: dict[str, Any]) -> dict:
	if name not in WRITE_TOOL_NAMES:
		frappe.throw(_("Unsupported Ask AI action."))
	details = ", ".join(part for key, value in arguments.items() if (part := _preview_arg(key, value)))
	return {
		"tool": name,
		"arguments": arguments,
		"title": ACTION_LABELS.get(name) or name.replace("_", " ").title(),
		"description": details,
	}


def bulk_action_preview(steps: list[dict[str, Any]]) -> dict:
	if len(steps) == 1:
		return dict(steps[0])
	lines = [f"{step['title']}: {step['description']}" for step in steps if step.get("description")]
	return {
		"tool": BULK_ACTIONS_TOOL,
		"arguments": {
			"actions": [{"tool": step["tool"], "arguments": step.get("arguments") or {}} for step in steps]
		},
		"title": _("Apply {0} changes").format(len(steps)),
		"description": "\n".join(lines) or _("Apply these changes together."),
	}


def execute_write_action(name: str, arguments: dict[str, Any], conversation: str | None = None):
	if name == BULK_ACTIONS_TOOL:
		return _execute_bulk_actions(arguments.get("actions") or [], conversation=conversation)

	unlocked = False
	try:
		from hrms.ai.settings import unlock_tool_permission

		unlocked = unlock_tool_permission(name)
	except Exception:
		unlocked = False

	if name == "review_time_clock_adjustment":
		from hrms.hr.page.time_clock_adjustments.time_clock_adjustments import review_adjustment

		action = str(arguments.get("action") or "").title()
		if action not in {"Approve", "Reject"}:
			frappe.throw(_("Action must be Approve or Reject."))
		result = review_adjustment(
			name=str(arguments.get("name") or ""),
			action=action,
			comment=str(arguments.get("comment") or ""),
		)

	elif name == "add_hours_comment":
		from hrms.hr.doctype.attendance.attendance import add_hours_comment as add_comment

		names = parse_name_list(arguments.get("names"), arguments.get("name"))
		if not names:
			frappe.throw(_("Attendance is required."))
		for attendance_name in names:
			add_comment(name=attendance_name, comment=str(arguments.get("comment") or ""))
		result = {"updated": len(names)}

	elif name == "add_hours_adjustment":
		from hrms.hr.doctype.attendance.attendance import add_hours_adjustment as adjust_hours

		result = _with_savepoint(
			lambda: adjust_hours(
				employees=resolve_employees(arguments.get("employees"), arguments.get("employee")),
				attendance_date=str(arguments.get("attendance_date") or ""),
				hours=arguments.get("hours"),
				comment=str(arguments.get("comment") or ""),
				direction=str(arguments.get("direction") or "Add"),
			)
		)

	elif name in {"add_hours_entries", "set_clock_times"}:
		from hrms.hr.doctype.attendance.attendance import set_clock_times as change_clocks

		result = _with_savepoint(
			lambda: change_clocks(
				employees=resolve_employees(arguments.get("employees"), arguments.get("employee")),
				attendance_date=str(arguments.get("attendance_date") or "") or None,
				in_time=str(arguments.get("in_time") or ""),
				out_time=str(arguments.get("out_time") or "") or None,
				comment=str(arguments.get("comment") or ""),
			)
		)

	elif name == "book_time_off":
		from hrms.hr.page.paid_time_off.paid_time_off import book_time_off as create_leave

		result = create_leave(
			employee=str(arguments.get("employee") or ""),
			leave_type=str(arguments.get("leave_type") or ""),
			from_date=str(arguments.get("from_date") or ""),
			to_date=str(arguments.get("to_date") or "") or None,
		)

	elif name == "run_payroll":
		from hrms.ai.tools.payroll import execute_run_payroll

		result = execute_run_payroll(arguments)

	elif name == "respond_to_agent_query":
		from hrms.ai.tools.queries import execute_respond_to_agent_query

		result = execute_respond_to_agent_query(arguments)

	elif name == "update_floor_settings":
		from hrms.ai.tools.floors import execute_update_floor_settings

		result = execute_update_floor_settings(arguments)

	elif name == "export_information":
		from hrms.ai.tools.export import execute_export_information

		result = execute_export_information(arguments, conversation=conversation)

	else:
		frappe.throw(_("Unsupported Ask AI action."))

	return _with_toolbox_flag(result, unlocked)


def _execute_bulk_actions(actions: list[dict[str, Any]], conversation: str | None = None):
	if not actions:
		frappe.throw(_("No bulk changes were provided."))
	results = _with_savepoint(lambda: [_execute_bulk_step(step, conversation) for step in actions])
	return {"updated": len(results), "results": results}


def _execute_bulk_step(step: dict[str, Any], conversation: str | None):
	tool = str(step.get("tool") or "")
	if tool == BULK_ACTIONS_TOOL:
		frappe.throw(_("Nested bulk actions are not allowed."))
	return execute_write_action(tool, step.get("arguments") or {}, conversation=conversation)


def _with_savepoint(fn):
	savepoint = f"ai_write_{frappe.generate_hash(length=8)}"
	frappe.db.savepoint(savepoint)
	try:
		return fn()
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def _with_toolbox_flag(result, unlocked: bool):
	if not unlocked:
		return result
	if isinstance(result, dict):
		payload = dict(result)
		payload["toolbox_enabled"] = True
		return payload
	return {"result": result, "toolbox_enabled": True}
