# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Create calendar Fiscal Years so payroll and invoices do not fail on this site."""


def execute():
	from hrms.overrides.fiscal_year import ensure_company_fiscal_years

	ensure_company_fiscal_years()
