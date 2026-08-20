# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Restyle Sales Invoice as a call-center BPO client invoice."""

from hrms.payroll.bpo_sales_invoice import apply_bpo_sales_invoice_layout


def execute():
	apply_bpo_sales_invoice_layout()
