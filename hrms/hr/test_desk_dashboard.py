# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import datetime

import frappe

from frappe.utils import add_days, add_years, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.desk_dashboard import (
	_absence_date_label,
	_attendance_board_kpis,
	_attendance_board_status,
	_attendance_overtime_by_employee,
	_bonus_in_range,
	_build_payroll_board_row,
	_chart_custom_options,
	_chart_is_empty,
	_chart_period_bounds,
	_chart_time_interval,
	_classify_earning,
	_custom_chart_source_method,
	_fetch_dashboard_chart_data,
	_format_board_clock,
	_format_overtime_label,
	_merge_live_floor_attendance,
	_normalize_chart_period,
	_normalize_kpi_period,
	_pay_in_range,
	_payroll_board_departments,
	_payroll_board_kpis,
	_payroll_board_period_label,
	_payroll_pay_date_label,
	_payroll_status,
	_previous_date_range,
	_previous_pay_period,
	_upcoming_pay_period,
	_percent_change,
	_period_bounds,
	_prepare_card_period_filters,
	_prepare_chart_period_filters,
	get_attendance_board,
	get_payroll_board,
	get_upcoming_absences,
	get_upcoming_celebrations,
)
from hrms.hr.doctype.attendance.attendance import mark_attendance
from hrms.hr.doctype.employee_checkin.test_employee_checkin import make_checkin
from hrms.hr.doctype.shift_type.test_shift_type import setup_shift_type
from hrms.tests.test_utils import create_department
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

	def tearDown(self):
		frappe.flags.current_date = None

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

	def test_absences_hide_after_the_last_day(self):
		frappe.flags.current_date = getdate("2013-05-06")
		payload = get_upcoming_absences(period="monthly", company=self.company)
		self.assertEqual(payload["rows"], [])

	def test_absence_date_label_is_readable(self):
		self.assertEqual(_absence_date_label("2026-09-09", "2026-09-09"), "September 9th")
		self.assertEqual(_absence_date_label("2026-09-09", "2026-09-12"), "September 9th – 12th")
		self.assertEqual(_absence_date_label("2026-09-08", "2026-10-02"), "September 8th – October 2nd")
		self.assertEqual(
			_absence_date_label("2026-12-28", "2027-01-03"),
			"December 28th, 2026 – January 3rd, 2027",
		)


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

	def test_custom_chart_source_is_used_instead_of_count_query(self):
		doc = frappe._dict(
			name="Employees by Age",
			chart_type="Custom",
			source="Employees by Age",
			timeseries=0,
			document_type="",
			filters_json="{}",
			dynamic_filters_json="{}",
		)
		method = _custom_chart_source_method(doc)
		self.assertTrue(callable(method))

		start, end = getdate("2026-09-01"), getdate("2026-09-30")
		filters = _prepare_chart_period_filters(doc, start, end, "Monthly")
		data = _fetch_dashboard_chart_data(doc, filters, start, end, "Monthly")
		self.assertTrue(data.get("labels"))
		self.assertTrue(data.get("datasets"))

	def test_empty_custom_options_are_ignored(self):
		self.assertEqual(_chart_custom_options(frappe._dict(custom_options="")), {})
		self.assertEqual(_chart_custom_options(frappe._dict(custom_options=None)), {})
		self.assertEqual(_chart_custom_options(frappe._dict(custom_options="   ")), {})
		self.assertEqual(_chart_custom_options(frappe._dict(custom_options="not-json")), {})
		self.assertEqual(
			_chart_custom_options(frappe._dict(custom_options='{"colors": ["#7c5cfc"]}')),
			{"colors": ["#7c5cfc"]},
		)


