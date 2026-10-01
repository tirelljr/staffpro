# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from langchain_core.tools import tool

from hrms.ai.permissions import PERMISSION_DENIED, user_can_show_documents
from hrms.ai.tools.common import resolve_employee, tool_result
from hrms.hr.job_letter import JOB_LETTER, OFFICE_PRINT

OPEN_STATUSES = ("Open", "In Progress", "Waiting on Employee")


@tool
def show_documents(employee: str = "", kind: str = "", name: str = "") -> str:
	"""Show job letters, office print requests, or files in an agent's documents.
	kind is job_letter, office_print, or file. Pass name to open one letter and include its preview.
	"""
	if not user_can_show_documents({"kind": kind, "name": name, "employee": employee}):
		return tool_result(PERMISSION_DENIED, {"permission_denied": True})
	if name:
		return _show_named(name)
	kind_key = (kind or "").strip().lower().replace(" ", "_")
	if kind_key in {"file", "files", "document", "documents"}:
		return _list_files(employee)
	request_type = OFFICE_PRINT if "print" in kind_key else JOB_LETTER if kind_key else ""
	return _list_letters(employee, request_type)


def _show_named(name: str) -> str:
	if not frappe.db.exists("HR Request", name):
		frappe.throw(_("Request {0} was not found.").format(name))
	doc = frappe.get_doc("HR Request", name)
	doc.check_permission("read")
	if doc.request_type not in {JOB_LETTER, OFFICE_PRINT}:
		frappe.throw(_("Request {0} is not a job letter.").format(name))
	blocks = [
		{
			"type": "document",
			"title": doc.subject or doc.name,
			"html": doc.letter_html or "",
			"route": ["Form", "HR Request", doc.name],
		}
	]
	return tool_result(
		f"{doc.request_type} {doc.name} for {doc.employee_name or doc.employee} is {doc.status}.",
		{"name": doc.name, "status": doc.status, "subject": doc.subject},
		blocks,
	)


def _list_letters(employee: str, request_type: str) -> str:
	frappe.has_permission("HR Request", "read", throw=True)
	filters: dict[str, Any] = {"status": ["in", list(OPEN_STATUSES)]}
	if request_type:
		filters["request_type"] = request_type
	else:
		filters["request_type"] = ["in", [JOB_LETTER, OFFICE_PRINT]]
	if employee:
		filters["employee"] = resolve_employee(employee)
	rows = frappe.get_list(
		"HR Request",
		fields=["name", "employee_name", "request_type", "subject", "status"],
		filters=filters,
		order_by="modified desc",
		limit_page_length=25,
	)
	blocks = [
		{
			"type": "table",
			"columns": [
				{"key": "name", "label": "Request"},
				{"key": "employee_name", "label": "Agent"},
				{"key": "request_type", "label": "Type"},
				{"key": "subject", "label": "Subject"},
				{"key": "status", "label": "Status"},
			],
			"rows": rows,
		},
		{"type": "navigate", "label": "Open Employee Requests", "route": ["List", "HR Request"]},
	]
	return tool_result(f"Found {len(rows)} letters.", rows, blocks if rows else [])


def _list_files(employee: str) -> str:
	from hrms.hr.agent_filesystem import list_files

	employee_id = resolve_employee(employee) if employee else ""
	if not employee_id:
		frappe.throw(_("Say which agent's documents to show."))
	rows = list_files(employee_id)
	shown = [
		{
			"name": row["name"],
			"file_name": row["file_name"],
			"category": row["category"],
			"file_url": row["file_url"],
		}
		for row in rows
	]
	blocks = [
		{
			"type": "table",
			"columns": [
				{"key": "file_name", "label": "File"},
				{"key": "category", "label": "Folder"},
			],
			"rows": shown,
		}
	]
	blocks.extend(
		{"type": "download", "label": row["file_name"], "file_url": row["file_url"], "file_name": row["file_name"]}
		for row in shown
		if row.get("file_url")
	)
	return tool_result(f"Found {len(shown)} documents.", shown, blocks if shown else [])


def execute_edit_job_letter(arguments: dict[str, Any]) -> dict[str, Any]:
	from hrms.hr.job_letter import update_job_letter

	name = str(arguments.get("name") or "").strip()
	if not name:
		frappe.throw(_("Select a job letter to edit."))
	text = arguments.get("letter_text")
	result = update_job_letter(
		name=name,
		addressed_to=arguments.get("addressed_to") or None,
		recipient_address=arguments.get("recipient_address") or None,
		honorific=arguments.get("honorific") or None,
		annual_salary=arguments.get("annual_salary") or None,
		biweekly_salary=arguments.get("biweekly_salary") or None,
		letter_paragraphs=None if text in (None, "") else str(text),
	)
	return {
		"name": result["name"],
		"subject": result["subject"],
		"blocks": [
			{
				"type": "document",
				"title": result.get("subject") or result["name"],
				"html": result.get("letter_html") or "",
				"route": ["Form", "HR Request", result["name"]],
			}
		],
	}


def execute_review_job_letter(arguments: dict[str, Any]) -> dict[str, Any]:
	from hrms.hr.job_letter import review_job_letter

	name = str(arguments.get("name") or "").strip()
	if not name:
		frappe.throw(_("Select a request to review."))
	result = review_job_letter(
		name=name,
		action=str(arguments.get("action") or ""),
		comment=str(arguments.get("comment") or ""),
	)
	return {
		"name": result["name"],
		"status": result["status"],
		"blocks": [
			{
				"type": "navigate",
				"label": _("Open {0}").format(result["name"]),
				"route": ["Form", "HR Request", result["name"]],
			}
		],
	}
