# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe
from frappe import _

AI_ROLES = frozenset({"HR User", "HR Manager", "HR Assistant", "System Manager", "Administrator"})

PERMISSION_DENIED = "Permission not granted by admin."

# Ask AI can do only what the signed-in user can do. Flags are the role
# switches an admin sets. DocType permissions are the same checks the screens use.
TOOL_USER_ACCESS = {
	"find_employees": {
		"any_flags": ("see_agents", "see_floor_workers"),
		"perms": (("Employee", "read"),),
	},
	"who_is_in": {"flags": ("see_attendance",), "perms": (("Attendance", "read"),)},
	"attendance_hours": {"flags": ("see_attendance",), "perms": (("Attendance", "read"),)},
	"overtime_summary": {"flags": ("see_overtime",), "perms": (("Overtime Slip", "read"),)},
	"list_agent_queries": {"flags": ("see_employee_requests",), "perms": (("HR Request", "read"),)},
	"upcoming_payroll": {"flags": ("see_agent_salary",), "perms": (("Salary Slip", "read"),)},
	"pending_clock_adjustments": {
		"flags": ("see_time_clock",),
		"perms": (("Time Clock Adjustment", "read"),),
	},
	"floor_map": {"flags": ("see_floor",), "perms": (("Office Floor", "read"),)},
	"show_documents": {"check": "documents"},
	"review_time_clock_adjustment": {
		"flags": ("see_time_clock",),
		"perms": (("Time Clock Adjustment", "write"),),
	},
	"add_hours_comment": {"flags": ("see_attendance",), "perms": (("Attendance", "write"),)},
	"add_hours_adjustment": {"flags": ("see_attendance",), "perms": (("Attendance", "write"),)},
	"add_hours_entries": {
		"flags": ("see_attendance",),
		"perms": (("Attendance", "write"), ("Employee Checkin", "create")),
	},
	"set_clock_times": {
		"flags": ("see_attendance",),
		"perms": (("Attendance", "write"), ("Employee Checkin", "create")),
	},
	"book_time_off": {
		"any_flags": ("see_paid_time_off", "see_time_off"),
		"perms": (("Leave Application", "create"), ("Leave Allocation", "create")),
	},
	"run_payroll": {"flags": ("see_agent_salary",), "perms": (("Payroll Entry", "create"),)},
	"respond_to_agent_query": {"flags": ("see_employee_requests",), "perms": (("HR Request", "write"),)},
	"update_floor_settings": {
		"flags": ("see_floor",),
		"any_perms": (("Office Floor", "write"), ("Cubicle", "write")),
	},
	"edit_job_letter": {"check": "job_letter"},
	"review_job_letter": {"check": "job_letter"},
	"export_information": {"check": "export"},
	"navigate_to_staff_pro": {"check": "navigate"},
}

CAPABILITIES = (
	("view employees", ("find_employees",)),
	("view attendance", ("who_is_in", "attendance_hours")),
	("edit hours", ("add_hours_comment", "add_hours_adjustment")),
	("change clock times", ("add_hours_entries", "set_clock_times")),
	("view overtime", ("overtime_summary",)),
	("view payroll", ("upcoming_payroll",)),
	("run payroll", ("run_payroll",)),
	("view time clock adjustments", ("pending_clock_adjustments",)),
	("review time clock adjustments", ("review_time_clock_adjustment",)),
	("book time off", ("book_time_off",)),
	("view employee requests", ("list_agent_queries",)),
	("respond to employee requests", ("respond_to_agent_query",)),
	("view documents", ("show_documents",)),
	("edit job letters", ("edit_job_letter",)),
	("review job letters", ("review_job_letter",)),
	("view floors", ("floor_map",)),
	("change floor settings", ("update_floor_settings",)),
	("export information", ("export_information",)),
	("open Staff Pro pages", ("navigate_to_staff_pro",)),
)

NAV_ACCESS = {
	"employees": {"any_flags": ("see_agents", "see_floor_workers"), "perms": (("Employee", "read"),)},
	"attendance": {"flags": ("see_attendance",), "perms": (("Attendance", "read"),)},
	"hours": {"flags": ("see_attendance",), "perms": (("Attendance", "read"),)},
	"who_is_in": {"flags": ("see_attendance",)},
	"time_clock_adjustments": {"flags": ("see_time_clock",)},
	"paid_time_off": {"flags": ("see_paid_time_off",)},
	"overtime": {"flags": ("see_overtime",), "perms": (("Overtime Slip", "read"),)},
	"payroll": {"flags": ("see_agent_salary",), "perms": (("Payroll Entry", "read"),)},
	"agent_queries": {"flags": ("see_employee_requests",), "perms": (("HR Request", "read"),)},
	"floors": {"flags": ("see_floor",)},
}

EXPORT_ACCESS = {
	"employees": {"any_flags": ("see_agents", "see_floor_workers"), "perms": (("Employee", "read"),)},
	"attendance": {"flags": ("see_attendance",), "perms": (("Attendance", "read"),)},
	"hours": {"flags": ("see_attendance",), "perms": (("Attendance", "read"),)},
	"overtime": {"flags": ("see_overtime",), "perms": (("Overtime Slip", "read"),)},
	"payroll": {"flags": ("see_agent_salary",), "perms": (("Salary Slip", "read"),)},
	"agent_queries": {"flags": ("see_employee_requests",), "perms": (("HR Request", "read"),)},
	"queries": {"flags": ("see_employee_requests",), "perms": (("HR Request", "read"),)},
	"floors": {"flags": ("see_floor",), "perms": (("Office Floor", "read"),)},
}