class TestDeskDashboardAttendanceBoard(HRMSTestSuite):
	def setUp(self):
		self.company = "_Test Company"
		self.dept = create_department("Dash Attendance Board")

	def test_status_and_label_helpers(self):
		self.assertEqual(_attendance_board_status({"late": 1, "in_time": "09:00 AM"}), "late")
		self.assertEqual(_attendance_board_status({"late": 1}), "absent")
		self.assertEqual(_attendance_board_status({"in_time": "09:00 AM"}), "present")
		self.assertEqual(_attendance_board_status({"status": "IN"}), "present")
		self.assertEqual(_attendance_board_status({"attendance_status": "Present"}), "present")
		self.assertEqual(_attendance_board_status({}), "absent")
		self.assertEqual(_format_overtime_label(0), "0h")
		self.assertEqual(_format_overtime_label(2), "2h")
		self.assertEqual(_format_overtime_label(1.3), "1.3h")
		self.assertEqual(_format_board_clock(datetime(2026, 9, 20, 8, 5)), "8:05 AM")
		self.assertEqual(_format_board_clock(datetime(2026, 9, 20, 17, 10)), "5:10 PM")
		self.assertEqual(_format_board_clock("9:00 AM"), "9:00 AM")
		self.assertEqual(_format_board_clock(""), "")

		kpis = _attendance_board_kpis(
			[{"status": "present"}, {"status": "late"}, {"status": "absent"}],
			2,
			[{"status": "present"}, {"status": "absent"}],
			1,
		)
		self.assertEqual(kpis["total"]["value"], 3)
		self.assertEqual(kpis["present"]["value"], 2)
		self.assertEqual(kpis["absent"]["value"], 1)
		self.assertEqual(kpis["paid_leave"]["value"], 2)
		self.assertEqual(kpis["present"]["change"], 100.0)

	def test_board_shows_present_absent_late_and_overtime(self):
		shift = setup_shift_type(
			shift_type="Dash Attendance Late Shift",
			start_time="08:00:00",
			end_time="17:00:00",
			enable_late_entry_marking=1,
			late_entry_grace_period=10,
		)
		present = make_employee(
			"dash.att.present@example.com",
			company=self.company,
			department=self.dept,
			first_name="Present",
			last_name="Board",
		)
		absent = make_employee(
			"dash.att.absent@example.com",
			company=self.company,
			department=self.dept,
			first_name="Absent",
			last_name="Board",
		)
		late = make_employee(
			"dash.att.late@example.com",
			company=self.company,
			department=self.dept,
			first_name="Late",
			last_name="Board",
			default_shift=shift.name,
		)
		frappe.db.set_value("Employee", present, "designation", "Software Engineer", update_modified=False)

		today = getdate()
		in_time = datetime.combine(today, datetime.min.time()).replace(hour=9, minute=0)
		out_time = datetime.combine(today, datetime.min.time()).replace(hour=18, minute=30)
		make_checkin(present, time=in_time, log_type="IN")
		make_checkin(present, time=out_time, log_type="OUT")
		make_checkin(late, time=datetime.combine(today, datetime.min.time()).replace(hour=8, minute=25), log_type="IN")

		attendance = frappe.db.get_value("Attendance", {"employee": present, "attendance_date": today}, "name")
		if not attendance:
			attendance = mark_attendance(present, today, "Present")
		frappe.db.set_value(
			"Attendance",
			attendance,
			{
				"working_hours": 9.5,
			},
			update_modified=False,
		)

		payload = get_attendance_board(department=self.dept)
		by_employee = {row["employee"]: row for row in payload["rows"]}

		self.assertIn(present, by_employee)
		self.assertIn(absent, by_employee)
		self.assertIn(late, by_employee)
		self.assertEqual(by_employee[present]["status"], "present")
		self.assertEqual(by_employee[absent]["status"], "absent")
		self.assertEqual(by_employee[late]["status"], "late")
		self.assertEqual(by_employee[present]["designation"], "Software Engineer")
		self.assertEqual(by_employee[present]["hours_worked"], 9.5)
		self.assertEqual(by_employee[present]["hours_worked_label"], "9.5h")
		self.assertEqual(by_employee[absent]["hours_worked_label"], "0h")
		self.assertGreater(by_employee[late]["hours_worked"], 0)
		self.assertEqual(by_employee[present]["overtime_label"], "1.5h")
		self.assertRegex(by_employee[present]["in_time"], r"(?i)^9:00\s*AM$")
		self.assertRegex(by_employee[present]["out_time"], r"(?i)^6:30\s*PM$")
		self.assertRegex(by_employee[late]["in_time"], r"(?i)^8:25\s*AM$")
		self.assertFalse(by_employee[late]["out_time"])
		self.assertFalse(by_employee[absent]["in_time"])
		self.assertFalse(by_employee[absent]["out_time"])
		self.assertEqual(payload["date"], str(today))
		self.assertEqual(get_attendance_board(attendance_date=str(add_days(today, -1)), department=self.dept)["date"], str(today))
		self.assertGreaterEqual(payload["kpis"]["present"]["value"], 2)
		self.assertGreaterEqual(payload["kpis"]["absent"]["value"], 1)
		self.assertEqual(payload["kpis"]["total"]["value"], len(payload["rows"]))

	def test_board_overtime_is_hours_past_eight(self):
		employee = make_employee(
			"dash.att.overtime@example.com",
			company=self.company,
			department=self.dept,
			first_name="Overtime",
			last_name="Board",
		)
		today = getdate()
		attendance = mark_attendance(employee, today, "Present")
		frappe.db.set_value("Attendance", attendance, "working_hours", 12.7, update_modified=False)

		payload = get_attendance_board(department=self.dept)
		row = next(item for item in payload["rows"] if item["employee"] == employee)
		self.assertEqual(row["hours_worked"], 12.7)
		self.assertEqual(row["hours_worked_label"], "12.7h")
		self.assertEqual(row["overtime_hours"], 4.7)
		self.assertEqual(row["overtime_label"], "4.7h")

		eight = make_employee(
			"dash.att.regular@example.com",
			company=self.company,
			department=self.dept,
			first_name="Regular",
			last_name="Board",
		)
		attendance = mark_attendance(eight, today, "Present")
		frappe.db.set_value("Attendance", attendance, "working_hours", 8, update_modified=False)
		overtime = _attendance_overtime_by_employee([employee, eight], today)
		self.assertEqual(overtime[employee], 4.7)
		self.assertEqual(overtime[eight], 0)

	def test_board_shows_first_checkin_and_last_checkout_for_the_day(self):
		employee = make_employee(
			"dash.att.clocks@example.com",
			company=self.company,
			department=self.dept,
			first_name="Clocks",
			last_name="Board",
		)
		today = getdate()
		make_checkin(employee, time=datetime.combine(today, datetime.min.time()).replace(hour=8, minute=5), log_type="IN")
		make_checkin(employee, time=datetime.combine(today, datetime.min.time()).replace(hour=12, minute=0), log_type="OUT")
		make_checkin(employee, time=datetime.combine(today, datetime.min.time()).replace(hour=12, minute=45), log_type="IN")
		make_checkin(employee, time=datetime.combine(today, datetime.min.time()).replace(hour=17, minute=10), log_type="OUT")
		make_checkin(employee, time=datetime.combine(today, datetime.min.time()).replace(hour=17, minute=40), log_type="IN")

		payload = get_attendance_board(department=self.dept)
		row = next(item for item in payload["rows"] if item["employee"] == employee)
		self.assertRegex(row["in_time"], r"(?i)^8:05\s*AM$")
		self.assertRegex(row["out_time"], r"(?i)^5:10\s*PM$")

	def test_set_clock_times_show_on_attendance_board(self):
		from hrms.hr.doctype.attendance.attendance import set_clock_times
		from hrms.hr.page.in_out_today.in_out_today import get_in_out_today

		employee = make_employee(
			"dash.att.setclock@example.com",
			company=self.company,
			department=self.dept,
			first_name="SetClock",
			last_name="Board",
		)
		today = getdate()
		set_clock_times(
			employee=employee,
			attendance_date=today,
			in_time="10:00 AM",
			out_time="4:00 PM",
		)

		board = get_attendance_board(department=self.dept)
		row = next(item for item in board["rows"] if item["employee"] == employee)
		self.assertRegex(row["in_time"], r"(?i)^10:00\s*AM$")
		self.assertRegex(row["out_time"], r"(?i)^4:00\s*PM$")

		who = get_in_out_today(department=self.dept)
		person = next(item for item in who["details"] if item["employee"] == employee)
		self.assertRegex(person["in_time"], r"(?i)^10:00\s*AM$")
		self.assertRegex(person["out_time"], r"(?i)^4:00\s*PM$")


