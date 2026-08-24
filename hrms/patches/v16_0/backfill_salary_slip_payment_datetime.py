# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Stamp payment date and time on pay stubs that are already Paid."""

import frappe


def execute():
	if not frappe.db.has_column("Salary Slip", "payment_date"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabSalary Slip`
		SET
			payment_date = DATE(`modified`),
			payment_time = TIME(`modified`)
		WHERE payment_status = 'Paid'
			AND (payment_date IS NULL OR payment_date = '')
		"""
	)
