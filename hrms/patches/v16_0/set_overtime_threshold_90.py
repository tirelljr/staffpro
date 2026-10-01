"""Move the Belize overtime default from 80 hours to 90 hours."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import flt

from hrms.setup import get_custom_fields


def execute():
	employee_fields = [
		field
		for field in get_custom_fields().get("Employee", [])
		if field.get("fieldname") == "overtime_threshold_hours"
	]
	if employee_fields:
		create_custom_fields({"Employee": employee_fields}, ignore_validate=True)

	threshold = frappe.db.get_single_value("HR Settings", "overtime_threshold_hours")
	if threshold in (None, "", 0) or flt(threshold) == 80:
		frappe.db.set_single_value("HR Settings", "overtime_threshold_hours", 90)

	if frappe.get_meta("Employee").has_field("overtime_threshold_hours"):
		frappe.db.sql(
			"""
			UPDATE `tabEmployee`
			SET overtime_threshold_hours = 90
			WHERE overtime_threshold_hours IS NULL
				OR overtime_threshold_hours = 0
				OR overtime_threshold_hours = 80
			"""
		)
