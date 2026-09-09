# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from frappe.utils import add_days, add_years, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.desk_dashboard import (
	_chart_custom_options,
	_chart_is_empty,
	_chart_period_bounds,
	_chart_time_interval,
	_merge_live_floor_attendance,
	_normalize_chart_period,
	_normalize_kpi_period,
	_percent_change,
	_period_bounds,
	_prepare_card_period_filters,
	_prepare_chart_period_filters,
	get_upcoming_absences,
	get_upcoming_celebrations,
)
from hrms.tests.utils import HRMSTestSuite


class TestDeskDashboardCelebrations(HRMSTestSuite):
	def setUp(self):
		self.company = "_Test Company"

	def test_celebrations_use_date_of_birth_and_date_of_joining(self):
		today = getdate()
		birthday = add_days(today, 2)
		anniversary = add_days(today, 3)
		date_of_birth = add_years(birthday, -32)
		date_of_joining = add_years(anniversary, -4)

		employee = make_employee(
			"dash.celebrations@example.com",
			company=self.company,
			first_name="Celeb",
			last_name="Dates",
			date_of_birth=date_of_birth,
			date_of_joining=date_of_joining,
		)

		payload = get_upcoming_celebrations(period="weekly", company=self.company)
		mine = [event for event in payload["events"] if event["employee"] == employee]
		by_type = {event["event_type"]: event for event in mine}

		self.assertFalse(payload["fallback"])
		self.assertIn("birthday", by_type)
		self.assertEqual(by_type["birthday"]["day"], birthday.day)
		self.assertEqual(by_type["birthday"]["month"], birthday.strftime("%b"))
		self.assertEqual(getdate(by_type["birthday"]["source_date"]), getdate(date_of_birth))

		self.assertIn("anniversary", by_type)
		self.assertEqual(by_type["anniversary"]["day"], anniversary.day)
		self.assertEqual(by_type["anniversary"]["month"], anniversary.strftime("%b"))
		self.assertEqual(by_type["anniversary"]["years_completed"], 4)
		self.assertEqual(getdate(by_type["anniversary"]["source_date"]), getdate(date_of_joining))


class TestDeskDashboardAbsences(HRMSTestSuite):
	def setUp(self):
		self.company = "_Test Company"

	def test_absences_show_upcoming_leave_applications(self):
		# The HRMS bootstrap test data creates Leave Applications in May 2013.
		frappe.flags.current_date = getdate("2013-05-02")

		payload = get_upcoming_absences(period="monthly", company=self.company)
		employees = {row["employee"] for row in payload["rows"]}
		self.assertEqual(len(payload["rows"]), 2)
		self.assertIn("_T-Employee-00001", employees)
		self.assertIn("_T-Employee-00002", employees)

		types = {row["leave_type"] for row in payload["rows"]}
		self.assertEqual(types, {"_Test Leave Type"})


