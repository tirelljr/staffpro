# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Drop payroll payout KPI from the People dashboard; keep hours/pay cards only."""

from hrms.patches.v16_0.add_data_analytics_dashboard import _import_dashboard


def execute():
	_import_dashboard("hr/hr_dashboard/human_resource/human_resource.json")
