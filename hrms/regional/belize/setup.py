# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import getdate, today

from hrms.payroll.social_security import ensure_employee_ss_fields, ensure_ss_salary_components


def setup():
	make_custom_fields()
	ensure_ss_salary_components()
	ensure_income_tax_component()
	create_belize_income_tax_slabs()


def uninstall():
	pass


def make_custom_fields():
	ensure_employee_ss_fields()


def ensure_income_tax_component():
	if not frappe.db.exists("Salary Component", "Income Tax"):
		return

	frappe.db.set_value(
		"Salary Component",
		"Income Tax",
		{
			"variable_based_on_taxable_salary": 1,
			"is_income_tax_component": 1,
		},
		update_modified=False,
	)


def create_belize_income_tax_slabs():
	for company in frappe.get_all("Company", filters={"country": "Belize"}, pluck="name"):
		_create_slab_for_company(company)

	if not frappe.get_all("Company", filters={"country": "Belize"}, pluck="name"):
		_create_slab_for_company(None)


def _create_slab_for_company(company: str | None):
	title = f"Belize PAYE {getdate(today()).year}"
	if company:
		title = f"{title} - {company}"

	if frappe.db.exists("Income Tax Slab", title):
		return frappe.get_doc("Income Tax Slab", title)

	currency = "BZD"
	if company:
		currency = frappe.get_cached_value("Company", company, "default_currency") or currency

	doc = frappe.get_doc(
		{
			"doctype": "Income Tax Slab",
			"name": title,
			"company": company,
			"currency": currency,
			"effective_from": f"{getdate(today()).year}-01-01",
			"tax_relief_limit": 26000,
			"allow_tax_exemption": 1,
			"standard_tax_exemption_amount": 0,
			"slabs": [
				{
					"from_amount": 26001,
					"to_amount": 0,
					"percent_deduction": 25,
				}
			],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc
