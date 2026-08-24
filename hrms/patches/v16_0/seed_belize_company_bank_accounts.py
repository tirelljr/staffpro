# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Create Belize Bank masters and company Bank Accounts for payroll source selection."""

from hrms.hr.belize_banks import ensure_belize_company_bank_accounts


def execute():
	ensure_belize_company_bank_accounts()
