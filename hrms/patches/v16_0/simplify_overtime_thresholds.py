"""Use one pay-period overtime threshold and flatten overtime navigation."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars
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
	if threshold in (None, "", 0):
		frappe.db.set_single_value("HR Settings", "overtime_threshold_hours", 80)

	multiplier = frappe.db.get_single_value("HR Settings", "overtime_pay_multiplier")
	if multiplier in (None, "", 0):
		frappe.db.set_single_value("HR Settings", "overtime_pay_multiplier", 1.5)

	sync_staff_pro_sidebars()
