# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Ship default, editable Shift Location records for Staff Pro offices."""

from __future__ import annotations

import frappe

DEFAULT_SHIFT_LOCATIONS = (
	"San Ignacio - Downstairs",
	"San Ignacio - Upstairs",
	"Santa Elena",
)


def ensure_staff_pro_shift_locations() -> list[str]:
	"""Create the default work sites if they are missing.

	Records are seeded once and then left editable. Later migrate/install
	runs do not overwrite user changes to name, coordinates, or radius.
	"""
	if not frappe.db.exists("DocType", "Shift Location"):
		return []

	created = []
	for location_name in DEFAULT_SHIFT_LOCATIONS:
		if frappe.db.exists("Shift Location", location_name):
			continue
		if frappe.db.exists("Shift Location", {"location_name": location_name}):
			continue

		frappe.get_doc(
			{
				"doctype": "Shift Location",
				"location_name": location_name,
			}
		).insert(ignore_permissions=True)
		created.append(location_name)

	return created
