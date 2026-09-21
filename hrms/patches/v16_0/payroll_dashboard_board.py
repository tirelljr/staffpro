# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Replace stock Payroll dashboard cards and charts with the custom board."""

from hrms.patches.v16_0.add_data_analytics_dashboard import _import_dashboard


def execute():
	_import_dashboard("payroll/payroll_dashboard/payroll/payroll.json")
