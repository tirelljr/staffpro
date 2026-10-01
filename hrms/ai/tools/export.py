# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import escape_html, nowdate
from frappe.utils.csvutils import to_csv
from frappe.utils.file_manager import save_file

DATASETS = {
	"employees": "Employees",
	"attendance": "Attendance hours",
	"hours": "Attendance hours",
	"overtime": "Overtime",
	"payroll": "Payroll",
	"agent_queries": "Agent queries",
	"queries": "Agent queries",
	"floors": "Floors",
}
FORMATS = {
	"csv": "csv",
	"excel": "xlsx",
	"xlsx": "xlsx",
	"xls": "xlsx",
	"pdf": "pdf",
}


def collect_export_data(arguments: dict[str, Any]) -> dict[str, Any]:
	dataset = _dataset_key(arguments.get("dataset") or arguments.get("source") or "")
	if dataset == "employees":
		frappe.has_permission("Employee", "read", throw=True)
		filters: dict[str, Any] = {}
		if arguments.get("department"):
			filters["department"] = arguments["department"]
		if arguments.get("status"):
			filters["status"] = arguments["status"]
		rows = frappe.get_list(
			"Employee",
			fields=["name", "employee_name", "department", "designation", "status"],
			filters=filters,
			order_by="employee_name asc",
			limit_page_length=500,
		)
		return {
			"title": _("Employees"),
			"columns": [
				{"key": "name", "label": "Employee"},
				{"key": "employee_name", "label": "Name"},
				{"key": "department", "label": "Department"},
				{"key": "designation", "label": "Designation"},
				{"key": "status", "label": "Status"},
			],
			"rows": rows,
		}

	if dataset in {"attendance", "hours"}:
		from hrms.hr.doctype.attendance.attendance import get_hours_rows

		today = nowdate()
		result = get_hours_rows(
			from_date=arguments.get("from_date") or today,
			to_date=arguments.get("to_date") or today,
			employee=arguments.get("employee") or None,
			department=arguments.get("department") or None,
		)
		return {
			"title": _("Attendance hours"),
			"columns": [
				{"key": "employee_name", "label": "Employee"},
				{"key": "attendance_date", "label": "Date"},
				{"key": "working_hours", "label": "Hours"},
				{"key": "overtime_hours", "label": "Overtime"},
			],
			"rows": result.get("rows") or [],
		}

	if dataset == "overtime":
		frappe.has_permission("Overtime Slip", "read", throw=True)
		filters = {}
		if arguments.get("department"):
			filters["department"] = arguments["department"]
		if arguments.get("employee"):
			filters["employee"] = arguments["employee"]
		rows = frappe.get_list(
			"Overtime Slip",
			fields=["name", "employee_name", "posting_date", "department", "total_overtime_duration"],
			filters=filters,
			order_by="posting_date desc",
			limit_page_length=500,
		)
		return {
			"title": _("Overtime"),
			"columns": [
				{"key": "employee_name", "label": "Employee"},
				{"key": "posting_date", "label": "Date"},
				{"key": "department", "label": "Department"},
				{"key": "total_overtime_duration", "label": "Hours"},
			],
			"rows": rows,
		}

	if dataset == "payroll":
		from hrms.hr.desk_dashboard import get_upcoming_payroll

		frappe.has_permission("Salary Slip", "read", throw=True)
		result = get_upcoming_payroll(
			period=str(arguments.get("period") or "monthly"),
			company=arguments.get("company") or None,
		)
		return {
			"title": _("Payroll"),
			"columns": [
				{"key": "employee_name", "label": "Employee"},
				{"key": "department", "label": "Department"},
				{"key": "gross_pay", "label": "Gross Pay"},
				{"key": "net_pay", "label": "Net Pay"},
			],
			"rows": result.get("rows") or [],
		}

	if dataset in {"agent_queries", "queries"}:
		frappe.has_permission("HR Request", "read", throw=True)
		filters: dict[str, Any] = {}
		if arguments.get("status"):
			filters["status"] = arguments["status"]
		else:
			filters["status"] = ["in", ["Open", "In Progress", "Waiting on Employee"]]
		if arguments.get("employee"):
			filters["employee"] = arguments["employee"]
		if arguments.get("request_type"):
			filters["request_type"] = arguments["request_type"]
		rows = frappe.get_list(
			"HR Request",
			fields=["name", "employee_name", "subject", "status", "request_type"],
			filters=filters,
			order_by="modified desc",
			limit_page_length=500,
		)
		return {
			"title": _("Agent queries"),
			"columns": [
				{"key": "name", "label": "Request"},
				{"key": "employee_name", "label": "Agent"},
				{"key": "subject", "label": "Subject"},
				{"key": "status", "label": "Status"},
			],
			"rows": rows,
		}

	from hrms.hr.page.floor_map.floor_map import get_floor_map

	result = get_floor_map(office_floor=arguments.get("office_floor") or None)
	rows = []
	for group in result.get("rows") or []:
		for cubicle in group.get("cubicles") or []:
			rows.append(
				{
					"row": cubicle.get("row"),
					"seat_number": cubicle.get("seat_number"),
					"status": cubicle.get("status"),
					"employee_name": cubicle.get("employee_name") or "",
					"device_id": cubicle.get("device_id") or "",
				}
			)
	return {
		"title": _("Floors"),
		"columns": [
			{"key": "row", "label": "Row"},
			{"key": "seat_number", "label": "Seat"},
			{"key": "status", "label": "Status"},
			{"key": "employee_name", "label": "Agent"},
			{"key": "device_id", "label": "Device"},
		],
		"rows": rows,
	}


