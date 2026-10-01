# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Fiscal Year helpers. Payroll YTD uses calendar dates; invoices still need a Fiscal Year."""

from __future__ import annotations

from datetime import date

import frappe
from frappe.utils import add_days, add_years, cint, getdate


def expected_fiscal_year_end(start_date):
	if not start_date:
		return None
	return add_days(add_years(getdate(start_date), 1), -1)


def align_fiscal_year_dates(doc, method=None):
	if not doc.year_start_date:
		return
	expected = expected_fiscal_year_end(doc.year_start_date)
	if expected and getdate(doc.year_end_date) != expected:
		doc.year_end_date = expected


def calendar_year_period(for_date):
	"""Jan 1 – Dec 31 of the given date. Payroll YTD never needs Fiscal Year."""
	resolved = getdate(for_date) if for_date else date.today()
	return date(resolved.year, 1, 1), date(resolved.year, 12, 31)


def years_to_cover(around=None, extra=None):
	"""Previous, current, and next calendar years, plus any extra years already in use."""
	resolved = getdate(around) if around else date.today()
	years = {resolved.year - 1, resolved.year, resolved.year + 1}
	for year in extra or ():
		year_num = cint(year)
		if year_num >= 1900:
			years.add(year_num)
	return sorted(years)


def ensure_company_fiscal_years(doc=None, method=None, around=None):
	"""Create calendar Fiscal Years so payroll, invoices, and setup never miss one."""
	if not frappe.db.exists("DocType", "Fiscal Year"):
		return []

	company = _company_name(doc)
	companies = [company] if company else frappe.get_all("Company", pluck="name")
	created = []
	for year_num in years_to_cover(around, _years_from_existing_docs()):
		start, end = date(year_num, 1, 1), date(year_num, 12, 31)
		name = _ensure_fiscal_year_record(str(year_num), start, end, companies)
		if name:
			created.append(name)
	return created


def _company_name(doc):
	if isinstance(doc, str) and doc:
		return doc
	return getattr(doc, "name", None) if doc is not None else None


def _years_from_existing_docs():
	years = set()
	for doctype, field in (
		("Payroll Entry", "start_date"),
		("Salary Slip", "start_date"),
		("Sales Invoice", "posting_date"),
		("Client Invoice", "posting_date"),
	):
		if not frappe.db.exists("DocType", doctype) or not frappe.db.has_column(doctype, field):
			continue
		row = frappe.db.sql(
			f"select min(`{field}`) as first_date, max(`{field}`) as last_date from `tab{doctype}`"
		)
		if not row or not row[0]:
			continue
		first_date, last_date = row[0]
		if first_date:
			years.add(getdate(first_date).year)
		if last_date:
			years.add(getdate(last_date).year)
	return years


def _ensure_fiscal_year_record(year_name: str, start, end, companies) -> str | None:
	existing = _covering_fiscal_year(start)
	if existing:
		_enable_fiscal_year(existing)
		_attach_companies_if_restricted(existing, companies)
		return existing

	if frappe.db.exists("Fiscal Year", year_name):
		_enable_fiscal_year(year_name)
		_attach_companies_if_restricted(year_name, companies)
		return year_name

	try:
		doc = frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": year_name,
				"year_start_date": start,
				"year_end_date": end,
				"auto_created": 1,
			}
		)
		for company_name in companies:
			if company_name:
				doc.append("companies", {"company": company_name})
		doc.flags.ignore_permissions = True
		doc.insert()
		return doc.name
	except Exception:
		frappe.log_error(title=f"Could not create Fiscal Year {year_name}")
		if frappe.db.exists("Fiscal Year", year_name):
			return year_name
		return None


def _enable_fiscal_year(name: str) -> None:
	if cint(frappe.db.get_value("Fiscal Year", name, "disabled")):
		frappe.db.set_value("Fiscal Year", name, "disabled", 0)


def _covering_fiscal_year(on_date):
	on_date = getdate(on_date)
	return frappe.db.get_value(
		"Fiscal Year",
		{"year_start_date": ["<=", on_date], "year_end_date": [">=", on_date], "disabled": 0},
		"name",
	)


def _attach_companies_if_restricted(fiscal_year: str, companies) -> None:
	"""A Fiscal Year with no companies is global. Only attach when it is already restricted."""
	if not frappe.db.exists("DocType", "Fiscal Year Company"):
		return
	if not frappe.db.exists("Fiscal Year Company", {"parent": fiscal_year}):
		return

	missing = [
		company
		for company in companies
		if company and not frappe.db.exists("Fiscal Year Company", {"parent": fiscal_year, "company": company})
	]
	if not missing:
		return

	doc = frappe.get_doc("Fiscal Year", fiscal_year)
	for company in missing:
		doc.append("companies", {"company": company})
	doc.flags.ignore_permissions = True
	doc.save()
