# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Count draft attendance from live clock-ins on People dashboard charts."""

from hrms.overrides.bpo_dashboards import import_fixture

CHARTS = (
	"hr/dashboard_chart/floor_attendance/floor_attendance.json",
	"hr/dashboard_chart/hours_worked/hours_worked.json",
	"hr/number_card/agents_present_(today)/agents_present_(today).json",
)


def execute():
	for path in CHARTS:
		import_fixture(path)
