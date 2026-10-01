# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Remove seeded demo agents and linked payroll records."""

import frappe


def execute():
	try:
		from hrms.hr.employee_cleanup import delete_demo_employees

		delete_demo_employees()
	except Exception:
		frappe.log_error(title="Demo employee cleanup failed")
		raise
