# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from hrms.setup import HIDDEN_EMPLOYEE_FIELDS


def execute():
	if not frappe.db.exists("DocType", "Employee"):
		return

	meta = frappe.get_meta("Employee")
	for fieldname in HIDDEN_EMPLOYEE_FIELDS:
		if not meta.has_field(fieldname):
			continue

		make_property_setter(
			"Employee",
			fieldname,
			"hidden",
			1,
			"Check",
			validate_fields_for_doctype=False,
		)
		frappe.db.set_value(
			"Custom Field",
			{"dt": "Employee", "fieldname": fieldname},
			"hidden",
			1,
			update_modified=False,
		)

	frappe.clear_cache(doctype="Employee")
