# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Add Employee Default IPv4 and apply the office clock-in IP to agents."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.hr.agent_access import apply_office_ipv4_defaults
from hrms.setup import get_custom_fields


def execute():
	custom_fields = get_custom_fields()
	to_create = {doctype: fields for doctype, fields in custom_fields.items() if doctype == "Employee"}
	create_custom_fields(to_create, ignore_validate=True)
	frappe.clear_cache(doctype="Employee")
	if frappe.get_meta("System Settings").has_field("office_clockin_ipv4"):
		apply_office_ipv4_defaults()
