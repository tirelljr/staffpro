# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

IPV4_PATTERN = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")


class Cubicle(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		device_id: DF.Data | None
		employee: DF.Link | None
		employee_name: DF.Data | None
		ip_address: DF.Data | None
		office_floor: DF.Link
		row: DF.Data
		seat_number: DF.Int
		status: DF.Literal["Vacant", "Occupied"]
	# end: auto-generated types

	def autoname(self):
		self.name = cubicle_name(self.office_floor, self.row, self.seat_number)

	def validate(self):
		self.row = (self.row or "").strip().upper()
		if not self.row:
			frappe.throw(_("Row is required"))
		if cint(self.seat_number) < 1:
			frappe.throw(_("Seat Number must be at least 1"))
		self.device_id = (self.device_id or "").strip() or None
		self.ip_address = (self.ip_address or "").strip() or None
		self._validate_ip()
		self.status = "Occupied" if self.employee else "Vacant"
		if not self.employee:
			self.employee_name = None
		self._ensure_unique_seat()
		self._ensure_unique_employee()

	def _validate_ip(self):
		if not self.ip_address:
			return
		if not IPV4_PATTERN.match(self.ip_address):
			frappe.throw(_("Enter a valid IPv4 address"))
		if any(not (0 <= cint(part) <= 255) for part in self.ip_address.split(".")):
			frappe.throw(_("Enter a valid IPv4 address"))

	def _ensure_unique_seat(self):
		filters = {
			"office_floor": self.office_floor,
			"row": self.row,
			"seat_number": self.seat_number,
		}
		if not self.is_new():
			filters["name"] = ["!=", self.name]
		if frappe.db.exists("Cubicle", filters):
			frappe.throw(
				_("Seat {0} in row {1} is already used on {2}").format(
					self.seat_number, self.row, self.office_floor
				)
			)

	def _ensure_unique_employee(self):
		if not self.employee:
			return
		filters = {"employee": self.employee}
		if not self.is_new():
			filters["name"] = ["!=", self.name]
		existing = frappe.db.get_value("Cubicle", filters, ["name", "office_floor", "row", "seat_number"], as_dict=True)
		if existing:
			frappe.throw(
				_("{0} already sits at {1} row {2} seat {3}").format(
					self.employee_name or self.employee,
					existing.office_floor,
					existing.row,
					existing.seat_number,
				)
			)


def cubicle_name(office_floor: str, row: str, seat_number: int | str) -> str:
	return f"{office_floor}-{str(row or '').strip().upper()}-{cint(seat_number):02d}"
