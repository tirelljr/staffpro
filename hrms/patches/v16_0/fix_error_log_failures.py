# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Repair the four Error Log failures seen on desk/admin/error-log."""


def execute():
	from hrms.hr.doctype.document_category.document_category import seed_document_categories
	from hrms.overrides.desk_compat import install_desk_compat
	from hrms.overrides.fiscal_year import ensure_company_fiscal_years
	from hrms.payroll.bpo_sales_invoice import ensure_invoice_report_permissions

	install_desk_compat()
	ensure_invoice_report_permissions()
	seed_document_categories()
	ensure_company_fiscal_years()
