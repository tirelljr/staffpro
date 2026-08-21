# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Hide Cost Center from BPO forms. Journals still use the company default."""

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from hrms.patches.v16_0.apply_bpo_sidebar_labels import execute as sync_sidebars

CUSTOM_FIELDS = (
	("Employee", "payroll_cost_center"),
	("Department", "payroll_cost_center"),
)


def execute():
	hide_cost_center_fields()
	sync_sidebars()


def hide_cost_center_fields():
	for doctype, fieldname in CUSTOM_FIELDS:
		if not frappe.db.exists("DocType", doctype):
			continue

		meta = frappe.get_meta(doctype)
		if not meta.has_field(fieldname):
			continue

		make_property_setter(
			doctype,
			fieldname,
			"hidden",
			1,
			"Check",
			validate_fields_for_doctype=False,
		)
		frappe.db.set_value(
			"Custom Field",
			{"dt": doctype, "fieldname": fieldname},
			"hidden",
			1,
			update_modified=False,
		)
		frappe.clear_cache(doctype=doctype)
