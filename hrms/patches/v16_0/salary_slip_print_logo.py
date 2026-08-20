# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	frappe.reload_doc("payroll", "doctype", "salary_slip")
	for print_format in (
		"salary_slip_standard",
		"salary_slip_with_year_to_date",
		"salary_slip_based_on_timesheet",
	):
		frappe.reload_doc("payroll", "print_format", print_format, force=True)

	if not frappe.db.exists("DocType", "Salary Slip"):
		return

	meta = frappe.get_meta("Salary Slip")
	for fieldname in ("total_in_words", "base_total_in_words", "section_break_55", "column_break_69"):
		if not meta.has_field(fieldname):
			continue
		make_property_setter(
			"Salary Slip",
			fieldname,
			"hidden",
			1,
			"Check",
			validate_fields_for_doctype=False,
		)
		make_property_setter(
			"Salary Slip",
			fieldname,
			"print_hide",
			1,
			"Check",
			validate_fields_for_doctype=False,
		)

	for fieldname in ("year_to_date", "month_to_date"):
		if not meta.has_field(fieldname):
			continue
		make_property_setter(
			"Salary Slip",
			fieldname,
			"description",
			"",
			"Small Text",
			validate_fields_for_doctype=False,
		)

	frappe.clear_cache(doctype="Salary Slip")
