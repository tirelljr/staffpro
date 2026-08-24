# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Relabel Employee salary fields for BPO hourly pay (not India CTC/PAN)."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

EMPLOYEE_FIELD_LABELS = {
	"ctc": "Agent Hourly",
	"pan_number": "Tax Number",
	"designation": "Role",
	"grade": "Campaign",
}

EMPLOYEE_FIELD_DEFAULTS = {
	"salary_currency": "BZD",
	"salary_mode": "Bank",
}

BELIZE_EMPLOYEE_BANKS = (
	"Heritage Bank",
	"Belize Bank",
	"Atlantic Bank",
	"National Bank of Belize",
)

OTHER_DOCTYPE_FIELD_LABELS = {
	"Salary Structure Assignment": {"ctc": "Agent Hourly", "grade": "Campaign"},
	"Salary Slip": {
		"ctc": "Agent Hourly",
		"bank_name": "Paid To Bank",
		"bank_account_no": "Paid To Account No",
	},
	"Payroll Entry": {"grade": "Campaign", "bank_account": "Pay From Bank Account"},
	"Employee Promotion": {
		"current_ctc": "Current Agent Hourly",
		"revised_ctc": "Revised Agent Hourly",
	},
	"Designation": {"designation_name": "Role"},
}


def apply_bpo_employee_labels():
	_relabel_fields("Employee", EMPLOYEE_FIELD_LABELS)
	_sync_custom_field_labels("Employee", EMPLOYEE_FIELD_LABELS)
	apply_belize_employee_bank_fields()
	apply_employee_salary_defaults()
	apply_payroll_payment_layout()

	for doctype, labels in OTHER_DOCTYPE_FIELD_LABELS.items():
		_relabel_fields(doctype, labels)

	for doctype in ["Employee", *OTHER_DOCTYPE_FIELD_LABELS]:
		if frappe.db.exists("DocType", doctype):
			frappe.clear_cache(doctype=doctype)


def apply_employee_salary_defaults():
	if not frappe.db.exists("DocType", "Employee"):
		return

	meta = frappe.get_meta("Employee")
	for fieldname, value in EMPLOYEE_FIELD_DEFAULTS.items():
		if not meta.has_field(fieldname):
			continue
		make_property_setter(
			"Employee",
			fieldname,
			"default",
			value,
			"Data",
			validate_fields_for_doctype=False,
		)

	if meta.has_field("ctc"):
		make_property_setter(
			"Employee",
			"ctc",
			"description",
			"Hourly pay in salary currency. After setting it, you can apply the same rate to other agents, a branch, campaign, or team.",
			"Small Text",
			validate_fields_for_doctype=False,
		)


def apply_payroll_payment_layout():
	if not frappe.db.exists("DocType", "Payroll Entry"):
		return

	meta = frappe.get_meta("Payroll Entry")
	hidden_fields = {
		"payment_account": "Check",
		"overtime_step": "Check",
		"accounting_dimensions_tab": "Check",
		"accounting_dimensions_section": "Check",
	}
	for fieldname, fieldtype in hidden_fields.items():
		if not meta.has_field(fieldname):
			continue
		make_property_setter(
			"Payroll Entry",
			fieldname,
			"hidden",
			1,
			fieldtype,
			validate_fields_for_doctype=False,
		)

	if meta.has_field("bank_account"):
		make_property_setter(
			"Payroll Entry",
			"bank_account",
			"description",
			"Company bank account to send agent payments from.",
			"Small Text",
			validate_fields_for_doctype=False,
		)


def apply_belize_employee_bank_fields():
	if not frappe.db.exists("DocType", "Employee"):
		return

	meta = frappe.get_meta("Employee")
	if meta.has_field("iban"):
		make_property_setter(
			"Employee",
			"iban",
			"hidden",
			1,
			"Check",
			validate_fields_for_doctype=False,
		)
		frappe.db.set_value(
			"Custom Field",
			{"dt": "Employee", "fieldname": "iban"},
			"hidden",
			1,
			update_modified=False,
		)

	if not meta.has_field("bank_name"):
		return

	make_property_setter(
		"Employee",
		"bank_name",
		"fieldtype",
		"Select",
		"Select",
		validate_fields_for_doctype=False,
	)
	make_property_setter(
		"Employee",
		"bank_name",
		"options",
		"\n" + "\n".join(BELIZE_EMPLOYEE_BANKS),
		"Text",
		validate_fields_for_doctype=False,
	)


def _relabel_fields(doctype: str, labels: dict[str, str]):
	if not frappe.db.exists("DocType", doctype):
		return

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
