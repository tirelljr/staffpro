# Copyright (c) 2026, Staff Pro BPO and Contributors

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _


def tool_result(summary: str, data: Any = None, blocks: list[dict] | None = None) -> str:
	return json.dumps(
		{"summary": summary, "data": data, "blocks": blocks or []},
		default=str,
		ensure_ascii=False,
	)


def parse_name_list(*values: Any) -> list[str]:
	names: list[str] = []
	for value in values:
		if value in (None, ""):
			continue
		if isinstance(value, (list, tuple, set)):
			for item in value:
				names.extend(parse_name_list(item))
			continue
		text = str(value).strip()
		if not text:
			continue
		if text.startswith("["):
			try:
				parsed = json.loads(text)
			except (TypeError, ValueError):
				parsed = None
			if isinstance(parsed, list):
				names.extend(parse_name_list(parsed))
				continue
		for part in text.replace(";", ",").split(","):
			item = part.strip().strip('"').strip("'")
			if item and item not in names:
				names.append(item)
	return names


def resolve_employee(value: str) -> str:
	value = str(value or "").strip()
	if not value:
		return ""
	if frappe.db.exists("Employee", value):
		return value
	name = frappe.db.get_value("Employee", {"employee_name": value}, "name")
	if name:
		return name
	term = f"%{value}%"
	matches = frappe.get_all(
		"Employee",
		or_filters={"employee_name": ["like", term], "name": ["like", term]},
		pluck="name",
		limit_page_length=5,
	)
	if len(matches) == 1:
		return matches[0]
	if len(matches) > 1:
		frappe.throw(_("Multiple employees match {0}.").format(value))
	frappe.throw(_("Could not find employee {0}.").format(value))


def resolve_employees(*values: Any) -> list[str]:
	employees = [resolve_employee(value) for value in parse_name_list(*values)]
	if not employees:
		frappe.throw(_("Select at least one employee."))
	return employees
