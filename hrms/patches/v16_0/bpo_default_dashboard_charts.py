# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Replace ERPNext default charts with call-center HRM and payroll charts."""

from hrms.overrides.bpo_dashboards import hide_non_bpo_dashboard_records, import_fixture
from hrms.patches.v16_0.add_data_analytics_dashboard import _import_dashboard

CHARTS = (
	"hr/dashboard_chart/hours_worked/hours_worked.json",
	"hr/dashboard_chart/daily_pay/daily_pay.json",
	"hr/dashboard_chart/floor_attendance/floor_attendance.json",
	"hr/dashboard_chart/clock_ins/clock_ins.json",
	"hr/dashboard_chart/time_off_requests/time_off_requests.json",
	"payroll/dashboard_chart/net_pay/net_pay.json",
)

CARDS = (
	"hr/number_card/agents_present_(today)/agents_present_(today).json",
	"hr/number_card/hours_worked_(this_week)/hours_worked_(this_week).json",
	"hr/number_card/daily_pay_(this_week)/daily_pay_(this_week).json",
)

DASHBOARDS = (
	"hr/hr_dashboard/human_resource/human_resource.json",
	"hr/hr_dashboard/leaves/leaves.json",
	"payroll/payroll_dashboard/payroll/payroll.json",
)


def execute():
	for path in CHARTS + CARDS:
		import_fixture(path)
	for path in DASHBOARDS:
		_import_dashboard(path)
	hide_non_bpo_dashboard_records()
