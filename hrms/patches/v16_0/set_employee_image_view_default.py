# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	if not frappe.db.exists("DocType", "Employee"):
		return

	make_property_setter(
		"Employee",
		None,
		"default_view",
		"Image",
		"Select",
		for_doctype=True,
		validate_fields_for_doctype=False,
	)
	frappe.db.set_value("DocType", "Employee", "default_view", "Image", update_modified=False)
	frappe.clear_cache(doctype="Employee")
