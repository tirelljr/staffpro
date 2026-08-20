# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Set unique date of birth / date of joining on demo employees and refresh today's clocks."""

import frappe


def execute():
	try:
		from hrms.import_hr_demo_data import seed_demo_employee_dates, seed_week_hours

		seed_demo_employee_dates()
		seed_week_hours()
	except Exception:
		frappe.log_error(title="Demo employee dates seed failed")
