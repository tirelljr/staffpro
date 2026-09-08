# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Belize banks the BPO wires payroll from, and company Bank Account records for each."""

from __future__ import annotations

import frappe

from hrms.hr.bpo_employee_labels import BELIZE_EMPLOYEE_BANKS

BELIZE_BANKS = BELIZE_EMPLOYEE_BANKS

BELIZE_BANK_CODES = {
	"Heritage Bank": "HBL",
	"Belize Bank": "BBL",
	"Atlantic Bank": "ABL",
	"National Bank of Belize": "NBB",
}

COMPANY_BANK_ACCOUNT_NOS = {
	"Heritage Bank": "1001002847",
	"Belize Bank": "2002003948",
	"Atlantic Bank": "3003004859",
	"National Bank of Belize": "4004005760",
}


def bank_code_for(bank_name: str | None) -> str:
	"""Three-letter remittance code used on the bank payroll sheet."""
	if not bank_name:
		return ""
	if bank_name in BELIZE_BANK_CODES:
		return BELIZE_BANK_CODES[bank_name]
	words = [part for part in str(bank_name).split() if part]
	if not words:
		return ""
	if len(words) == 1:
		return words[0][:3].upper()
	return "".join(word[0] for word in words)[:3].upper()


def bank_label_for_account(bank_account: str | None) -> str:
	if not bank_account:
		return ""
	row = frappe.db.get_value("Bank Account", bank_account, ["bank", "account_name"], as_dict=True)
	if not row:
		return bank_account
	return row.bank or row.account_name or bank_account


def ensure_belize_banks() -> list[str]:
	if not frappe.db.exists("DocType", "Bank"):
		return []

	created = []
	for bank_name in BELIZE_BANKS:
		if frappe.db.exists("Bank", bank_name):
			continue
		frappe.get_doc({"doctype": "Bank", "bank_name": bank_name}).insert(ignore_permissions=True)
		created.append(bank_name)
	return created


def ensure_belize_company_bank_accounts(company: str | None = None) -> list[dict]:
	"""Create company Bank Accounts named after Belize banks so payroll can pick a source."""
	if not frappe.db.exists("DocType", "Bank Account"):
		return []

	ensure_belize_banks()
	companies = [company] if company else frappe.get_all("Company", pluck="name")
	accounts = []
	for company_name in companies:
		if not company_name:
			continue
		accounts.extend(_ensure_company_bank_accounts(company_name))
	return accounts


def get_company_payment_banks(company: str) -> list[dict]:
	"""Return the BPO bank accounts payroll can be wired from."""
	if not company:
		return []

	ensure_belize_company_bank_accounts(company)
	if not frappe.db.exists("DocType", "Bank Account"):
		return []

	fields = ["name", "account_name", "bank", "account", "bank_account_no"]
	meta = frappe.get_meta("Bank Account")
	if meta.has_field("party"):
		fields.append("party")
	if meta.has_field("party_type"):
		fields.append("party_type")

	rows = frappe.get_all(
		"Bank Account",
		filters=_connected_bank_account_filters(company),
		fields=fields,
		order_by="bank asc, account_name asc",
	)
	rows = [row for row in rows if _is_connected_company_bank(row)]
	belize = {bank: None for bank in BELIZE_BANKS}
	others = []
	for row in rows:
		payload = {
			"name": row.name,
			"account_name": row.account_name,
			"bank": row.bank,
			"account": row.account,
			"bank_account_no": row.bank_account_no,
			"label": row.bank or row.account_name or row.name,
		}
		if row.bank in belize and belize[row.bank] is None:
			belize[row.bank] = payload
		else:
			others.append(payload)

	return [belize[bank] for bank in BELIZE_BANKS if belize[bank]] + others


def _ensure_company_bank_accounts(company: str) -> list[dict]:
	fallback_gl = _company_bank_gl(company)
	if not fallback_gl:
		return []

	abbr = frappe.db.get_value("Company", company, "abbr") or company
	created = []
	for bank_name in BELIZE_BANKS:
		gl_account = _bank_gl_for(company, bank_name, fallback_gl)
		name = _get_or_create_company_bank_account(company, bank_name, gl_account, abbr)
		if name:
			_stamp_company_account_no(name, bank_name)
			created.append({"name": name, "bank": bank_name, "account": gl_account})
	if created:
		_set_company_default_bank(company, created[0]["account"])
	return created


