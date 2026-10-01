# Copyright (c) 2026, Staff Pro BPO and Contributors

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from langchain_core.tools import tool

from hrms.ai.tools.common import tool_result
from hrms.hr.desk_dashboard import get_upcoming_payroll
from hrms.payroll.auto_payroll import (
	build_payroll_entry,
	canonical_frequency,
	get_last_working_period,
)
from hrms.payroll.doctype.payroll_entry.payroll_entry import get_start_end_dates


FREQUENCY_ALIASES = {
	"biweekly": "Fortnightly",
	"bi-weekly": "Fortnightly",
	"bi weekly": "Fortnightly",
}


@tool
def upcoming_payroll(period: str = "monthly", company: str = "") -> str:
	"""Preview upcoming employee payroll for weekly, biweekly, or monthly periods."""
	frappe.has_permission("Salary Slip", "read", throw=True)
	result = get_upcoming_payroll(period=period, company=company or None)
	rows = result.get("rows", [])
	columns = [
		{"key": "employee_name", "label": "Employee"},
		{"key": "department", "label": "Department"},
		{"key": "gross_pay", "label": "Gross Pay"},
		{"key": "net_pay", "label": "Net Pay"},
	]
	blocks = [
		{"type": "table", "columns": columns, "rows": rows[:25]},
		{"type": "navigate", "label": "Open Payroll", "route": ["List", "Payroll Entry"]},
	]
	return tool_result(
		f"Upcoming payroll for {result.get('period_label') or period} contains {len(rows)} employees.",
		result,
		blocks,
	)


def execute_run_payroll(arguments: dict[str, Any]) -> dict[str, Any]:
	frappe.has_permission("Payroll Entry", "create", throw=True)
	company = str(
		arguments.get("company")
		or frappe.defaults.get_user_default("Company")
		or frappe.defaults.get_global_default("company")
		or ""
	).strip()
	if not company:
		frappe.throw(_("Select a company before running payroll."))

	frequency = _payroll_frequency(arguments.get("payroll_frequency") or arguments.get("frequency") or "Fortnightly")
	start_date = str(arguments.get("start_date") or "").strip() or None
	end_date = str(arguments.get("end_date") or "").strip() or None
	if start_date and not end_date:
		dates = get_start_end_dates(frequency, start_date, company)
		start_date, end_date = dates.start_date, dates.end_date
	elif not start_date or not end_date:
		period = get_last_working_period()
		start_date = start_date or period["start_date"]
		end_date = end_date or period["end_date"]

	frappe.flags.skip_payroll_enqueue = True
	settings = frappe.get_single("Payroll Settings")
	entry = build_payroll_entry(settings, company, start_date, end_date, frequency)
	department = str(arguments.get("department") or "").strip()
	if department:
		entry.department = department
	entry.fill_employee_details()
	entry.insert()
	entry.submit()
	entry.reload()
	return {
		"name": entry.name,
		"start_date": entry.start_date,
		"end_date": entry.end_date,
		"employees": entry.number_of_employees,
		"status": entry.status,
		"blocks": [
			{
				"type": "navigate",
				"label": _("Open {0}").format(entry.name),
				"route": ["Form", "Payroll Entry", entry.name],
			}
		],
	}


def _payroll_frequency(value: str) -> str:
	key = " ".join(str(value or "").strip().lower().split())
	mapped = FREQUENCY_ALIASES.get(key) or canonical_frequency(value)
	return mapped or "Fortnightly"
