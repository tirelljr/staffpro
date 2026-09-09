# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Lock Employee salary currency to BZD."""

import frappe

from hrms.hr.bpo_employee_labels import lock_employee_salary_currency


def execute():
	lock_employee_salary_currency()
	if frappe.db.exists("DocType", "Employee"):
		frappe.clear_cache(doctype="Employee")
