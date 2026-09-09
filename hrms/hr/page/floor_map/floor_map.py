# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint

from hrms.hr.agent_access import office_default_ipv4


def _require_floor_access():
	frappe.only_for(["HR Manager", "HR User", "System Manager", "Administrator"])


@frappe.whitelist()
def get_floor_map(office_floor: str | None = None):
	_require_floor_access()
	floors = frappe.get_all(
		"Office Floor",
		fields=["name", "floor_name", "work_site"],
		order_by="floor_name",
	)
	if not floors:
		return {
			"floors": [],
			"office_floor": "",
			"seats": [],
			"rows": [],
			"totals": {"total": 0, "occupied": 0, "vacant": 0},
		}

	selected = office_floor if office_floor and any(row.name == office_floor for row in floors) else floors[0].name
	cubicles = frappe.get_all(
		"Cubicle",
		fields=[
			"name",
			"office_floor",
			"row",
			"seat_number",
			"status",
			"employee",
			"employee_name",
			"device_id",
			"ip_address",
		],
		filters={"office_floor": selected},
		order_by="row asc, seat_number asc",
	)

	employee_ids = [row.employee for row in cubicles if row.employee]
	images = {}
	defaults = {}
	if employee_ids:
		emp_fields = ["name", "image"]
		if frappe.get_meta("Employee").has_field("default_ipv4"):
			emp_fields.append("default_ipv4")
		for row in frappe.get_all("Employee", fields=emp_fields, filters={"name": ["in", employee_ids]}):
			images[row.name] = row.image
			defaults[row.name] = getattr(row, "default_ipv4", None) or ""

	office_ip = office_default_ipv4()

	seats = sorted({cint(row.seat_number) for row in cubicles if cint(row.seat_number)})
	grouped = defaultdict(list)
	for row in cubicles:
		grouped[row.row].append(
			{
				"name": row.name,
				"row": row.row,
				"seat_number": cint(row.seat_number),
				"status": row.status or ("Occupied" if row.employee else "Vacant"),
				"employee": row.employee or "",
				"employee_name": row.employee_name or "",
				"image": images.get(row.employee) or "",
				"device_id": row.device_id or "",
				"ip_address": row.ip_address or defaults.get(row.employee) or office_ip,
			}
		)

	rows = [{"row": label, "cubicles": grouped[label]} for label in sorted(grouped.keys())]
	occupied = sum(1 for row in cubicles if row.employee)
	return {
		"floors": floors,
		"office_floor": selected,
		"seats": seats,
		"rows": rows,
		"totals": {
			"total": len(cubicles),
			"occupied": occupied,
			"vacant": len(cubicles) - occupied,
		},
	}


@frappe.whitelist()
def assign_cubicle(
	cubicle: str,
	employee: str | None = None,
	device_id: str | None = None,
	ip_address: str | None = None,
	clear: int | str = 0,
):
	_require_floor_access()
	if not frappe.has_permission("Cubicle", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	doc = frappe.get_doc("Cubicle", cubicle)
	if cint(clear):
		doc.employee = None
		doc.employee_name = None
	elif employee:
		doc.employee = employee
	if device_id is not None:
		doc.device_id = device_id
	if ip_address is not None:
		doc.ip_address = ip_address
	doc.save()
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def add_seat(office_floor: str, row: str):
	_require_floor_access()
	if not frappe.has_permission("Cubicle", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	row = (row or "").strip().upper()
	if not office_floor or not row:
		frappe.throw(_("Floor and row are required"))
	if not frappe.db.exists("Office Floor", office_floor):
		frappe.throw(_("Office Floor {0} not found").format(office_floor))

	current = frappe.get_all(
		"Cubicle",
		filters={"office_floor": office_floor, "row": row},
		pluck="seat_number",
	)
	next_seat = (max(cint(n) for n in current) + 1) if current else 1
	if next_seat > 40:
		frappe.throw(_("A row can have at most 40 seats"))

	doc = frappe.get_doc(
		{
			"doctype": "Cubicle",
			"office_floor": office_floor,
			"row": row,
			"seat_number": next_seat,
		}
	)
	doc.insert()
	return {"name": doc.name, "row": row, "seat_number": next_seat}


@frappe.whitelist()
def delete_seat(cubicle: str):
	_require_floor_access()
	if not frappe.has_permission("Cubicle", "delete"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	doc = frappe.get_doc("Cubicle", cubicle)
	name = doc.name
	doc.delete()
	return {"name": name}


@frappe.whitelist()
def move_assignment(source: str, target: str):
	_require_floor_access()
	if not frappe.has_permission("Cubicle", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if source == target:
		return {"moved": 0}

	from_doc = frappe.get_doc("Cubicle", source)
	to_doc = frappe.get_doc("Cubicle", target)
	if from_doc.office_floor != to_doc.office_floor:
		frappe.throw(_("Seats must be on the same floor"))

	from_employee = from_doc.employee
	to_employee = to_doc.employee
	if not from_employee and not to_employee:
		return {"moved": 0}

	from_doc.employee = None
	from_doc.employee_name = None
	from_doc.save()
	to_doc.employee = None
	to_doc.employee_name = None
	to_doc.save()

	from_doc.employee = to_employee
	to_doc.employee = from_employee
	from_doc.save()
	to_doc.save()
	return {"moved": 1, "source": from_doc.name, "target": to_doc.name}
