# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Make employee user bonus a settable attendance plan for BPO agents."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.payroll.doctype.bonus_type.bonus_type import (
	configure_attendance_bonus_defaults,
	ensure_attendance_deduction_component,
	seed_bonus_types,
)
from hrms.setup import get_custom_fields


def execute():
	create_custom_fields(get_custom_fields(), ignore_validate=True, update=True)

	if frappe.db.exists("Custom Field", "Employee-user_bonus"):
		frappe.db.set_value("Custom Field", "Employee-user_bonus", "read_only", 0)
		frappe.db.set_value(
			"Custom Field",
			"Employee-user_bonus",
			"description",
			"Amount this agent can earn, for example 500. Paid over the months below if they keep the attendance target.",
		)

	if frappe.db.has_column("Employee", "user_bonus_period_months"):
		frappe.db.sql(
			"""
			UPDATE `tabEmployee`
			SET user_bonus_period_months = 3
			WHERE IFNULL(user_bonus_period_months, 0) = 0
			"""
		)
	if frappe.db.has_column("Employee", "user_bonus_attendance_target"):
		frappe.db.sql(
			"""
			UPDATE `tabEmployee`
			SET user_bonus_attendance_target = 90
			WHERE IFNULL(user_bonus_attendance_target, 0) = 0
			"""
		)
	if frappe.db.has_column("Employee", "user_bonus_if_below"):
		frappe.db.sql(
			"""
			UPDATE `tabEmployee`
			SET user_bonus_if_below = 'No Bonus'
			WHERE IFNULL(user_bonus_if_below, '') = ''
			"""
		)

	if frappe.db.table_exists("Bonus Type"):
		seed_bonus_types()
		configure_attendance_bonus_defaults()
	ensure_attendance_deduction_component()

	frappe.clear_cache(doctype="Employee")
	if frappe.db.exists("DocType", "Bonus Type"):
		frappe.clear_cache(doctype="Bonus Type")
	if frappe.db.exists("DocType", "Additional Salary"):
		frappe.clear_cache(doctype="Additional Salary")
