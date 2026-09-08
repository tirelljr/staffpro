# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Add Checking/Savings on Employee so bank payroll can mark SAV."""

import frappe

from hrms.hr.bpo_employee_labels import apply_belize_employee_bank_fields
from hrms.import_hr_demo_data import seed_demo_employee_banks


def execute():
	apply_belize_employee_bank_fields()
	if frappe.db.exists("DocType", "Employee"):
		frappe.clear_cache(doctype="Employee")
	seed_demo_employee_banks()