def permission_denied_text() -> str:
	return _(PERMISSION_DENIED)


def raise_permission_denied() -> None:
	frappe.throw(permission_denied_text(), frappe.PermissionError, title=_("Ask AI"))


def user_can_use_tool(name: str, user: str | None = None) -> bool:
	"""True when this user may use the tool the same way they can use the screen."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	spec = TOOL_USER_ACCESS.get(name)
	if spec is None:
		return True
	return _access_allows(spec, user)


def user_can_run_call(name: str, args: dict | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not user_can_use_tool(name, user):
		return False
	args = args or {}
	if name == "export_information":
		dataset = args.get("dataset") or args.get("source")
		if not str(dataset or "").strip():
			return True
		return user_can_export(dataset, user)
	if name == "navigate_to_staff_pro":
		destination = args.get("destination")
		if not str(destination or "").strip():
			return True
		return user_can_navigate(destination, user)
	if name == "show_documents":
		return user_can_show_documents(args, user)
	return True


def assert_user_can_use_tool(name: str, user: str | None = None) -> None:
	if not user_can_use_tool(name, user):
		raise_permission_denied()


def assert_user_can_run_call(name: str, args: dict | None = None, user: str | None = None) -> None:
	if not user_can_run_call(name, args, user):
		raise_permission_denied()


def user_can_navigate(destination: str, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	key = str(destination or "").strip().lower().replace(" ", "_")
	spec = NAV_ACCESS.get(key)
	if spec is None:
		return False
	return _access_allows(spec, user)


def user_can_export(dataset: str, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	key = str(dataset or "").strip().lower().replace(" ", "_").replace("-", "_")
	spec = EXPORT_ACCESS.get(key)
	if spec is None:
		return False
	return _access_allows(spec, user)


def user_can_show_documents(args: dict | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	args = args or {}
	kind = str(args.get("kind") or "").strip().lower().replace(" ", "_")
	if kind in {"file", "files", "document", "documents"}:
		return _access_allows(
			{"flags": ("see_agent_documents",), "perms": (("Agent Document", "read"),)},
			user,
		)
	return _access_allows(
		{"flags": ("see_employee_requests",), "perms": (("HR Request", "read"),)},
		user,
	)


def denied_capability_labels(user: str | None = None) -> list[str]:
	user = user or frappe.session.user
	denied: list[str] = []
	for label, tools in CAPABILITIES:
		if tools and not any(user_can_use_tool(name, user) for name in tools):
			denied.append(label)
	return denied


def _access_allows(spec: dict, user: str) -> bool:
	from hrms.hr.role_access import can_see

	flags = spec.get("flags") or ()
	any_flags = spec.get("any_flags") or ()
	if flags and not all(can_see(flag, user) for flag in flags):
		return False
	if any_flags and not any(can_see(flag, user) for flag in any_flags):
		return False
	perms = spec.get("perms") or ()
	if perms and not all(_has_perm(doctype, ptype, user) for doctype, ptype in perms):
		return False
	any_perms = spec.get("any_perms") or ()
	if any_perms and not any(_has_perm(doctype, ptype, user) for doctype, ptype in any_perms):
		return False
	checker = spec.get("check")
	if checker == "documents":
		return _can_view_documents(user)
	if checker == "job_letter":
		return _can_change_job_letter(user)
	if checker == "export":
		return any(_access_allows(item, user) for item in EXPORT_ACCESS.values())
	if checker == "navigate":
		return any(_access_allows(item, user) for item in NAV_ACCESS.values())
	return True


def _can_view_documents(user: str) -> bool:
	letters = _access_allows(
		{"flags": ("see_employee_requests",), "perms": (("HR Request", "read"),)},
		user,
	)
	files = _access_allows(
		{"flags": ("see_agent_documents",), "perms": (("Agent Document", "read"),)},
		user,
	)
	return letters or files


def _can_change_job_letter(user: str) -> bool:
	from hrms.hr.job_letter import _can_edit_letter

	if not _can_edit_letter(user):
		return False
	return _access_allows(
		{"flags": ("see_employee_requests",), "perms": (("HR Request", "write"),)},
		user,
	)


def _has_perm(doctype: str, ptype: str, user: str) -> bool:
	try:
		return bool(frappe.has_permission(doctype, ptype, user=user))
	except Exception:
		return False


def can_use_ask_ai(user: str | None = None) -> bool:
	"""Desk users see Ask AI; tools still follow that user's role switches."""
	from hrms.ai.settings import is_ask_ai_enabled
	from hrms.boot import is_staff_pro_desk_admin

	user = user or frappe.session.user
	if not user or user == "Guest":
		return False
	if not is_ask_ai_enabled():
		return False
	if is_staff_pro_desk_admin(user):
		return True
	return bool(AI_ROLES.intersection(frappe.get_roles(user)))


def ensure_ai_access(user: str | None = None) -> None:
	from hrms.ai.settings import is_ask_ai_enabled

	user = user or frappe.session.user
	if not is_ask_ai_enabled():
		frappe.throw(_("Ask AI is turned off. Enable it in System Settings > AI."))
	if not can_use_ask_ai(user):
		frappe.throw(_("You do not have permission to use Ask AI."), frappe.PermissionError)


def ensure_conversation_access(name: str):
	from hrms.hr.doctype.ai_conversation.ai_conversation import conversation_user

	ensure_ai_access()
	doc = frappe.get_doc("AI Conversation", name)
	if conversation_user(doc) != frappe.session.user:
		frappe.throw(_("You do not have permission to access this conversation."), frappe.PermissionError)
	return doc
