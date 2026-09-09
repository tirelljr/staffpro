# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Employee user bonus fields and Attendance Bonus auto-calculate rules."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.payroll.doctype.bonus_type.bonus_type import (
	configure_attendance_bonus_defaults,
	seed_bonus_types,
)
from hrms.setup import get_custom_fields


def execute():
	create_custom_fields(get_custom_fields(), ignore_validate=True)
	if frappe.db.table_exists("Bonus Type"):
		seed_bonus_types()
		configure_attendance_bonus_defaults()
	frappe.clear_cache(doctype="Employee")
	if frappe.db.exists("DocType", "Bonus Type"):
		frappe.clear_cache(doctype="Bonus Type")
	if frappe.db.exists("DocType", "Additional Salary"):
		frappe.clear_cache(doctype="Additional Salary")