class TestDeskDashboardPayrollBoard(HRMSTestSuite):
	def setUp(self):
		self.company = "_Test Company"
		self.dept = create_department("Dash Payroll Design")

	def test_classify_earning_uses_category_then_name(self):
		self.assertEqual(_classify_earning("Basic", "Regular"), "base")
		self.assertEqual(_classify_earning("Night Bonus", "Bonus"), "bonus")
		self.assertEqual(_classify_earning("Referral Incentive", "Incentive"), "bonus")
		self.assertEqual(_classify_earning("OT Pay", "Overtime"), "overtime")
		self.assertEqual(_classify_earning("Weekend Overtime", None), "overtime")
		self.assertEqual(_classify_earning("Employee Incentive", ""), "bonus")

	def test_pay_date_label_uses_ordinal_month_day(self):
		self.assertEqual(_payroll_pay_date_label("2026-09-15"), "September 15th, 2026")
		self.assertEqual(_payroll_pay_date_label("2026-01-01"), "January 1st, 2026")
		self.assertEqual(_payroll_pay_date_label("2026-01-02"), "January 2nd, 2026")
		self.assertEqual(_payroll_pay_date_label("2026-01-03"), "January 3rd, 2026")
		self.assertEqual(_payroll_pay_date_label("2026-01-31"), "January 31st, 2026")
		self.assertEqual(_payroll_pay_date_label(None), "")

	def test_payroll_status_paid_pending_not_paid(self):
		self.assertEqual(_payroll_status(frappe._dict(docstatus=0, status="Draft")), ("pending", "Pending"))
		self.assertEqual(
			_payroll_status(frappe._dict(docstatus=1, status="Submitted", journal_entry="JE-1")),
			("paid", "Paid"),
		)
		self.assertEqual(
			_payroll_status(frappe._dict(docstatus=1, status="Submitted", payment_status="Paid")),
			("paid", "Paid"),
		)
		self.assertEqual(
			_payroll_status(frappe._dict(docstatus=1, status="Submitted", payment_status="Not Paid")),
			("unpaid", "Not Paid"),
		)

	def test_board_row_fills_zero_slip_from_attendance_and_bonus(self):
		slip = frappe._dict(
			name="SS-ZERO",
			employee="E1",
			employee_name="Ana Cruz",
			image=None,
			employee_department="Design",
			department=None,
			designation="Designer",
			start_date=getdate("2026-09-01"),
			end_date=getdate("2026-09-15"),
			gross_pay=0,
			net_pay=0,
			currency="USD",
			status="Draft",
			docstatus=0,
			journal_entry=None,
			payment_status="Not Paid",
			hour_rate=0,
			total_working_hours=0,
		)
		row = _build_payroll_board_row(slip, {}, "USD", attendance_pay=5000, extra_bonus=500)
		self.assertEqual(row["status"], "pending")
		self.assertEqual(row["status_label"], "Pending")
		self.assertEqual(row["pay_date_label"], "September 15th, 2026")
		self.assertEqual(row["base_salary"], 5000)
		self.assertEqual(row["bonus"], 500)
		self.assertEqual(row["gross_pay"], 5500)
		self.assertGreater(row["ss_contribution"], 0)
		self.assertLess(row["net_pay"], row["gross_pay"])

	def test_board_row_keeps_slip_amounts_and_adds_to_total(self):
		slip = frappe._dict(
			name="SS-PAID",
			employee="E1",
			employee_name="Jony Ive",
			image=None,
			employee_department="Design",
			department=None,
			designation="Designer",
			start_date=getdate("2026-01-01"),
			end_date=getdate("2026-01-05"),
			gross_pay=5500,
			net_pay=5500,
			currency="USD",
			status="Submitted",
			docstatus=1,
			journal_entry="JE-1",
			payment_status="Paid",
		)
		row = _build_payroll_board_row(slip, {"base": 5000, "bonus": 500, "overtime": 0}, "USD")
		self.assertEqual(row["status"], "paid")
		self.assertEqual(row["status_label"], "Paid")
		self.assertEqual(row["pay_date_label"], "January 5th, 2026")
		self.assertEqual(row["base_salary"], 5000)
		self.assertEqual(row["bonus"], 500)
		self.assertEqual(row["gross_pay"], 5500)
		self.assertGreater(row["ss_contribution"], 0)
		self.assertLess(row["net_pay"], row["gross_pay"])

	def test_board_row_uses_hourly_rate_when_gross_is_zero(self):
		slip = frappe._dict(
			name="SS-HOURLY",
			employee="E1",
			employee_name="Carlos Mendoza",
			image=None,
			employee_department="Dev",
			department=None,
			designation="Developer",
			start_date=getdate("2026-09-01"),
			end_date=getdate("2026-09-15"),
			gross_pay=0,
			net_pay=0,
			currency="USD",
			status="Submitted",
			docstatus=1,
			journal_entry=None,
			payment_status="Not Paid",
			hour_rate=12.5,
			total_working_hours=80,
		)
		row = _build_payroll_board_row(slip, {}, "USD")
		self.assertEqual(row["status"], "unpaid")
		self.assertEqual(row["status_label"], "Not Paid")
		self.assertEqual(row["base_salary"], 1000)
		self.assertEqual(row["bonus"], 0)
		self.assertEqual(row["gross_pay"], 1000)
		self.assertGreater(row["ss_contribution"], 0)
		self.assertLess(row["net_pay"], row["base_salary"])
		self.assertNotEqual(row["base_salary"], row["net_pay"])

	def test_board_row_subtracts_ss_from_total_salary(self):
		slip = frappe._dict(
			name="SS-SSB",
			employee="E1",
			employee_name="Ana Cruz",
			image=None,
			employee_department="Customer Support - SPB",
			department=None,
			designation="Agent",
			start_date=getdate("2026-09-01"),
			end_date=getdate("2026-09-15"),
			gross_pay=640,
			net_pay=640,
			currency="USD",
			status="Submitted",
			docstatus=1,
			journal_entry="JE-1",
			payment_status="Paid",
			ss_employee_amount=32,
		)
		row = _build_payroll_board_row(slip, {"base": 640, "bonus": 0, "overtime": 0}, "USD")
		self.assertEqual(row["base_salary"], 640)
		self.assertEqual(row["bonus"], 0)
		self.assertEqual(row["ss_contribution"], 32)
		self.assertEqual(row["gross_pay"], 640)
		self.assertEqual(row["net_pay"], 608)
		self.assertNotEqual(row["base_salary"], row["net_pay"])

	def test_indexed_pay_and_bonus_range(self):
		pay_index = {"E1": [(getdate("2026-09-01"), 100), (getdate("2026-09-16"), 200)]}
		self.assertEqual(_pay_in_range(pay_index, "E1", "2026-09-01", "2026-09-15"), 100)
		self.assertEqual(_pay_in_range(pay_index, "E1", "2026-09-16", "2026-09-30"), 200)
		bonus_index = {
			"E1": [
				frappe._dict(amount=500, payroll_date=getdate("2026-09-05")),
				frappe._dict(amount=80, payroll_date=getdate("2026-10-01")),
			]
		}
		self.assertEqual(_bonus_in_range(bonus_index, "E1", "2026-09-01", "2026-09-15"), 500)
		self.assertEqual(_bonus_in_range(bonus_index, "E1", "2026-10-01", "2026-10-15"), 80)

	def test_period_label_and_previous_range(self):
		start = getdate("2026-01-01")
		end = getdate("2026-01-31")
		self.assertEqual(_payroll_board_period_label(start, end), "1 January - 31 January 2026")
		self.assertEqual(_payroll_board_period_label(getdate("2025-12-15"), end), "15 December 2025 - 31 January 2026")
		prev_start, prev_end = _previous_date_range(start, end)
		self.assertEqual(prev_start, getdate("2025-12-01"))
		self.assertEqual(prev_end, getdate("2025-12-31"))

	def test_previous_pay_period_uses_listed_or_working_days(self):
		start = getdate("2026-08-11")
		listed = _previous_pay_period(
			start,
			None,
			[
				{"from_date": "2026-08-11", "to_date": "2026-08-24"},
				{"from_date": "2026-07-28", "to_date": "2026-08-10"},
			],
		)
		self.assertEqual(listed, (getdate("2026-07-28"), getdate("2026-08-10")))

		prev_start, prev_end = _previous_pay_period(start, None, None)
		self.assertEqual(prev_end, getdate("2026-08-10"))
		self.assertLessEqual(prev_start, prev_end)

	def test_upcoming_pay_period_covers_today_or_next(self):
		today = getdate()
		start, end = _upcoming_pay_period(self.company)
		self.assertLessEqual(start, end)
		self.assertGreaterEqual(end, today)

	def test_board_defaults_to_current_pay_period(self):
		payload = get_payroll_board(company=self.company)
		self.assertTrue(payload["periods"])
		current = next((row for row in payload["periods"] if row.get("current")), None)
		self.assertIsNotNone(current)
		self.assertEqual(payload["from_date"], current["from_date"])
		self.assertEqual(payload["to_date"], current["to_date"])
		self.assertGreaterEqual(getdate(current["to_date"]), getdate())

	def test_kpis_and_department_rollups(self):
		current = [
			{
				"employee": "E1",
				"status": "paid",
				"gross_pay": 1000,
				"overtime": 50,
				"base_salary": 900,
				"bonus": 100,
				"department": "Design",
			},
			{
				"employee": "E2",
				"status": "pending",
				"gross_pay": 500,
				"overtime": 0,
				"base_salary": 500,
				"bonus": 0,
				"department": "Development",
			},
		]
		previous = [
			{
				"employee": "E1",
				"status": "paid",
				"gross_pay": 800,
				"overtime": 25,
				"base_salary": 800,
				"bonus": 0,
				"department": "Design",
			}
		]
		kpis = _payroll_board_kpis(current, previous, 4, "USD")
		self.assertEqual(kpis["total_salary"]["value"], 1500)
		self.assertEqual(kpis["employees_paid"]["value"], 1)
		self.assertEqual(kpis["employees_paid"]["total"], 4)
		self.assertEqual(kpis["total_overtime"]["value"], 50)
		self.assertEqual(kpis["total_salary"]["change"], 87.5)

		departments = _payroll_board_departments(current, "USD", previous)
		self.assertEqual(departments["items"][0]["label"], "DESIGN")
		self.assertEqual(departments["items"][0]["salary"], 900)
		self.assertEqual(departments["items"][0]["bonus"], 100)
		self.assertEqual(departments["total"], 1500)
		self.assertEqual(departments["change"], 87.5)

	def test_board_reads_salary_slips_in_range(self):
		employee = make_employee(
			"dash.pay.board@example.com",
			company=self.company,
			department=self.dept,
			first_name="Pay",
			last_name="Board",
		)
		start = getdate("2026-01-01")
		end = getdate("2026-01-31")
		slip = frappe.new_doc("Salary Slip")
		slip.name = frappe.generate_hash(length=10)
		slip.employee = employee
		slip.employee_name = "Pay Board"
		slip.company = self.company
		slip.department = self.dept
		slip.posting_date = end
		slip.start_date = start
		slip.end_date = end
		slip.gross_pay = 1200
		slip.net_pay = 1100
		slip.currency = "USD"
		slip.docstatus = 1
		slip.status = "Submitted"
		slip.journal_entry = "PAY-JE-BOARD"
		slip.db_insert()

		payload = get_payroll_board(
			from_date=str(start),
			to_date=str(end),
			company=self.company,
			department=self.dept,
		)
		mine = [row for row in payload["rows"] if row["employee"] == employee]
		self.assertEqual(len(mine), 1)
		self.assertEqual(mine[0]["gross_pay"], 1200)
		self.assertEqual(mine[0]["base_salary"], 1200)
		self.assertEqual(mine[0]["bonus"], 0)
		self.assertEqual(mine[0]["status"], "paid")
		self.assertEqual(mine[0]["status_label"], "Paid")
		self.assertEqual(mine[0]["pay_date_label"], "January 31st, 2026")
		self.assertEqual(payload["kpis"]["total_salary"]["value"], 1200)
		self.assertEqual(payload["kpis"]["employees_paid"]["value"], 1)
		self.assertGreaterEqual(payload["kpis"]["employees_paid"]["total"], 1)
		self.assertTrue(payload["departments"]["items"])
		self.assertEqual(payload["period_label"], "1 January - 31 January 2026")


