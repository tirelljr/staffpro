# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Simplify Customer into a call-center BPO client form."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

# Retail, tax, and generic ERP fields that do not belong on BPO clients.
HIDDEN_CUSTOMER_FIELDS = (
	"naming_series",
	"salutation",
	"gender",
	"default_bank_account",
	"lead_name",
	"opportunity_name",
	"prospect_name",
	"tax_id",
	"tax_category",
	"tax_withholding_category",
	"gst_category",
	"gstin",
	"pan",
	"default_price_list",
	"customer_pos_id",
	"is_internal_customer",
	"represents_company",
	"market_segment",
	"industry",
	"website",
	"language",
	"territory",
	"default_sales_partner",
	"default_commission_rate",
	"sales_team",
	"sales_team_section",
	"sales_team_tab",
	"loyalty_program",
	"loyalty_program_tier",
	"portal_users",
	"portal_users_tab",
	"so_required",
	"dn_required",
	"is_frozen",
	"companies",
	"credit_limits",
	"credit_limits_section",
	"tax_tab",
	"settings_tab",
	"more_info",
	"more_info_tab",
)

CUSTOMER_LABELS = {
	"customer_name": "Client Name",
	"customer_type": "Client Type",
	"customer_group": "Client Group",
	"account_manager": "Account Manager",
	"customer_details": "Notes",
	"customer_primary_contact": "Primary Contact",
	"customer_primary_address": "Primary Address",
	"payment_terms": "Payment Terms",
	"default_currency": "Currency",
	"default_billing_rate": "Hourly Billing Rate",
	"disabled": "Disabled",
	"alias": "Short Name",
}


def apply_bpo_customer_layout():
	if not frappe.db.exists("DocType", "Customer"):
		return

	_hide_fields("Customer", HIDDEN_CUSTOMER_FIELDS)
	_relabel_fields("Customer", CUSTOMER_LABELS)
	_sync_custom_field_labels("Customer", CUSTOMER_LABELS)
	_set_default("Customer", "customer_type", "Company")
	_set_default("Customer", "default_currency", "USD", property_type="Link")
	frappe.clear_cache(doctype="Customer")


def _hide_fields(doctype: str, fieldnames: tuple[str, ...]):
	meta = frappe.get_meta(doctype)
	for fieldname in fieldnames:
		if not meta.has_field(fieldname):
			continue
		make_property_setter(
			doctype,
			fieldname,
			"hidden",
			1,
			"Check",
			validate_fields_for_doctype=False,
		)
		frappe.db.set_value(
			"Custom Field",
			{"dt": doctype, "fieldname": fieldname},
			"hidden",
			1,
			update_modified=False,
		)


def _relabel_fields(doctype: str, labels: dict[str, str]):
	meta = frappe.get_meta(doctype)
	for fieldname, label in labels.items():
		if not meta.has_field(fieldname):
			continue
		make_property_setter(
			doctype,
			fieldname,
			"label",
			label,
			"Data",
			validate_fields_for_doctype=False,
		)


def _sync_custom_field_labels(doctype: str, labels: dict[str, str]):
	for fieldname, label in labels.items():
		name = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": fieldname}, "name")
		if not name:
			continue
		frappe.db.set_value("Custom Field", name, "label", label, update_modified=False)


def _set_default(doctype: str, fieldname: str, value: str, property_type: str = "Select"):
	meta = frappe.get_meta(doctype)
	if not meta.has_field(fieldname):
		return
	make_property_setter(
		doctype,
		fieldname,
		"default",
		value,
		property_type,
		validate_fields_for_doctype=False,
	)
