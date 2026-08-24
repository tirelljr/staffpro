# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Simplify Bank Account for Belize payroll source accounts."""

from __future__ import annotations

import json

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

# Party linking, IBAN, and company-account flags are not used for BPO payroll banks.
HIDDEN_BANK_ACCOUNT_FIELDS = (
	"section_break_11",
	"party_type",
	"column_break_14",
	"party",
	"account_details_section",
	"iban",
	"column_break_12",
	"is_company_account",
)

# Keep these on the first column under Account Subtype.
VISIBLE_BANK_ACCOUNT_FIELDS = (
	"bank_account_no",
	"branch_code",
	"statement_password",
)

BANK_ACCOUNT_LABELS = {
	"bank_account_no": "Bank Account Number",
	"branch_code": "Branch Location",
}

# IBAN and GL Company Account are not needed on the Bank Account list.
LIST_HIDDEN_BANK_ACCOUNT_FIELDS = (
	"iban",
	"account",
	"is_company_account",
)


def apply_bank_account_layout():
	if not frappe.db.exists("DocType", "Bank Account"):
		return

	_hide_fields("Bank Account", HIDDEN_BANK_ACCOUNT_FIELDS)
	_unhide_fields("Bank Account", VISIBLE_BANK_ACCOUNT_FIELDS)
	_relabel_fields("Bank Account", BANK_ACCOUNT_LABELS)
	_place_fields_after("Bank Account", VISIBLE_BANK_ACCOUNT_FIELDS, "account_subtype")
	_hide_from_list_view("Bank Account", LIST_HIDDEN_BANK_ACCOUNT_FIELDS)
	_show_in_list_view("Bank Account", ("bank_account_no",))
	frappe.clear_cache(doctype="Bank Account")


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


def _unhide_fields(doctype: str, fieldnames: tuple[str, ...]):
	meta = frappe.get_meta(doctype)
	for fieldname in fieldnames:
		if not meta.has_field(fieldname):
			continue
		make_property_setter(
			doctype,
			fieldname,
			"hidden",
			0,
			"Check",
			validate_fields_for_doctype=False,
		)
		frappe.db.set_value(
			"Custom Field",
			{"dt": doctype, "fieldname": fieldname},
			"hidden",
			0,
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


def _place_fields_after(doctype: str, fieldnames: tuple[str, ...], insert_after: str):
	"""Reorder standard fields via DocType field_order (insert_after only works for Custom Fields)."""
	meta = frappe.get_meta(doctype, cached=False)
	order = [df.fieldname for df in meta.get("fields") or [] if df.fieldname]
	existing = [fieldname for fieldname in fieldnames if fieldname in order]
	if not existing or insert_after not in order:
		return

	frappe.db.delete(
		"Property Setter",
		{
			"doc_type": doctype,
			"field_name": ["in", existing],
			"property": "insert_after",
		},
	)

	for fieldname in existing:
		order.remove(fieldname)
	idx = order.index(insert_after) + 1
	for offset, fieldname in enumerate(existing):
		order.insert(idx + offset, fieldname)

	make_property_setter(
		doctype,
		None,
		"field_order",
		json.dumps(order),
		"Small Text",
		for_doctype=True,
		validate_fields_for_doctype=False,
	)


def _hide_from_list_view(doctype: str, fieldnames: tuple[str, ...]):
	_set_list_view(doctype, fieldnames, 0)
	_strip_list_view_settings(doctype, fieldnames)


def _show_in_list_view(doctype: str, fieldnames: tuple[str, ...]):
	_set_list_view(doctype, fieldnames, 1)


def _set_list_view(doctype: str, fieldnames: tuple[str, ...], value: int):
	meta = frappe.get_meta(doctype)
	for fieldname in fieldnames:
		if not meta.has_field(fieldname):
			continue
		make_property_setter(
			doctype,
			fieldname,
			"in_list_view",
			value,
			"Check",
			validate_fields_for_doctype=False,
		)


def _strip_list_view_settings(doctype: str, fieldnames: tuple[str, ...]):
	if not frappe.db.exists("DocType", "List View Settings"):
		return
	if not frappe.db.exists("List View Settings", doctype):
		return

	raw = frappe.db.get_value("List View Settings", doctype, "fields")
	if not raw:
		return

	try:
		fields = json.loads(raw)
	except (TypeError, ValueError):
		return
	if not isinstance(fields, list):
		return

	hidden = set(fieldnames)

	def _fieldname(entry):
		if isinstance(entry, str):
			return entry.lstrip("`").split(".", 1)[-1]
		if isinstance(entry, dict):
			return entry.get("fieldname") or entry.get("field")
		return None

	cleaned = [entry for entry in fields if _fieldname(entry) not in hidden]
	if cleaned != fields:
		frappe.db.set_value(
			"List View Settings",
			doctype,
			"fields",
			json.dumps(cleaned),
			update_modified=False,
		)
