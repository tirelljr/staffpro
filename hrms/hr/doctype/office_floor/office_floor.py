# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import string

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from hrms.hr.staff_pro_shift_locations import DEFAULT_SHIFT_LOCATIONS

DEFAULT_OFFICE_FLOORS = tuple((name, name) for name in DEFAULT_SHIFT_LOCATIONS)


class OfficeFloor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		floor_name: DF.Data
		notes: DF.SmallText | None
		work_site: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.floor_name = (self.floor_name or "").strip()
		if not self.floor_name:
			frappe.throw(_("Floor Name is required"))


def row_label(index: int) -> str:
	"""1-based index to A, B, ... Z, AA, AB, ..."""
	if index < 1:
		frappe.throw(_("Row count must be at least 1"))
	label = ""
	n = index
	while n:
		n, rem = divmod(n - 1, 26)
		label = string.ascii_uppercase[rem] + label
	return label


@frappe.whitelist()
def generate_layout(office_floor: str, row_count: int | str, seats_per_row: int | str) -> dict:
	frappe.only_for(["HR Manager", "HR User", "System Manager", "Administrator"])
	if not frappe.has_permission("Cubicle", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	floor = frappe.get_doc("Office Floor", office_floor)
	rows = cint(row_count)
	seats = cint(seats_per_row)
	if rows < 1 or rows > 52:
		frappe.throw(_("Row count must be between 1 and 52"))
	if seats < 1 or seats > 40:
		frappe.throw(_("Seats per row must be between 1 and 40"))

	created = 0
	for row_index in range(1, rows + 1):
		label = row_label(row_index)
		for seat in range(1, seats + 1):
			if frappe.db.exists("Cubicle", {"office_floor": floor.name, "row": label, "seat_number": seat}):
				continue
			doc = frappe.get_doc(
				{
					"doctype": "Cubicle",
					"office_floor": floor.name,
					"row": label,
					"seat_number": seat,
				}
			)
			doc.insert(ignore_permissions=True)
			created += 1

	return {"created": created, "office_floor": floor.name, "rows": rows, "seats_per_row": seats}


def seed_office_floors() -> list[str]:
	if not frappe.db.table_exists("Office Floor"):
		return []

	created = []
	for floor_name, work_site in DEFAULT_OFFICE_FLOORS:
		if frappe.db.exists("Office Floor", floor_name):
			continue
		values = {"doctype": "Office Floor", "floor_name": floor_name}
		if frappe.db.exists("DocType", "Shift Location") and (
			frappe.db.exists("Shift Location", work_site)
			or frappe.db.exists("Shift Location", {"location_name": work_site})
		):
			values["work_site"] = work_site if frappe.db.exists("Shift Location", work_site) else None
			if not values["work_site"]:
				values["work_site"] = frappe.db.get_value("Shift Location", {"location_name": work_site}, "name")
		frappe.get_doc(values).insert(ignore_permissions=True)
		created.append(floor_name)
	return created
