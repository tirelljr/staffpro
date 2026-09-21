# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from langchain_core.tools import tool

from hrms.ai.tools.common import tool_result

OPEN_STATUSES = ("Open", "In Progress", "Waiting on Employee")
REPLY_STATUSES = {
	"open": "Open",
	"in progress": "In Progress",
	"waiting": "Waiting on Employee",
	"waiting on employee": "Waiting on Employee",
	"resolved": "Resolved",
	"rejected": "Rejected",
	"cancelled": "Cancelled",
}


@tool
def list_agent_queries(
	status: str = "",
	employee: str = "",
	request_type: str = "",
	limit: int = 25,
) -> str:
	"""List agent HR requests/queries. Defaults to open, in progress, and waiting requests."""
	frappe.has_permission("HR Request", "read", throw=True)
	filters: dict[str, Any] = {}
	normalized = REPLY_STATUSES.get((status or "").strip().lower())
	if normalized:
		filters["status"] = normalized
	else:
		filters["status"] = ["in", list(OPEN_STATUSES)]
	if employee:
		filters["employee"] = employee
	if request_type:
		filters["request_type"] = request_type
	rows = frappe.get_list(
		"HR Request",
		fields=[
			"name",
			"employee",
			"employee_name",
			"request_type",
			"subject",
			"status",
			"priority",
			"creation",
		],
		filters=filters,
		order_by="modified desc",
		limit_page_length=max(1, min(int(limit or 25), 50)),
	)
	blocks = [
		{
			"type": "table",
			"columns": [
				{"key": "name", "label": "Request"},
				{"key": "employee_name", "label": "Agent"},
				{"key": "subject", "label": "Subject"},
				{"key": "status", "label": "Status"},
			],
			"rows": rows,
		},
		{"type": "navigate", "label": "Open Employee Requests", "route": ["List", "HR Request"]},
	]
	return tool_result(f"Found {len(rows)} agent queries.", rows, blocks if rows else [])


def execute_respond_to_agent_query(arguments: dict[str, Any]) -> dict[str, Any]:
	frappe.has_permission("HR Request", "write", throw=True)
	name = str(arguments.get("name") or "").strip()
	response = str(arguments.get("response") or arguments.get("comment") or "").strip()
	if not name:
		frappe.throw(_("Select an agent query to respond to."))
	if not response:
		frappe.throw(_("Enter a response for the agent."))
	if not frappe.db.exists("HR Request", name):
		frappe.throw(_("Agent query {0} was not found.").format(name))

	status = REPLY_STATUSES.get(str(arguments.get("status") or "Resolved").strip().lower(), "Resolved")
	doc = frappe.get_doc("HR Request", name)
	doc.check_permission("write")
	doc.status = status
	if status in {"Resolved", "Rejected"}:
		doc.resolution = response
	if not doc.assigned_to:
		doc.assigned_to = frappe.session.user
	doc.save()
	doc.add_comment("Comment", text=response)
	return {
		"name": doc.name,
		"status": doc.status,
		"employee": doc.employee_name or doc.employee,
		"blocks": [
			{"type": "navigate", "label": _("Open {0}").format(doc.name), "route": ["Form", "HR Request", doc.name]}
		],
	}
