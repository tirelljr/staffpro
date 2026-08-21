# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""USD receivables for client invoices when the company books in another currency (BZD)."""

from __future__ import annotations

import frappe

# Keep in sync with Client Invoice CLIENT_BILLING_CURRENCY.
BILLING_CURRENCY = "USD"
MULTI_CURRENCY_SETTING = "allow_multi_currency_invoices_against_single_party_account"


def setup_usd_client_billing():
	"""Create USD Debtors, point clients at it, and allow USD invoices against company books."""
	if not frappe.db.exists("DocType", "Account"):
		return

	enable_multi_currency_party_invoices()

	for company in frappe.get_all("Company", pluck="name"):
		account = get_or_create_receivable_account(company, BILLING_CURRENCY)
		if not account:
			continue
		for customer in frappe.get_all("Customer", pluck="name"):
			prepare_customer_for_usd_invoicing(customer, company, account)


def enable_multi_currency_party_invoices():
	if not frappe.db.exists("DocType", "Accounts Settings"):
		return
	meta = frappe.get_meta("Accounts Settings")
	if not meta.has_field(MULTI_CURRENCY_SETTING):
		return
	if frappe.db.get_single_value("Accounts Settings", MULTI_CURRENCY_SETTING):
		return
	frappe.db.set_single_value("Accounts Settings", MULTI_CURRENCY_SETTING, 1, update_modified=False)


def get_invoice_receivable_account(company: str, customer: str | None, currency: str) -> str | None:
	"""Receivable whose currency matches the invoice, unless the client is already locked."""
	if not company or not currency:
		return None

	gle_currency = _get_party_gle_currency(customer, company)
	if gle_currency and gle_currency != currency:
		enable_multi_currency_party_invoices()
		return _get_existing_party_account(customer, company) or frappe.get_cached_value(
			"Company", company, "default_receivable_account"
		)

	account = get_or_create_receivable_account(company, currency)
	if not account:
		enable_multi_currency_party_invoices()
		return _get_existing_party_account(customer, company) or frappe.get_cached_value(
			"Company", company, "default_receivable_account"
		)
	if customer:
		prepare_customer_for_usd_invoicing(customer, company, account)
	return account


def prepare_customer_for_usd_invoicing(customer: str, company: str, account: str | None = None):
	if not customer or not frappe.db.exists("Customer", customer):
		return

	gle_currency = _get_party_gle_currency(customer, company)
	if gle_currency and gle_currency != BILLING_CURRENCY:
		enable_multi_currency_party_invoices()
		return

	account = account or get_or_create_receivable_account(company, BILLING_CURRENCY)
	if not account:
		enable_multi_currency_party_invoices()
		return

	_set_customer_party_account(customer, company, account)
	if frappe.get_meta("Customer").has_field("default_currency"):
		current = frappe.db.get_value("Customer", customer, "default_currency")
		if current != BILLING_CURRENCY:
			frappe.db.set_value(
				"Customer", customer, "default_currency", BILLING_CURRENCY, update_modified=False
			)
	if frappe.get_meta("Customer").has_field("billing_currency"):
		frappe.db.set_value(
			"Customer", customer, "billing_currency", BILLING_CURRENCY, update_modified=False
		)


def set_client_billing_defaults(doc, method=None):
	if doc.meta.has_field("billing_currency"):
		doc.billing_currency = BILLING_CURRENCY
	if _customer_is_locked_to_other_currency(doc):
		return
	if doc.meta.has_field("default_currency"):
		doc.default_currency = BILLING_CURRENCY
	_align_party_accounts_on_doc(doc)


def after_insert_customer(doc, method=None):
	for company in frappe.get_all("Company", pluck="name"):
		prepare_customer_for_usd_invoicing(doc.name, company)


def get_or_create_receivable_account(company: str, currency: str) -> str | None:
	if not company or not currency or not frappe.db.exists("DocType", "Account"):
		return None

	named = frappe.db.get_value(
		"Account",
		{"company": company, "account_name": f"Debtors {currency}", "is_group": 0},
		"name",
	)
	if named:
		if frappe.db.get_value("Account", named, "disabled"):
			frappe.db.set_value("Account", named, "disabled", 0, update_modified=False)
		return named

	existing = frappe.db.get_value(
		"Account",
		{
			"company": company,
			"account_type": "Receivable",
			"account_currency": currency,
			"is_group": 0,
			"disabled": 0,
		},
		"name",
	)
	if existing:
		return existing

	company_currency = frappe.get_cached_value("Company", company, "default_currency")
	default_recv = frappe.get_cached_value("Company", company, "default_receivable_account")
	if currency == company_currency:
		return default_recv

	if not default_recv or not frappe.db.exists("Account", default_recv):
		return None

	parent = frappe.db.get_value("Account", default_recv, "parent_account")
	if not parent:
		return None

	account_name = f"Debtors {currency}"
	try:
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": parent,
				"company": company,
				"account_type": "Receivable",
				"account_currency": currency,
				"root_type": "Asset",
				"report_type": "Balance Sheet",
				"is_group": 0,
			}
		)
		account.flags.ignore_permissions = True
		account.flags.ignore_mandatory = True
		account.insert(ignore_if_duplicate=True)
		return account.name
	except Exception:
		frappe.log_error(frappe.get_traceback(), "USD client receivable")
		return frappe.db.get_value(
			"Account",
			{"company": company, "account_name": account_name, "is_group": 0},
			"name",
		)


def _align_party_accounts_on_doc(doc):
	for row in doc.get("accounts") or []:
		if not row.company or not row.account:
			continue
		account_currency = frappe.get_cached_value("Account", row.account, "account_currency")
		if account_currency == BILLING_CURRENCY:
			continue
		gle_currency = _get_party_gle_currency(None if doc.is_new() else doc.name, row.company)
		if gle_currency and gle_currency != BILLING_CURRENCY:
			continue
		usd_account = get_or_create_receivable_account(row.company, BILLING_CURRENCY)
		if usd_account:
			row.account = usd_account


def _get_party_gle_currency(customer: str | None, company: str) -> str | None:
	if not customer or not company or not frappe.db.exists("DocType", "GL Entry"):
		return None
	try:
		from erpnext.accounts.party import get_party_gle_currency

		return get_party_gle_currency("Customer", customer, company)
	except Exception:
		return None


def _customer_is_locked_to_other_currency(doc) -> bool:
	if doc.is_new() or not doc.name:
		return False
	for company in frappe.get_all("Company", pluck="name"):
		gle_currency = _get_party_gle_currency(doc.name, company)
		if gle_currency and gle_currency != BILLING_CURRENCY:
			return True
	return False


def _get_existing_party_account(customer: str | None, company: str) -> str | None:
	if not customer:
		return None
	return frappe.db.get_value(
		"Party Account",
		{"parenttype": "Customer", "parent": customer, "company": company},
		"account",
	)


def _set_customer_party_account(customer: str, company: str, account: str):
	if not frappe.db.exists("DocType", "Party Account"):
		return

	existing = frappe.db.get_value(
		"Party Account",
		{"parenttype": "Customer", "parent": customer, "company": company},
		["name", "account"],
		as_dict=True,
	)
	if existing:
		if existing.account != account:
			frappe.db.set_value("Party Account", existing.name, "account", account, update_modified=False)
		return

	row = frappe.get_doc(
		{
			"doctype": "Party Account",
			"parenttype": "Customer",
			"parent": customer,
			"parentfield": "accounts",
			"company": company,
			"account": account,
		}
	)
	row.flags.ignore_permissions = True
	try:
		row.insert()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "USD client party account")
