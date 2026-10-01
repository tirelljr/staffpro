# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint
from langchain_core.tools import tool

from hrms.ai.tools.common import resolve_employee, tool_result
from hrms.hr.page.floor_map.floor_map import add_seat, assign_cubicle, get_floor_map


@tool
def floor_map(office_floor: str = "") -> str:
	"""Show office floors, vacant and occupied seats, and workstation assignments."""
	result = get_floor_map(office_floor=office_floor or None)
	rows = []
	for group in result.get("rows") or []:
		for cubicle in group.get("cubicles") or []:
			rows.append(
				{
					"cubicle": cubicle.get("name"),
					"row": cubicle.get("row"),
					"seat_number": cubicle.get("seat_number"),
					"status": cubicle.get("status"),
					"employee_name": cubicle.get("employee_name") or "",
					"device_id": cubicle.get("device_id") or "",
					"ip_address": cubicle.get("ip_address") or "",
				}
			)
	blocks = [
		{
			"type": "table",
			"columns": [
				{"key": "row", "label": "Row"},
				{"key": "seat_number", "label": "Seat"},
				{"key": "status", "label": "Status"},
				{"key": "employee_name", "label": "Agent"},
			],
			"rows": rows[:40],
		},
		{"type": "navigate", "label": "Open Floor Map", "route": ["floor-map"]},
	]
	totals = result.get("totals") or {}
	floor = result.get("office_floor") or office_floor or "floors"
	return tool_result(
		f"{floor}: {totals.get('occupied', 0)} occupied, {totals.get('vacant', 0)} vacant.",
		result,
		blocks,
	)


def _resolve_office_floor(value: str) -> str:
	value = str(value or "").strip()
	if not value:
		return ""
	if frappe.db.exists("Office Floor", value):
		return value
	name = frappe.db.get_value("Office Floor", {"floor_name": value}, "name")
	if name:
		return name
	matches = frappe.get_all(
		"Office Floor",
		filters={"floor_name": ["like", f"%{value}%"]},
		pluck="name",
		limit_page_length=5,
	)
	if len(matches) == 1:
		return matches[0]
	return value


def _resolve_employee(value: str) -> str:
	return resolve_employee(value)


def _resolve_cubicle(arguments: dict[str, Any]) -> str:
	cubicle = str(arguments.get("cubicle") or "").strip()
	if cubicle and frappe.db.exists("Cubicle", cubicle):
		return cubicle
	office_floor = _resolve_office_floor(
		str(arguments.get("office_floor") or arguments.get("floor_name") or "")
	)
	row = str(arguments.get("row") or "").strip().upper()
	if row.startswith("ROW "):
		row = row[4:].strip()
	raw_seat = arguments.get("seat_number")
	if isinstance(raw_seat, str):
		raw_seat = raw_seat.lower().replace("seat", "").strip()
	seat = cint(raw_seat)
	if office_floor and row and seat:
		name = frappe.db.get_value(
			"Cubicle",
			{"office_floor": office_floor, "row": row, "seat_number": seat},
			"name",
		)
		if name:
			return name
	frappe.throw(_("Could not find that seat."))


def execute_update_floor_settings(arguments: dict[str, Any]) -> dict[str, Any]:
	action = str(arguments.get("action") or "update_floor").strip().lower().replace(" ", "_")
	if action == "create_floor":
		return _create_floor(arguments)
	if action == "update_floor":
		return _update_floor(arguments)
	if action in {"assign_seat", "assign"}:
		return _assign_seat(arguments, clear=False)
	if action in {"clear_seat", "clear", "unassign"}:
		return _assign_seat(arguments, clear=True)
	if action in {"add_seat", "add"}:
		return add_seat(
			office_floor=_resolve_office_floor(str(arguments.get("office_floor") or arguments.get("floor_name") or "")),
			row=str(arguments.get("row") or ""),
		)
	frappe.throw(_("Unsupported floor action."))


def _create_floor(arguments: dict[str, Any]) -> dict[str, Any]:
	frappe.has_permission("Office Floor", "create", throw=True)
	floor_name = str(arguments.get("floor_name") or arguments.get("office_floor") or "").strip()
	if not floor_name:
		frappe.throw(_("Floor name is required."))
	doc = frappe.get_doc(
		{
			"doctype": "Office Floor",
			"floor_name": floor_name,
			"work_site": str(arguments.get("work_site") or "") or None,
			"notes": str(arguments.get("notes") or "") or None,
		}
	)
	doc.insert()
	return {"name": doc.name, "action": "create_floor"}


def _update_floor(arguments: dict[str, Any]) -> dict[str, Any]:
	frappe.has_permission("Office Floor", "write", throw=True)
	name = _resolve_office_floor(str(arguments.get("office_floor") or arguments.get("floor_name") or ""))
	if not name or not frappe.db.exists("Office Floor", name):
		frappe.throw(_("Select a floor to update."))
	doc = frappe.get_doc("Office Floor", name)
	if "work_site" in arguments:
		doc.work_site = str(arguments.get("work_site") or "") or None
	if "notes" in arguments:
		doc.notes = str(arguments.get("notes") or "") or None
	doc.save()
	return {"name": doc.name, "action": "update_floor", "work_site": doc.work_site, "notes": doc.notes}


def _assign_seat(arguments: dict[str, Any], clear: bool) -> dict[str, Any]:
	cubicle = _resolve_cubicle(arguments)
	employee = "" if clear else _resolve_employee(str(arguments.get("employee") or ""))
	if not clear and not employee:
		frappe.throw(_("Select an agent to assign to that seat."))
	kwargs: dict[str, Any] = {
		"cubicle": cubicle,
		"employee": employee or None,
		"clear": 1 if clear else 0,
	}
	device_id = str(arguments.get("device_id") or "").strip()
	ip_address = str(arguments.get("ip_address") or "").strip()
	if device_id:
		kwargs["device_id"] = device_id
	if ip_address:
		kwargs["ip_address"] = ip_address
	return assign_cubicle(**kwargs)
