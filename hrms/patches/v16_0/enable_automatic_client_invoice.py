# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Turn on automatic client invoices and ensure billing fields exist."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint

from hrms.patches.v16_0.add_invoicing_workspace import ensure_bpo_agent_hours_item
from hrms.setup import get_custom_fields


def execute():
	create_custom_fields(get_custom_fields(), ignore_validate=True)
	frappe.reload_doc("payroll", "doctype", "payroll_settings", force=True)
	frappe.reload_doc("payroll", "doctype", "client_invoice", force=True)

	ensure_bpo_agent_hours_item()

	values = {}
	if not cint(frappe.db.get_single_value("Payroll Settings", "enable_automatic_client_invoice")):
		values["enable_automatic_client_invoice"] = 1
	if values:
		frappe.db.set_single_value("Payroll Settings", values, update_modified=False)