class TestDeskDashboardKpiPeriod(HRMSTestSuite):
	def setUp(self):
		frappe.flags.current_date = getdate("2026-09-03")

	def tearDown(self):
		frappe.flags.current_date = None

	def test_normalize_kpi_period(self):
		self.assertEqual(_normalize_kpi_period("today"), "day")
		self.assertEqual(_normalize_kpi_period("This Week"), "week")
		self.assertEqual(_normalize_kpi_period("monthly"), "month")
		self.assertEqual(_normalize_kpi_period("unknown"), "month")

	def test_period_bounds(self):
		self.assertEqual(_period_bounds("Daily", 0), (getdate("2026-09-03"), getdate("2026-09-03")))
		self.assertEqual(_period_bounds("Weekly", 0), (getdate("2026-08-31"), getdate("2026-09-06")))
		self.assertEqual(_period_bounds("Monthly", 0), (getdate("2026-09-01"), getdate("2026-09-30")))
		self.assertEqual(_period_bounds("Yearly", 0), (getdate("2026-01-01"), getdate("2026-12-31")))
		self.assertEqual(_period_bounds("Weekly", 1), (getdate("2026-08-24"), getdate("2026-08-30")))

	def test_timespan_filter_is_replaced(self):
		doc = frappe._dict(
			document_type="Attendance",
			filters_json='[["Attendance","status","=","Present"],["Attendance","attendance_date","Timespan","this month"]]',
			dynamic_filters_json="[]",
		)
		prepared = _prepare_card_period_filters(doc, "week")
		self.assertEqual(prepared["date_field"], "attendance_date")
		self.assertIn(["Attendance", "status", "=", "Present"], prepared["current"])
		self.assertIn(
			["Attendance", "attendance_date", "between", ["2026-08-31", "2026-09-06"]],
			prepared["current"],
		)
		self.assertFalse(any(row[2] == "Timespan" for row in prepared["current"]))

	def test_leave_overlap_filters(self):
		doc = frappe._dict(
			document_type="Leave Application",
			filters_json='[["Leave Application","status","=","Approved"]]',
			dynamic_filters_json='[["Leave Application","from_date","<=","2026-09-03"],["Leave Application","to_date",">=","2026-09-03"]]',
		)
		prepared = _prepare_card_period_filters(doc, "month")
		self.assertEqual(prepared["overlap"], ("from_date", "to_date"))
		self.assertIn(["Leave Application", "from_date", "<=", "2026-09-30"], prepared["current"])
		self.assertIn(["Leave Application", "to_date", ">=", "2026-09-01"], prepared["current"])

	def test_percent_change(self):
		self.assertEqual(_percent_change(12, 10), 20.0)
		self.assertEqual(_percent_change(5, 0), 100.0)
		self.assertEqual(_percent_change(0, 0), 0.0)


