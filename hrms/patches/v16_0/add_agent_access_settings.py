# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""System Settings agent IP/device locks and Employee registered device field."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import get_custom_fields


def execute():
	custom_fields = get_custom_fields()
	to_create = {
		doctype: fields
		for doctype, fields in custom_fields.items()
		if doctype in {"System Settings", "Employee"}
	}
	create_custom_fields(to_create, ignore_validate=True)
	frappe.clear_cache(doctype="System Settings")
	frappe.clear_cache(doctype="Employee")
