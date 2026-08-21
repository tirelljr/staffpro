# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Restyle Customer and Sales Invoice as call-center BPO client forms."""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.payroll.bpo_customer import apply_bpo_customer_layout
from hrms.payroll.bpo_sales_invoice import apply_bpo_sales_invoice_layout
from hrms.setup import get_custom_fields


def execute():
	custom_fields = get_custom_fields()
	to_create = {
		doctype: fields
		for doctype, fields in custom_fields.items()
		if doctype in ("Customer", "Sales Invoice")
	}
	if to_create:
		create_custom_fields(to_create, ignore_validate=True)

	apply_bpo_customer_layout()
	apply_bpo_sales_invoice_layout()
