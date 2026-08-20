# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

from datetime import datetime

import frappe
from frappe.utils import (
	add_days,
	add_months,
	flt,
	get_first_day,
	get_last_day,
	get_time,
	get_year_ending,
	get_year_start,
	getdate,
	nowdate,
)
from frappe.utils.user import add_role

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.attendance.attendance import (
	DuplicateAttendanceError,
	OverlappingShiftAttendanceError,
	add_absence,
	add_hours_adjustment,
	add_hours_entries,
	add_hours_entry,
	approve_hours_entries,
	cancel_hours_entries,
	cancel_hours_entry,
	get_events,
	get_hours_entry,
	get_hours_rows,
	get_hours_totals,
	get_unmarked_days,
	mark_attendance,
	mark_bulk_attendance,
	update_hours_entry,
)
from hrms.hr.doctype.holiday_list_assignment.test_holiday_list_assignment import (
	assign_holiday_list,
	create_holiday_list_assignment,
)
from hrms.tests.test_utils import get_first_sunday
from hrms.tests.utils import HRMSTestSuite


class TestAttendance(HRMSTestSuite):
	def setUp(self):
		self.holiday_list = "Salary Slip Test Holiday List"

	def test_duplicate_attendance(self):
		employee = make_employee("test_duplicate_attendance@example.com", company="_Test Company")
		date = nowdate()

		mark_attendance(employee, date, "Present")
		attendance = frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": date,
				"status": "Absent",
				"company": "_Test Company",
			}
		)

		self.assertRaises(DuplicateAttendanceError, attendance.insert)

	def test_duplicate_attendance_with_shift(self):
		from hrms.hr.doctype.shift_type.test_shift_type import setup_shift_type

		employee = make_employee("test_duplicate_attendance@example.com", company="_Test Company")
		date = nowdate()

		shift_1 = setup_shift_type(shift_type="Shift 1", start_time="08:00:00", end_time="10:00:00")
		mark_attendance(employee, date, "Present", shift=shift_1.name)

		# attendance record with shift
		attendance = frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": date,
				"status": "Absent",
				"company": "_Test Company",
				"shift": shift_1.name,
			}
		)

		self.assertRaises(DuplicateAttendanceError, attendance.insert)

		# attendance record without any shift
		attendance = frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": date,
				"status": "Absent",
				"company": "_Test Company",
			}
		)

		self.assertRaises(DuplicateAttendanceError, attendance.insert)

	def test_overlapping_shift_attendance_validation(self):
		from hrms.hr.doctype.shift_type.test_shift_type import setup_shift_type

		employee = make_employee("test_overlap_attendance@example.com", company="_Test Company")
		date = nowdate()

		shift_1 = setup_shift_type(shift_type="Shift 1", start_time="08:00:00", end_time="10:00:00")
		shift_2 = setup_shift_type(shift_type="Shift 2", start_time="09:30:00", end_time="11:00:00")

		mark_attendance(employee, date, "Present", shift=shift_1.name)

		# attendance record with overlapping shift
		attendance = frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": date,
				"status": "Absent",
				"company": "_Test Company",
				"shift": shift_2.name,
			}
		)

		self.assertRaises(OverlappingShiftAttendanceError, attendance.insert)

	def test_allow_attendance_with_different_shifts(self):
		# allows attendance with 2 different non-overlapping shifts
		from hrms.hr.doctype.shift_type.test_shift_type import setup_shift_type

		employee = make_employee("test_duplicate_attendance@example.com", company="_Test Company")
		date = nowdate()

		shift_1 = setup_shift_type(shift_type="Shift 1", start_time="08:00:00", end_time="10:00:00")
		shift_2 = setup_shift_type(shift_type="Shift 2", start_time="11:00:00", end_time="12:00:00")

		mark_attendance(employee, date, "Present", shift_1.name)
		frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": date,
				"status": "Absent",
				"company": "_Test Company",
				"shift": shift_2.name,
			}
		).insert()

	def test_mark_absent(self):
		employee = make_employee("test_mark_absent@example.com", company="_Test Company")
		date = nowdate()

		attendance = mark_attendance(employee, date, "Absent")
		fetch_attendance = frappe.get_value(
			"Attendance", {"employee": employee, "attendance_date": date, "status": "Absent"}
		)
		self.assertEqual(attendance, fetch_attendance)

	def test_unmarked_days(self):
		first_sunday = get_first_sunday(self.holiday_list, for_date=get_last_day(add_months(getdate(), -1)))
		attendance_date = add_days(first_sunday, 1)

		employee = make_employee(
			"test_unmarked_days@example.com",
			date_of_joining=add_days(attendance_date, -1),
			company="_Test Company",
		)
		frappe.db.set_value("Employee", employee, "holiday_list", self.holiday_list)

		mark_attendance(employee, attendance_date, "Present")

		unmarked_days = get_unmarked_days(
			employee, get_first_day(attendance_date), get_last_day(attendance_date)
		)
		unmarked_days = [getdate(date) for date in unmarked_days]

		# attendance already marked for the day
		self.assertNotIn(attendance_date, unmarked_days)
		# attendance unmarked
		self.assertIn(getdate(add_days(attendance_date, 1)), unmarked_days)
		# holiday considered in unmarked days
		self.assertIn(first_sunday, unmarked_days)

	@assign_holiday_list("Salary Slip Test Holiday List", "_Test Company")
	def test_unmarked_days_excluding_holidays(self):
		first_sunday = get_first_sunday(self.holiday_list, for_date=get_last_day(add_months(getdate(), -1)))
		attendance_date = add_days(first_sunday, 1)

		employee = make_employee(
			"test_unmarked_days@example.com",
			date_of_joining=add_days(attendance_date, -1),
			company="_Test Company",
		)

		mark_attendance(employee, attendance_date, "Present")

		unmarked_days = get_unmarked_days(
			employee, get_first_day(attendance_date), get_last_day(attendance_date), exclude_holidays=True
		)
		unmarked_days = [getdate(date) for date in unmarked_days]

		# attendance already marked for the day
		self.assertNotIn(attendance_date, unmarked_days)
		# attendance unmarked
		self.assertIn(getdate(add_days(attendance_date, 1)), unmarked_days)
		# holidays not considered in unmarked days
		self.assertNotIn(first_sunday, unmarked_days)

	def test_unmarked_days_excluding_holidays_across_two_holiday_list_assignments(self):
		from hrms.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list

		employee = make_employee("test_unmarked_days_exclude_holidays@example.com", company="_Test Company")
		start_date = get_first_day(getdate())
		mid_date = add_days(start_date, 15)
		end_date = get_last_day(getdate())
		holiday_list_1 = make_holiday_list(
			"First Holiday List", from_date=start_date, to_date=add_days(mid_date, -1)
		)
		holiday_list_2 = make_holiday_list("Second Holiday List", from_date=mid_date, to_date=end_date)
		create_holiday_list_assignment("Employee", employee, holiday_list=holiday_list_1)
		create_holiday_list_assignment("Employee", employee, holiday_list=holiday_list_2)

		unmarked_days = get_unmarked_days(employee, start_date, end_date, exclude_holidays=True)
		unmarked_days = [getdate(date) for date in unmarked_days]
		sunday_in_holiday_list_1 = get_first_sunday(holiday_list=holiday_list_1, for_date=start_date)
		sunday_in_holiday_list_2 = get_first_sunday(holiday_list=holiday_list_2, for_date=end_date)

		self.assertNotIn(sunday_in_holiday_list_1, unmarked_days)
		self.assertNotIn(sunday_in_holiday_list_2, unmarked_days)

	def test_unmarked_days_as_per_joining_and_relieving_dates(self):
		first_sunday = get_first_sunday(self.holiday_list, for_date=get_last_day(add_months(getdate(), -1)))
		date = add_days(first_sunday, 1)

		doj = add_days(date, 1)
		relieving_date = add_days(date, 5)
		employee = make_employee(
			"test_unmarked_days_as_per_doj@example.com",
			date_of_joining=doj,
			relieving_date=relieving_date,
			company="_Test Company",
		)

		frappe.db.set_value("Employee", employee, "holiday_list", self.holiday_list)

		attendance_date = add_days(date, 2)
		mark_attendance(employee, attendance_date, "Present")

		unmarked_days = get_unmarked_days(
			employee, get_first_day(attendance_date), get_last_day(attendance_date)
		)
		unmarked_days = [getdate(date) for date in unmarked_days]

		# attendance already marked for the day
		self.assertNotIn(attendance_date, unmarked_days)
		# date before doj not in unmarked days
		self.assertNotIn(add_days(doj, -1), unmarked_days)
		# date after relieving not in unmarked days
		self.assertNotIn(add_days(relieving_date, 1), unmarked_days)

	def test_duplicate_attendance_when_created_from_checkins_and_tool(self):
		from hrms.hr.doctype.employee_checkin.test_employee_checkin import make_checkin
		from hrms.hr.doctype.shift_type.test_shift_type import setup_shift_type

		shift = setup_shift_type(shift_type="Shift 1", start_time="08:00:00", end_time="17:00:00")
		employee = make_employee(
			"test_duplicate@attendance.com", company="_Test Company", default_shift=shift.name
		)
		mark_attendance(employee, getdate(), "Half Day", shift=shift.name, half_day_status="Absent")
		make_checkin(employee, datetime.combine(getdate(), get_time("14:00:00")))
		shift.process_auto_attendance()

		attendances = frappe.get_all(
			"Attendance",
			filters={
				"employee": employee,
				"attendance_date": getdate(),
			},
		)
		self.assertEqual(len(attendances), 1)

	def test_get_events_returns_attendance(self):
		employee = frappe.get_doc("Employee", {"first_name": "_Test Employee"})

		attendance_name = mark_attendance(employee.name, getdate(), status="Present")
		attendance = frappe.get_value("Attendance", attendance_name, "status")

		self.assertEqual(attendance, "Present")

		frappe.set_user(employee.user_id)
		try:
			events = get_events(start=getdate(), end=getdate())
		finally:
			frappe.set_user("Administrator")

		self.assertTrue(events)
		attendance_events = [e for e in events if e.get("doctype") == "Attendance"]
		self.assertTrue(attendance_events)
		self.assertEqual(attendance_events[0].get("status"), "Present")
		self.assertEqual(
			attendance_events[0].get("employee_name"),
			frappe.db.get_value("Employee", employee.name, "employee_name"),
		)
		self.assertEqual(attendance_events[0].get("attendance_date"), getdate())

	def test_bulk_attendance_marking_through_bg(self):
		user1 = "test_bg1@example.com"
		user2 = "test_bg2@example.com"
		employee1 = make_employee("test_bg1@example.com", company="_Test Company")
		employee2 = make_employee("test_bg2@example.com", company="_Test Company")
		add_role(user1, "HR Manager")
		add_role(user2, "HR Manager")
		frappe.flags.test_bg_job = True
		frappe.set_user(user1)
		data1 = frappe._dict(unmarked_days=[getdate()], employee=employee1, status="Present", shift="")
		data2 = frappe._dict(unmarked_days=[getdate()], employee=employee2, status="Present", shift="")
		mark_bulk_attendance(data1)
		self.assertStartsWith(
			frappe.message_log[-1].message, "Bulk attendance marking is queued with a background job."
		)
		frappe.set_user(user2)
		mark_bulk_attendance(data1)
		self.assertStartsWith(
			frappe.message_log[-1].message, "Bulk attendance marking is already in progress for employee"
		)
		mark_bulk_attendance(data2)
		self.assertStartsWith(
			frappe.message_log[-1].message, "Bulk attendance marking is queued with a background job."
		)
		frappe.flags.test_bg_job = False
		mark_bulk_attendance(data2)
		frappe.set_user("Administrator")
		attendance_records = frappe.get_all("Attendance", {"employee": employee2})
		self.assertEqual(len(attendance_records), 1)

	def test_add_hours_entry_creates_attendance_and_checkins(self):
		employee = make_employee("test_hours_entry@example.com", company="_Test Company")
		date = nowdate()
		name = add_hours_entry(employee, date, "09:00:00", "17:30:00")
		attendance = frappe.get_doc("Attendance", name)

		self.assertEqual(attendance.status, "Present")
		self.assertEqual(attendance.working_hours, 8.5)
		self.assertTrue(attendance.in_time)
		self.assertTrue(attendance.out_time)

		checkins = frappe.get_all(
			"Employee Checkin",
			filters={"employee": employee, "attendance": name},
			fields=["log_type"],
			order_by="time",
		)
		self.assertEqual([row.log_type for row in checkins], ["IN", "OUT"])

		totals = get_hours_totals(from_date=date, to_date=date, employee=employee)
		self.assertEqual(totals["total"], 8.5)
		self.assertEqual(totals["paid"], 0)
		self.assertEqual(totals["unpaid"], 8.5)

		payload = get_hours_rows(from_date=date, to_date=date, employee=employee)
		self.assertEqual(len(payload["rows"]), 1)
		self.assertEqual(payload["rows"][0]["name"], name)
		self.assertEqual(payload["totals"]["total"], 8.5)
		self.assertEqual(payload["rows"][0]["reg"], 8.5)
		self.assertEqual(payload["rows"][0]["paid"], 0)
		self.assertEqual(payload["rows"][0]["unpaid"], 8.5)
		self.assertEqual(payload["approval"], "Not Approved Yet")

		self.assertEqual(approve_hours_entries([name]).get("approved"), [name])
		payload = get_hours_rows(from_date=date, to_date=date, employee=employee)
		self.assertEqual(payload["rows"][0]["paid"], 8.5)
		self.assertEqual(payload["rows"][0]["unpaid"], 0)
		self.assertEqual(payload["approval"], "Approved")

		add_hours_entry(employee, add_days(date, 1), "09:00:00", "17:00:00", comment="test note")
		payload = get_hours_rows(from_date=add_days(date, 1), to_date=add_days(date, 1), employee=employee)
		self.assertTrue(payload["rows"][0]["comments"])
		self.assertEqual(payload["rows"][0]["comments"][0]["content"], "test note")

		cancel_hours_entry(name)
		self.assertFalse(frappe.db.exists("Attendance", {"name": name, "docstatus": ("<", 2)}))

	def test_update_hours_entry_changes_times(self):
		employee = make_employee("test_hours_edit@example.com", company="_Test Company")
		date = nowdate()
		name = add_hours_entry(employee, date, "09:00:00", "17:00:00", comment="first")
		new_name = update_hours_entry(name, date, "10:00:00", "18:00:00", comment="updated")
		entry = get_hours_entry(new_name)
		self.assertEqual(entry["in_time"], "10:00:00")
		self.assertEqual(entry["out_time"], "18:00:00")
		self.assertEqual(entry["comment"], "updated")

	def test_add_hours_entries_creates_for_each_employee(self):
		employee_one = make_employee("test_hours_bulk_one@example.com", company="_Test Company")
		employee_two = make_employee("test_hours_bulk_two@example.com", company="_Test Company")
		date = nowdate()
		names = add_hours_entries(
			[employee_one, employee_two],
			date,
			"09:00:00",
			"18:00:00",
		)
		self.assertEqual(len(names), 2)
		self.assertEqual(frappe.db.get_value("Attendance", names[0], "employee"), employee_one)
		self.assertEqual(frappe.db.get_value("Attendance", names[1], "employee"), employee_two)

	def test_add_hours_adjustment_updates_working_hours(self):
		employee = make_employee("test_hours_adjustment@example.com", company="_Test Company")
		date = nowdate()
		name = add_hours_entry(employee, date, "09:00:00", "17:00:00")
		add_hours_adjustment(employee, date, 1.5, "Overtime")
		self.assertEqual(flt(frappe.db.get_value("Attendance", name, "working_hours")), 9.5)
		add_hours_adjustment(employee, date, 0.5, direction="Deduction")
		self.assertEqual(flt(frappe.db.get_value("Attendance", name, "working_hours")), 9.0)

	def test_add_absence_marks_absent_days(self):
		employee = make_employee("test_hours_absence@example.com", company="_Test Company")
		date = nowdate()
		result = add_absence(employee, date, date)
		self.assertEqual(len(result["names"]), 1)
		self.assertEqual(frappe.db.get_value("Attendance", result["names"][0], "status"), "Absent")

	def test_cancel_hours_entries_removes_selected(self):
		employee = make_employee("test_hours_bulk_cancel@example.com", company="_Test Company")
		date = nowdate()
		first = add_hours_entry(employee, date, "09:00:00", "17:00:00")
		second = add_hours_entry(employee, add_days(date, 1), "09:00:00", "17:00:00")
		self.assertEqual(approve_hours_entries([first]).get("approved"), [first])
		cancel_hours_entries([first, second])
		self.assertFalse(frappe.db.exists("Attendance", {"name": first, "docstatus": ("<", 2)}))
		self.assertFalse(frappe.db.exists("Attendance", {"name": second, "docstatus": ("<", 2)}))

	def tearDown(self):
		frappe.db.rollback()
