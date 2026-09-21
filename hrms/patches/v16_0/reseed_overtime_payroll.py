# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Drop old payroll runs and rebuild them from the 80-hour pay-period overtime rule."""

import frappe


def execute():
	try:
		from hrms.import_hr_demo_data import reseed_payroll

		reseed_payroll()
	except Exception:
		frappe.log_error(title="Overtime payroll reseed failed")
		raise
