# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Give each demo employee a Belize bank and account number."""

import frappe


def execute():
	try:
		from hrms.import_hr_demo_data import seed_demo_employee_banks

		seed_demo_employee_banks()
	except Exception:
		frappe.log_error(title="Demo employee bank seed failed")
