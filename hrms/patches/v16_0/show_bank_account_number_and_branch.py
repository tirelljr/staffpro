# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Show Bank Account Number and Branch Location on the main Bank Account column."""

from hrms.hr.bpo_bank_account import apply_bank_account_layout


def execute():
	apply_bank_account_layout()