def _bank_gl_for(company: str, bank_name: str, fallback_gl: str) -> str:
	existing = frappe.db.get_value(
		"Account",
		{"account_name": bank_name, "company": company, "account_type": "Bank", "is_group": 0},
		"name",
	)
	if existing:
		return existing

	parent = frappe.db.get_value("Account", fallback_gl, "parent_account") if fallback_gl else None
	if not parent:
		parent = frappe.db.get_value(
			"Account",
			{"company": company, "is_group": 1, "account_type": "Bank"},
			"name",
		) or frappe.db.get_value(
			"Account",
			{"company": company, "is_group": 1, "root_type": "Asset"},
			"name",
		)
	if not parent:
		return fallback_gl

	try:
		return (
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": bank_name,
					"parent_account": parent,
					"company": company,
					"account_type": "Bank",
					"is_group": 0,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	except Exception:
		return (
			frappe.db.get_value(
				"Account",
				{"account_name": bank_name, "company": company, "is_group": 0},
				"name",
			)
			or fallback_gl
		)


def _connected_bank_account_filters(company: str | None = None) -> dict:
	"""Bank accounts linked to the company, without requiring Is Company Account."""
	filters = {}
	if company:
		filters["company"] = company
	if frappe.get_meta("Bank Account").has_field("disabled"):
		filters["disabled"] = 0
	return filters


def _is_connected_company_bank(row) -> bool:
	return not (row.get("party") or row.get("party_type"))


@frappe.whitelist()
def get_default_payroll_bank_account(company: str | None = None) -> str | None:
	"""Bank Account to prefill on Payroll Entry Pay From Bank Account."""
	if not company:
		return None

	last_used = frappe.get_all(
		"Payroll Entry",
		filters={"company": company, "docstatus": ["<", 2]},
		fields=["bank_account"],
		order_by="modified desc",
		limit=20,
	)
	for row in last_used:
		name = row.bank_account
		if name and _is_usable_payroll_bank(name, company):
			return name

	banks = get_company_payment_banks(company)
	return banks[0]["name"] if banks else None


def _is_usable_payroll_bank(name: str, company: str) -> bool:
	meta = frappe.get_meta("Bank Account")
	fields = ["name", "company"]
	if meta.has_field("disabled"):
		fields.append("disabled")
	if meta.has_field("party"):
		fields.append("party")
	if meta.has_field("party_type"):
		fields.append("party_type")
	row = frappe.db.get_value("Bank Account", name, fields, as_dict=True)
	if not row or row.company != company:
		return False
	if row.get("disabled"):
		return False
	return _is_connected_company_bank(row)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def payroll_bank_account_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link search for Pay From Bank Account: company-connected banks, no company-account flag."""
	from frappe.desk.reportview import get_match_cond

	company = (filters or {}).get("company")
	meta = frappe.get_meta("Bank Account")
	conditions = []
	if meta.has_field("party"):
		conditions.append("ifnull(party, '') = ''")
	if meta.has_field("party_type"):
		conditions.append("ifnull(party_type, '') = ''")
	values = {
		"txt": f"%{txt or ''}%",
		"start": int(start or 0),
		"page_len": int(page_len or 20),
	}

	if company:
		conditions.append("company = %(company)s")
		values["company"] = company
	if meta.has_field("disabled"):
		conditions.append("ifnull(disabled, 0) = 0")

	search_fields = [searchfield, "account_name", "bank"]
	if meta.has_field("bank_account_no"):
		search_fields.append("bank_account_no")
	search_clause = " or ".join(f"`{field}` like %(txt)s" for field in search_fields if field)
	if search_clause:
		conditions.append(f"({search_clause})")

	return frappe.db.sql(
		f"""
		select name, ifnull(bank, account_name), ifnull(bank_account_no, '')
		from `tabBank Account`
		where {" and ".join(conditions) if conditions else "1=1"}
		{get_match_cond(doctype)}
		order by bank, account_name
		limit %(start)s, %(page_len)s
		""",
		values,
	)


def _get_or_create_company_bank_account(company: str, bank_name: str, gl_account: str, abbr: str) -> str | None:
	existing = _existing_company_bank_account(company, bank_name)
	if existing:
		return existing

	account_name = f"{bank_name} - {abbr}"
	if frappe.db.exists("Bank Account", account_name):
		return account_name

	doc = {
		"doctype": "Bank Account",
		"account_name": account_name,
		"bank": bank_name,
		"is_company_account": 1,
		"company": company,
		"account": gl_account,
	}
	meta = frappe.get_meta("Bank Account")
	account_type_field = meta.get_field("account_type")
	if account_type_field:
		account_type = "Bank"
		if account_type_field.fieldtype == "Link":
			account_type = (
				account_type
				if frappe.db.exists(account_type_field.options, account_type)
				else None
			)
		if account_type:
			doc["account_type"] = account_type
	account_no = COMPANY_BANK_ACCOUNT_NOS.get(bank_name)
	if meta.has_field("bank_account_no") and account_no:
		doc["bank_account_no"] = account_no

	try:
		return frappe.get_doc(doc).insert(ignore_permissions=True).name
	except Exception:
		frappe.log_error(title=f"Could not create payroll bank account {account_name}")
		return _existing_company_bank_account(company, bank_name)


def _existing_company_bank_account(company: str, bank_name: str) -> str | None:
	fields = ["name"]
	meta = frappe.get_meta("Bank Account")
	if meta.has_field("party"):
		fields.append("party")
	if meta.has_field("party_type"):
		fields.append("party_type")
	rows = frappe.get_all(
		"Bank Account",
		filters={"company": company, "bank": bank_name},
		fields=fields,
		order_by="creation",
	)
	for row in rows:
		if _is_connected_company_bank(row):
			return row.name
	return None


def _stamp_company_account_no(name: str, bank_name: str):
	if not name or not frappe.get_meta("Bank Account").has_field("bank_account_no"):
		return
	account_no = COMPANY_BANK_ACCOUNT_NOS.get(bank_name)
	if not account_no:
		return
	if frappe.db.get_value("Bank Account", name, "bank_account_no"):
		return
	frappe.db.set_value("Bank Account", name, "bank_account_no", account_no, update_modified=False)


def ensure_company_default_bank_account(company: str | None = None) -> str | None:
	"""Return a Bank GL for payroll, creating the Belize chart defaults if needed."""
	if not company:
		return None
	ensure_belize_company_bank_accounts(company)
	return _company_bank_gl(company)


def _company_bank_gl(company: str) -> str | None:
	gl = frappe.db.get_value("Company", company, "default_bank_account")
	if gl and frappe.db.exists("Account", gl):
		return gl
	existing = frappe.db.get_value(
		"Account",
		{"company": company, "account_type": "Bank", "is_group": 0, "disabled": 0},
		"name",
		order_by="creation",
	)
	if existing:
		_set_company_default_bank(company, existing)
		return existing
	created = _create_default_bank_gl(company)
	if created:
		_set_company_default_bank(company, created)
	return created


def _create_default_bank_gl(company: str) -> str | None:
	if not frappe.db.exists("DocType", "Account"):
		return None
	parent = frappe.db.get_value(
		"Account",
		{"company": company, "is_group": 1, "account_type": "Bank"},
		"name",
	) or frappe.db.get_value(
		"Account",
		{"company": company, "is_group": 1, "root_type": "Asset"},
		"name",
	)
	if not parent:
		return None

	account_name = BELIZE_BANKS[0] if BELIZE_BANKS else "Bank Account"
	existing = frappe.db.get_value(
		"Account",
		{"account_name": account_name, "company": company, "is_group": 0},
		"name",
	)
	if existing:
		return existing

	try:
		return (
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": account_name,
					"parent_account": parent,
					"company": company,
					"account_type": "Bank",
					"is_group": 0,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	except Exception:
		frappe.log_error(title=f"Could not create default bank GL for {company}")
		return frappe.db.get_value(
			"Account",
			{"account_name": account_name, "company": company, "is_group": 0},
			"name",
		)


def _set_company_default_bank(company: str, gl: str | None):
	if not company or not gl:
		return
	if frappe.db.get_value("Company", company, "default_bank_account"):
		return
	frappe.db.set_value("Company", company, "default_bank_account", gl, update_modified=False)