def execute_export_information(arguments: dict[str, Any], conversation: str | None = None) -> dict[str, Any]:
	file_format = _file_format(arguments.get("file_format") or arguments.get("format") or "csv")
	data = collect_export_data(arguments)
	rows = list(data.get("rows") or [])[:500]
	if not rows:
		frappe.throw(_("Nothing to export for {0}.").format(data["title"]))
	content, filename = _render_file(data["title"], data["columns"], rows, file_format)
	file_doc = save_file(
		fname=filename,
		content=content,
		dt="AI Conversation" if conversation else "",
		dn=conversation or "",
		folder="Home",
		is_private=1,
	)
	label = _("Download {0}").format({"csv": "CSV", "xlsx": "Excel", "pdf": "PDF"}[file_format])
	return {
		"file_url": file_doc.file_url,
		"file_name": file_doc.file_name,
		"rows": len(rows),
		"blocks": [
			{
				"type": "download",
				"file_url": file_doc.file_url,
				"file_name": file_doc.file_name,
				"label": label,
			}
		],
	}


def _dataset_key(value: str) -> str:
	key = " ".join(str(value or "").strip().lower().replace("-", "_").split()).replace(" ", "_")
	if key in DATASETS:
		return key
	for name in DATASETS:
		if name in key:
			return name
	frappe.throw(_("Choose employees, attendance, overtime, payroll, agent queries, or floors to export."))


def _file_format(value: str) -> str:
	key = str(value or "csv").strip().lower().lstrip(".")
	if key in FORMATS:
		return FORMATS[key]
	frappe.throw(_("Choose PDF, Excel, or CSV."))


def _render_file(title: str, columns: list[dict], rows: list[dict], file_format: str) -> tuple[bytes | str, str]:
	headers = [column["label"] for column in columns]
	keys = [column["key"] for column in columns]
	table = [headers, *[[_cell(row.get(key)) for key in keys] for row in rows]]
	stamp = nowdate()
	safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in title)
	if file_format == "csv":
		return to_csv(table), f"Staff_Pro_{safe}_{stamp}.csv"
	if file_format == "xlsx":
		from frappe.utils.xlsxutils import make_xlsx

		return make_xlsx(table, title).getvalue(), f"Staff_Pro_{safe}_{stamp}.xlsx"
	from frappe.utils.pdf import get_pdf
	html = [
		"<html><head><meta charset='utf-8'></head><body>",
		f"<h1>{escape_html(title)}</h1>",
		f"<p>{escape_html(stamp)}</p>",
		"<table border='1' cellspacing='0' cellpadding='6'><thead><tr>",
		"".join(f"<th>{escape_html(header)}</th>" for header in headers),
		"</tr></thead><tbody>",
	]
	for values in table[1:]:
		html.append("<tr>" + "".join(f"<td>{escape_html(value)}</td>" for value in values) + "</tr>")
	html.append("</tbody></table></body></html>")
	return get_pdf("".join(html)), f"Staff_Pro_{safe}_{stamp}.pdf"


def _cell(value: Any) -> str:
	if value is None:
		return ""
	return str(value)
