# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Remove Employees by Grade from the Data Analytics dashboard."""

from hrms.patches.v16_0.add_data_analytics_dashboard import _import_dashboard


def execute():
	_import_dashboard("hr/hr_dashboard/data_analytics/data_analytics.json")
