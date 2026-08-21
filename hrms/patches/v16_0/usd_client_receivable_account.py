# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""USD client invoices need a USD receivable — company Debtors stay in BZD."""

from hrms.payroll.bpo_client_accounts import setup_usd_client_billing


def execute():
	setup_usd_client_billing()