class TestDeskDashboardChartPeriod(HRMSTestSuite):
	def setUp(self):
		frappe.flags.current_date = getdate("2026-09-03")

	def tearDown(self):
		frappe.flags.current_date = None

	def test_normalize_chart_period(self):
		self.assertEqual(_normalize_chart_period("today"), "day")
		self.assertEqual(_normalize_chart_period("This Week"), "week")
		self.assertEqual(_normalize_chart_period("monthly"), "month")
		self.assertEqual(_normalize_chart_period("Select Date Range"), "custom")
		self.assertEqual(_normalize_chart_period("unknown"), "month")

	def test_chart_period_bounds(self):
		self.assertEqual(_chart_period_bounds("day"), (getdate("2026-09-03"), getdate("2026-09-03")))
		self.assertEqual(_chart_period_bounds("week"), (getdate("2026-08-31"), getdate("2026-09-06")))
		self.assertEqual(_chart_period_bounds("month"), (getdate("2026-09-01"), getdate("2026-09-30")))
		self.assertEqual(
			_chart_period_bounds("custom", "2026-08-01", "2026-08-15"),
			(getdate("2026-08-01"), getdate("2026-08-15")),
		)
		self.assertEqual(
			_chart_period_bounds("custom", "2026-08-15", "2026-08-01"),
			(getdate("2026-08-01"), getdate("2026-08-15")),
		)

	def test_group_by_timespan_is_replaced(self):
		doc = frappe._dict(
			chart_type="Group By",
			timeseries=0,
			document_type="Attendance",
			time_interval="Yearly",
			filters_json='[["Attendance","docstatus","=","1"],["Attendance","attendance_date","Timespan","this month"]]',
			dynamic_filters_json="[]",
		)
		start, end = _chart_period_bounds("week")
		filters = _prepare_chart_period_filters(doc, start, end, "Daily")
		self.assertIn(["Attendance", "docstatus", "=", "1"], filters)
		self.assertIn(["Attendance", "attendance_date", "between", ["2026-08-31", "2026-09-06"]], filters)
		self.assertFalse(any(row[2] == "Timespan" for row in filters))

	def test_employee_snapshot_uses_joining_cutoff(self):
		doc = frappe._dict(
			chart_type="Group By",
			timeseries=0,
			document_type="Employee",
			time_interval="Yearly",
			filters_json='[["Employee","status","=","Active"]]',
			dynamic_filters_json="[]",
		)
		start, end = _chart_period_bounds("month")
		filters = _prepare_chart_period_filters(doc, start, end, "Monthly")
		self.assertIn(["Employee", "status", "=", "Active"], filters)
		self.assertIn(["Employee", "date_of_joining", "<=", "2026-09-30"], filters)
		self.assertFalse(any(row[2] == "between" for row in filters))

	def test_timeseries_keeps_based_on_dates(self):
		doc = frappe._dict(
			chart_type="Count",
			timeseries=1,
			document_type="Employee Checkin",
			time_interval="Daily",
			filters_json='[["Employee Checkin","log_type","=","IN"]]',
			dynamic_filters_json="[]",
		)
		start, end = _chart_period_bounds("month")
		filters = _prepare_chart_period_filters(doc, start, end, "Daily")
		self.assertEqual(filters, [["Employee Checkin", "log_type", "=", "IN"]])

	def test_custom_chart_gets_date_filters(self):
		doc = frappe._dict(
			chart_type="Custom",
			timeseries=0,
			document_type="",
			time_interval="Monthly",
			filters_json='{"time_interval":"Monthly"}',
			dynamic_filters_json="{}",
		)
		start, end = _chart_period_bounds("week")
		filters = _prepare_chart_period_filters(doc, start, end, "Daily")
		self.assertEqual(filters["from_date"], "2026-08-31")
		self.assertEqual(filters["to_date"], "2026-09-06")
		self.assertEqual(filters["time_interval"], "Daily")

	def test_chart_time_interval(self):
		daily = frappe._dict(time_interval="Daily")
		monthly = frappe._dict(time_interval="Monthly")
		self.assertEqual(_chart_time_interval("day", getdate("2026-09-03"), getdate("2026-09-03"), daily), "Daily")
		self.assertEqual(_chart_time_interval("month", getdate("2026-09-01"), getdate("2026-09-30"), daily), "Daily")
		self.assertEqual(_chart_time_interval("month", getdate("2026-09-01"), getdate("2026-09-30"), monthly), "Monthly")
		self.assertEqual(_chart_time_interval("custom", getdate("2026-01-01"), getdate("2026-12-31"), monthly), "Monthly")

	def test_empty_company_filter_is_dropped(self):
		doc = frappe._dict(
			chart_type="Group By",
			timeseries=0,
			document_type="Attendance",
			time_interval="Yearly",
			filters_json='[["Attendance","docstatus","<","2"]]',
			dynamic_filters_json='[["Attendance","company","=","None"]]',
		)
		start, end = _chart_period_bounds("month")
		filters = _prepare_chart_period_filters(doc, start, end, "Daily")
		self.assertFalse(any(row[1] == "company" for row in filters))

	def test_chart_is_empty_ignores_zero_series(self):
		self.assertTrue(_chart_is_empty({"labels": ["Sep 1"], "datasets": [{"values": [0, 0]}]}))
		self.assertFalse(_chart_is_empty({"labels": ["Present"], "datasets": [{"values": [3]}]}))

	def test_floor_attendance_includes_live_clock_in(self):
		from hrms.hr.doctype.employee_checkin.test_employee_checkin import make_checkin

		frappe.flags.current_date = None
		employee = make_employee(
			"dash.floor.live@example.com",
			company="_Test Company",
			first_name="Floor",
			last_name="Live",
		)
		make_checkin(employee, log_type="IN")
		doc = frappe._dict(name="Floor Attendance", chart_name="Floor Attendance")
		today = getdate()
		merged = _merge_live_floor_attendance(doc, {"labels": [], "datasets": []}, today, today)
		self.assertFalse(_chart_is_empty(merged))
		self.assertIn("Present", merged.get("labels") or [])

	def test_empty_custom_options_are_ignored(self):
		self.assertEqual(_chart_custom_options(frappe._dict(custom_options="")), {})
		self.assertEqual(_chart_custom_options(frappe._dict(custom_options=None)), {})
		self.assertEqual(_chart_custom_options(frappe._dict(custom_options="   ")), {})
		self.assertEqual(_chart_custom_options(frappe._dict(custom_options="not-json")), {})
		self.assertEqual(
			_chart_custom_options(frappe._dict(custom_options='{"colors": ["#7c5cfc"]}')),
			{"colors": ["#7c5cfc"]},
		)

