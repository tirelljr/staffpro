# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.hr.belize_holidays import add_belize_holidays_to_list


def _holiday_list_pay_fields() -> dict:
	return {
		"Holiday List": [
			{
				"fieldname": "holiday_pay_section",
				"fieldtype": "Section Break",
				"label": _("Holiday Pay"),
				"insert_after": "weekly_off",
			},
			{
				"fieldname": "pay_time_and_a_half",
				"fieldtype": "Check",
				"label": _("Pay Time and a Half"),
				"insert_after": "holiday_pay_section",
				"description": _("Public holidays only. Mutually exclusive with Double Time."),
			},
			{
				"fieldname": "column_break_holiday_pay",
				"fieldtype": "Column Break",
				"insert_after": "pay_time_and_a_half",
			},
			{
				"fieldname": "pay_double_time",
				"fieldtype": "Check",
				"label": _("Pay Double Time"),
				"insert_after": "column_break_holiday_pay",
				"description": _("Public holidays only. Mutually exclusive with Time and a Half."),
			},
		]
	}


def execute():
	create_custom_fields(_holiday_list_pay_fields(), update=True)

	list_name = "Staff Pro Holiday List"
	if frappe.db.exists("Holiday List", list_name):
		add_belize_holidays_to_list(list_name)
