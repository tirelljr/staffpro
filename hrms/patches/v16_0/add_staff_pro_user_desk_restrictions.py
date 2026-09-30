# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import get_custom_fields


def execute():
	user_fields = get_custom_fields().get("User")
	if not user_fields:
		return
	create_custom_fields({"User": user_fields}, ignore_validate=True, update=True)
	frappe.clear_cache(doctype="User")
