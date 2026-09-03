# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Store Agent Hourly on Salary Structure Assignment as the employee's hourly rate."""

import frappe


def execute():
	if not frappe.db.has_column("Salary Structure Assignment", "ctc"):
		return
	if not frappe.db.has_column("Employee", "ctc"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabSalary Structure Assignment` ssa
		INNER JOIN `tabEmployee` emp ON emp.name = ssa.employee
		SET ssa.ctc = IFNULL(emp.ctc, 0)
		"""
	)
