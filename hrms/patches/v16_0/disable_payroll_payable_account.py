# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Disable Payroll Payable (e.g. 2120) and hide related fields for direct Bank/Cash payroll."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	_disable_payroll_payable_accounts()
	_clear_company_defaults()
	_hide_company_custom_field()
	_hide_cheque_salary_mode()


def _disable_payroll_payable_accounts():
	names = set()

	for account in frappe.get_all(
		"Account",
		filters={"is_group": 0, "account_name": ("like", "%Payroll Payable%")},
		pluck="name",
	):
		names.add(account)

	for account in frappe.get_all(
		"Account",
		filters={"is_group": 0, "account_number": "2120"},
		fields=["name", "account_name"],
	):
		if "payroll payable" in (account.account_name or "").lower():
			names.add(account.name)

	for name in names:
		frappe.db.set_value("Account", name, "disabled", 1, update_modified=False)


def _clear_company_defaults():
	if not frappe.db.exists("DocType", "Company"):
		return
	if not frappe.db.has_column("Company", "default_payroll_payable_account"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabCompany`
		SET default_payroll_payable_account = NULL
		WHERE IFNULL(default_payroll_payable_account, '') != ''
		"""
	)


def _hide_company_custom_field():
	existing = frappe.db.exists(
		"Custom Field", {"dt": "Company", "fieldname": "default_payroll_payable_account"}
	)
	if existing:
		frappe.db.set_value("Custom Field", existing, "hidden", 1, update_modified=False)
	else:
		create_custom_fields(
			{
				"Company": [
					{
						"depends_on": "eval:!doc.__islocal",
						"fieldname": "default_payroll_payable_account",
						"fieldtype": "Link",
						"hidden": 1,
						"ignore_user_permissions": 1,
						"label": "Default Payroll Payable Account",
						"no_copy": 1,
						"options": "Account",
						"insert_after": "column_break_10",
					}
				]
			},
			ignore_validate=True,
			update=True,
		)


def _hide_cheque_salary_mode():
	"""Employee salary_mode: Bank or Cash only (hide Cheque)."""
	if not frappe.db.exists("DocField", {"parent": "Employee", "fieldname": "salary_mode"}):
		return

	frappe.make_property_setter(
		{
			"doctype": "Employee",
			"doctype_or_field": "DocField",
			"fieldname": "salary_mode",
			"property": "options",
			"value": "\nBank\nCash",
			"property_type": "Text",
		},
		validate_fields_for_doctype=False,
		is_system_generated=True,
	)
