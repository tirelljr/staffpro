"""Attendance dashboard: keep month KPIs, drop charts, open Hours from Time."""

from hrms.patches.v16_0.add_data_analytics_dashboard import _import_dashboard
from hrms.patches.v16_0.apply_bpo_sidebar_labels import execute as sync_sidebars


def execute():
	_import_dashboard("hr/hr_dashboard/attendance/attendance.json")
	sync_sidebars()
