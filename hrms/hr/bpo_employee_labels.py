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
	"user_id": "Username",
}

STAFF_PRO_SALARY_CURRENCY = "BZD"

EMPLOYEE_FIELD_DEFAULTS = {
	"salary_currency": STAFF_PRO_SALARY_CURRENCY,
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
			"Hourly pay in salary currency. Use Change Hourly Rate to update this agent, or apply the same rate to other agents, a branch, campaign, or team.",
			"Small Text",
			validate_fields_for_doctype=False,
		)

	lock_employee_salary_currency()
	apply_employee_username_field()
	enable_username_login()


def lock_employee_salary_currency():
	"""Agent pay is always Belize dollars. Keep the field visible but not editable."""
	if not frappe.db.exists("DocType", "Employee"):
		return

	meta = frappe.get_meta("Employee")
	if not meta.has_field("salary_currency"):
		return

	make_property_setter(
		"Employee",
		"salary_currency",
		"read_only",
		1,
		"Check",
		validate_fields_for_doctype=False,
	)
	make_property_setter(
		"Employee",
		"salary_currency",
		"description",
		"Agent salary is always Belize dollars (BZD).",
		"Small Text",
		validate_fields_for_doctype=False,
	)

	if not frappe.db.has_column("Employee", "salary_currency"):
		return
	if not frappe.db.exists("Currency", STAFF_PRO_SALARY_CURRENCY):
		return

	frappe.db.sql(
		"""
		UPDATE `tabEmployee`
		SET salary_currency = %(currency)s
		WHERE IFNULL(salary_currency, '') != %(currency)s
		""",
		{"currency": STAFF_PRO_SALARY_CURRENCY},
	)


def enable_username_login():
	"""Frappe only accepts User.username at login when this System Setting is on."""
	if not frappe.db.exists("DocType", "System Settings"):
		return
	frappe.db.set_single_value("System Settings", "allow_login_using_user_name", 1)


def apply_employee_username_field():
	if not frappe.db.exists("DocType", "Employee"):
		return

	meta = frappe.get_meta("Employee")
	if not meta.has_field("user_id"):
		return

	make_property_setter(
		"Employee",
		"user_id",
		"label",
		"Username",
		"Data",
		validate_fields_for_doctype=False,
	)
	make_property_setter(
		"Employee",
		"user_id",
		"fieldtype",
		"Data",
		"Data",
		validate_fields_for_doctype=False,
	)
	make_property_setter(
		"Employee",
		"user_id",
		"options",
		"",
		"Small Text",
		validate_fields_for_doctype=False,
	)
	make_property_setter(
		"Employee",
		"user_id",
		"description",
		"",
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

	_ensure_employee_bank_account_type()

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


def _ensure_employee_bank_account_type():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if not frappe.db.exists("DocType", "Employee"):
		return
	if frappe.db.exists("Custom Field", {"dt": "Employee", "fieldname": "bank_account_type"}):
		return
	if frappe.get_meta("Employee").has_field("bank_account_type"):
		return

	create_custom_field(
		"Employee",
		{
			"fieldname": "bank_account_type",
			"label": "Bank Account Type",
			"fieldtype": "Select",
			"options": "\nChecking\nSavings",
			"insert_after": "bank_ac_no",
			"default": "Checking",
		},
		ignore_validate=True,
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
