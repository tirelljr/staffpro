# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Simplify Sales Invoice into a call-center BPO client invoice form."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

# Stock, POS, and generic ERP fields that do not belong on BPO client invoices.
HIDDEN_SALES_INVOICE_FIELDS = (
	"scan_barcode",
	"update_stock",
	"set_warehouse",
	"set_target_warehouse",
	"naming_series",
	"set_posting_time",
	"posting_time",
	"is_pos",
	"pos_profile",
	"is_return",
	"is_debit_note",
	"is_internal_customer",
	"represents_company",
	"customer_group",
	"territory",
	"campaign",
	"source",
	"has_purchase_order",
	"po_no",
	"po_date",
	"project",
	"cost_center",
	"incoterm",
	"named_place",
	"shipping_rule",
	"tax_id",
	"tax_category",
	"taxes_and_charges",
	"shipping_address_name",
	"dispatch_address_name",
	"company_address",
	"contact_person",
	"customer_address",
	"address_display",
	"shipping_address",
	"company_address_display",
	"contact_display",
	"contact_mobile",
	"contact_email",
	"exempt_from_sales_tax",
	"taxes",
	"taxes_section",
	"section_break_40",
	"section_break_43",
	"section_break_vacb",
	"total_advance",
	"allocate_advances_automatically",
	"advances",
	"use_company_roundoff_cost_center",
	"ignore_pricing_rule",
	"pricing_rules",
	"additional_discount_percentage",
	"discount_amount",
	"apply_discount_on",
	"is_cash_or_non_trade_discount",
	"write_off_amount",
	"write_off_outstanding_amount_automatically",
	"loyalty_points",
	"loyalty_redemption",
	"redeem_loyalty_points",
	"subscription",
	"timesheets",
	"packed_items",
	"product_bundle",
	"transporter",
	"driver",
	"lr_no",
	"lr_date",
	"vehicle_no",
	"is_opening",
	"group_same_items",
	"language",
	"select_print_heading",
	"from_date",
	"to_date",
	"auto_repeat",
	"more_info",
	"more_info_tab",
	"address_and_contact_tab",
)

HIDDEN_SALES_INVOICE_ITEM_FIELDS = (
	"warehouse",
	"target_warehouse",
	"from_warehouse",
	"actual_qty",
	"received_qty",
	"rejected_qty",
	"stock_uom",
	"conversion_factor",
	"stock_qty",
	"weight_per_unit",
	"total_weight",
	"incoming_rate",
	"allow_zero_valuation_rate",
	"serial_no",
	"serial_and_batch_bundle",
	"batch_no",
	"use_serial_batch_fields",
	"quality_inspection",
	"item_group",
	"brand",
	"image",
	"barcode",
	"manufacturer",
	"manufacturer_part_no",
	"delivered_by_supplier",
	"supplier",
	"is_fixed_asset",
	"asset",
	"grant_commission",
	"enable_deferred_revenue",
	"deferred_revenue_account",
	"service_stop_date",
	"service_start_date",
	"service_end_date",
	"sales_order",
	"so_detail",
	"delivery_note",
	"dn_detail",
	"quotation",
	"quotation_item",
	"material_request",
	"material_request_item",
	"page_break",
	"item_tax_template",
	"item_tax_rate",
	"gst_hsn_code",
	"is_nil_exempt",
	"is_non_gst",
	"expense_account",
	"cost_center",
	"project",
	"discount_percentage",
	"discount_amount",
	"base_rate",
	"base_amount",
	"net_rate",
	"net_amount",
	"income_account",
)

SALES_INVOICE_LABELS = {
	"customer": "Client",
	"customer_name": "Client Name",
	"items": "Agent Hours",
	"items_section": "Agent Hours",
}

SALES_INVOICE_ITEM_LABELS = {
	"item_code": "Service",
	"item_name": "Description",
	"qty": "Hours",
	"uom": "Unit",
	"rate": "Billing Rate",
}


def apply_bpo_sales_invoice_layout():
	if not frappe.db.exists("DocType", "Sales Invoice"):
		return

	_hide_fields("Sales Invoice", HIDDEN_SALES_INVOICE_FIELDS)
	_relabel_fields("Sales Invoice", SALES_INVOICE_LABELS)

	if frappe.db.exists("DocType", "Sales Invoice Item"):
		_hide_fields("Sales Invoice Item", HIDDEN_SALES_INVOICE_ITEM_FIELDS)
		_relabel_fields("Sales Invoice Item", SALES_INVOICE_ITEM_LABELS)

	frappe.clear_cache(doctype="Sales Invoice")
	if frappe.db.exists("DocType", "Sales Invoice Item"):
		frappe.clear_cache(doctype="Sales Invoice Item")


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
