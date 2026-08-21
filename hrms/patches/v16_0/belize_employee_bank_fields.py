# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Limit Employee bank_name to Belize banks and hide IBAN."""

import frappe

from hrms.hr.bpo_employee_labels import apply_belize_employee_bank_fields


def execute():
	apply_belize_employee_bank_fields()
	if frappe.db.exists("DocType", "Employee"):
		frappe.clear_cache(doctype="Employee")
