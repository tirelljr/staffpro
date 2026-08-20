# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Bill clients in USD, separately from agent payroll currency."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.payroll.doctype.client_invoice.client_invoice import CLIENT_BILLING_CURRENCY
from hrms.setup import get_custom_fields


def execute():
	create_custom_fields(get_custom_fields(), ignore_validate=True)

	if frappe.db.has_column("Employee", "billing_currency"):
		frappe.db.sql(
			"""
			UPDATE `tabEmployee`
			SET billing_currency = %s
			WHERE IFNULL(billing_currency, '') = ''
			""",
			CLIENT_BILLING_CURRENCY,
		)

	if frappe.db.has_column("Customer", "billing_currency"):
		frappe.db.sql(
			"""
			UPDATE `tabCustomer`
			SET billing_currency = %s
			WHERE IFNULL(billing_currency, '') = ''
			""",
			CLIENT_BILLING_CURRENCY,
		)

	if frappe.db.exists("DocType", "Client Invoice"):
		frappe.db.sql(
			"""
			UPDATE `tabClient Invoice`
			SET currency = %s
			WHERE docstatus = 0 AND IFNULL(currency, '') != %s
			""",
			(CLIENT_BILLING_CURRENCY, CLIENT_BILLING_CURRENCY),
		)

	frappe.clear_cache(doctype="Employee")
	frappe.clear_cache(doctype="Customer")
	frappe.clear_cache(doctype="Client Invoice")
