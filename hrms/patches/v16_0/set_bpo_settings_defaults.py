# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""BPO defaults: attendance payroll, Full Name employees, 40 hours, birthday reminders."""

import frappe

from hrms.branding import hide_system_settings_app_tab
from hrms.patches.v16_0.apply_bpo_sidebar_labels import execute as sync_sidebars


def execute():
	hide_system_settings_app_tab()
	_set_payroll_defaults()
	_set_hr_defaults()
	sync_sidebars()


def _set_payroll_defaults():
	if not frappe.db.exists("DocType", "Payroll Settings"):
		return

	frappe.reload_doc("payroll", "doctype", "payroll_settings", force=True)
	values = {"payroll_based_on": "Attendance"}
	if not frappe.db.get_single_value("Payroll Settings", "consider_unmarked_attendance_as"):
		values["consider_unmarked_attendance_as"] = "Present"
	frappe.db.set_single_value("Payroll Settings", values, update_modified=False)


def _set_hr_defaults():
	if not frappe.db.exists("DocType", "HR Settings"):
		return

	frappe.reload_doc("hr", "doctype", "hr_settings", force=True)
	frappe.db.set_single_value(
		"HR Settings",
		{
			"emp_created_by": "Full Name",
			"standard_working_hours": 40,
			"send_birthday_reminders": 1,
		},
		update_modified=False,
	)