class TestTwelveHourClock(HRMSTestSuite):
	def test_format_clock_uses_twelve_hour(self):
		from hrms.hr.clock_format import format_clock

		self.assertEqual(format_clock("13:00:00"), "1:00 PM")
		self.assertEqual(format_clock("14:00:00"), "2:00 PM")
		self.assertEqual(format_clock("03:00:00"), "3:00 AM")
		self.assertEqual(format_clock("00:00:00"), "12:00 AM")

	def test_bootinfo_forces_twelve_hour_time_format(self):
		from hrms.boot import _force_twelve_hour_clock

		bootinfo = {"sysdefaults": {"time_format": "HH:mm:ss"}}
		_force_twelve_hour_clock(bootinfo)
		self.assertEqual(bootinfo["sysdefaults"]["time_format"], "hh:mm A")

	def test_bootinfo_forces_belize_timezone(self):
		from hrms.boot import _force_belize_timezone
		from hrms.branding import STAFF_PRO_TIMEZONE

		bootinfo = {
			"sysdefaults": {"time_zone": "Asia/Kolkata"},
			"time_zone": {"system": "Asia/Kolkata", "user": "Asia/Kolkata"},
		}
		_force_belize_timezone(bootinfo)
		self.assertEqual(bootinfo["sysdefaults"]["time_zone"], STAFF_PRO_TIMEZONE)
		self.assertEqual(bootinfo["time_zone"]["system"], STAFF_PRO_TIMEZONE)

