# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Copy an agent's hourly rate to other agents, a branch, campaign, or team."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt


def _as_list(value) -> list[str]:
	if not value:
		return []
	if isinstance(value, str):
		value = frappe.parse_json(value) if value.startswith("[") else [value]
	if isinstance(value, dict):
		value = list(value.values())
	out = []
	for item in value or []:
		if isinstance(item, dict):
			item = item.get("employee") or item.get("name") or item.get("branch") or item.get("value")
		if item:
			out.append(item)
	return out


def find_hourly_rate_targets(
	source_employee: str | None = None,
	employees: list[str] | str | None = None,
	branches: list[str] | str | None = None,
	campaigns: list[str] | str | None = None,
	teams: list[str] | str | None = None,
	company: str | None = None,
) -> list[str]:
	names = set(_as_list(employees))
	branch_list = _as_list(branches)
	campaign_list = _as_list(campaigns)
	team_list = _as_list(teams)

	if not company and source_employee:
		company = frappe.db.get_value("Employee", source_employee, "company")

	filters = {"status": "Active"}
	if company:
		filters["company"] = company

	or_filters = []
	if branch_list:
		or_filters.append(["branch", "in", branch_list])
	if campaign_list:
		or_filters.append(["grade", "in", campaign_list])
	if team_list:
		or_filters.append(["department", "in", team_list])

	if or_filters:
		grouped = frappe.get_all(
			"Employee",
			filters=filters,
			or_filters=or_filters,
			pluck="name",
		)
		names.update(grouped)

	if source_employee:
		names.discard(source_employee)

	return sorted(names)


@frappe.whitelist()
def preview_hourly_rate_targets(
	source_employee: str | None = None,
	employees: list[str] | str | None = None,
	branches: list[str] | str | None = None,
	campaigns: list[str] | str | None = None,
	teams: list[str] | str | None = None,
	company: str | None = None,
):
	targets = find_hourly_rate_targets(
		source_employee=source_employee,
		employees=employees,
		branches=branches,
		campaigns=campaigns,
		teams=teams,
		company=company,
	)
	rows = []
	if targets:
		rows = frappe.get_all(
			"Employee",
			filters={"name": ("in", targets)},
			fields=["name", "employee_name", "branch", "grade", "department", "ctc"],
			order_by="employee_name",
		)
	return {"count": len(targets), "employees": rows}


@frappe.whitelist()
def apply_hourly_rate(
	source_employee: str | None = None,
	hourly_rate: float | str | None = None,
	employees: list[str] | str | None = None,
	branches: list[str] | str | None = None,
	campaigns: list[str] | str | None = None,
	teams: list[str] | str | None = None,
	company: str | None = None,
):
	if not frappe.has_permission("Employee", "write"):
		frappe.throw(_("Not permitted to update agents."), frappe.PermissionError)

	rate = flt(hourly_rate)
	if rate <= 0:
		frappe.throw(_("Enter an Agent Hourly greater than zero."))

	targets = find_hourly_rate_targets(
		source_employee=source_employee,
		employees=employees,
		branches=branches,
		campaigns=campaigns,
		teams=teams,
		company=company,
	)
	if source_employee:
		targets = [source_employee, *[name for name in targets if name != source_employee]]
	if not targets:
		frappe.throw(_("Select this agent or other agents, a branch, campaign, or team."))

	from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
		ensure_salary_structure_assignment,
	)

	updated = 0
	assigned = []
	for name in targets:
		if not frappe.has_permission("Employee", "write", name):
			continue
		frappe.db.set_value("Employee", name, "ctc", rate, update_modified=True)
		assignment = ensure_salary_structure_assignment(name)
		if assignment:
			assigned.append(assignment)
		updated += 1

	frappe.flags.hour_rate_cache = {}
	return {"updated": updated, "rate": rate, "assignments": assigned}
