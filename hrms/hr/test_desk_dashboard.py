# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from frappe.utils import add_days, add_years, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.desk_dashboard import (
	_normalize_kpi_period,
	_percent_change,
	_period_bounds,
	_prepare_card_period_filters,
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
