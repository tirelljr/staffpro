# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Drop IBAN and Company Account from the Bank Account list; hide Is Company Account."""

from hrms.hr.bpo_bank_account import apply_bank_account_layout


def execute():
	apply_bank_account_layout()
