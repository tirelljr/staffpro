# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import datetime, timedelta

import frappe
from frappe.utils import add_days, getdate, now_datetime

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.attendance.attendance import mark_attendance
from hrms.hr.doctype.employee_checkin.test_employee_checkin import make_checkin
from hrms.hr.doctype.leave_type.test_leave_type import create_leave_type
from hrms.hr.doctype.shift_type.test_shift_type import setup_shift_type
from hrms.hr.page.in_out_today.in_out_today import format_late_label, get_in_out_today
from hrms.tests.test_utils import create_department
from hrms.tests.utils import HRMSTestSuite


class TestInOutToday(HRMSTestSuite):
	def setUp(self):
		self.company = "_Test Company"
		self.dept_a = create_department("In Out Dept A")
		self.dept_b = create_department("In Out Dept B")

	def test_in_out_status_and_department_filter(self):
		emp_in = make_employee(
			"inout.today.in@example.com",
			company=self.company,
			department=self.dept_a,
			first_name="InAgent",
			last_name="Today",
		)
		emp_out = make_employee(
			"inout.today.out@example.com",
			company=self.company,
			department=self.dept_a,
			first_name="OutAgent",
			last_name="Today",
		)
		emp_other = make_employee(
			"inout.today.other@example.com",
			company=self.company,
			department=self.dept_b,
			first_name="OtherDept",
			last_name="Today",
		)

		make_checkin(emp_in, time=now_datetime().replace(hour=7, minute=30, second=0, microsecond=0), log_type="IN")
		make_checkin(
			emp_other,
			time=now_datetime().replace(hour=8, minute=0, second=0, microsecond=0),
			log_type="OUT",
		)

		payload = get_in_out_today()
		by_employee = {row["employee"]: row for row in payload["details"]}

		self.assertEqual(by_employee[emp_in]["status"], "IN")
		self.assertEqual(by_employee[emp_out]["status"], "OUT")
		self.assertEqual(by_employee[emp_other]["status"], "OUT")
		self.assertTrue(by_employee[emp_in]["device_id"])
		self.assertIn(self.dept_a, payload["departments"])
		self.assertIn(self.dept_b, payload["departments"])

		filtered = get_in_out_today(department=self.dept_a)
		filtered_ids = {row["employee"] for row in filtered["details"]}
		self.assertIn(emp_in, filtered_ids)
		self.assertIn(emp_out, filtered_ids)
		self.assertNotIn(emp_other, filtered_ids)
		self.assertTrue(all(row["department"] == self.dept_a for row in filtered["details"]))
		self.assertEqual(by_employee[emp_in]["status"], "IN")
		self.assertEqual({row["department"] for row in filtered["summary"]}, {self.dept_a})
		self.assertEqual(filtered["totals"]["total"], len(filtered["details"]))
		self.assertEqual(filtered["totals"]["in_count"], sum(1 for row in filtered["details"] if row["status"] == "IN"))
		self.assertEqual(filtered["totals"]["out_count"], sum(1 for row in filtered["details"] if row["status"] == "OUT"))

	def test_late_from_shift_grace(self):
		shift = setup_shift_type(
			shift_type="In Out Late Shift",
			start_time="08:00:00",
			end_time="17:00:00",
			enable_late_entry_marking=1,
			late_entry_grace_period=10,
		)
		employee = make_employee(
			"inout.today.late@example.com",
			company=self.company,
			department=self.dept_a,
			first_name="LateAgent",
			last_name="Today",
			default_shift=shift.name,
		)
		punch_time = datetime.combine(getdate(), datetime.min.time()).replace(hour=8, minute=25)
		make_checkin(employee, time=punch_time, log_type="IN")

		payload = get_in_out_today(department=self.dept_a)
		row = next(item for item in payload["details"] if item["employee"] == employee)
		self.assertEqual(row["status"], "IN")
		self.assertTrue(row["late"])
		self.assertGreaterEqual(row["late_minutes"], 25)
		self.assertIn("minute", row["late_label"])
		self.assertGreaterEqual(payload["totals"]["late"], 1)
		dept_row = next(item for item in payload["summary"] if item["department"] == self.dept_a)
		self.assertGreaterEqual(dept_row["late"], 1)

	def test_not_clocked_in_after_start_is_late(self):
		now = now_datetime()
		shift = setup_shift_type(
			shift_type="In Out Waiting Late Shift",
			start_time=(now - timedelta(hours=1, minutes=10)).strftime("%H:%M:%S"),
			end_time=(now + timedelta(hours=6)).strftime("%H:%M:%S"),
			enable_late_entry_marking=1,
			late_entry_grace_period=10,
		)
		employee = make_employee(
			"inout.today.waiting.late@example.com",
			company=self.company,
			department=self.dept_a,
			first_name="WaitingLate",
			last_name="Today",
			default_shift=shift.name,
		)

		payload = get_in_out_today(department=self.dept_a)
		row = next(item for item in payload["details"] if item["employee"] == employee)
		self.assertEqual(row["status"], "OUT")
		self.assertTrue(row["late"])
		self.assertGreaterEqual(row["late_minutes"], 60)
		self.assertIn("hour", row["late_label"])
		self.assertGreaterEqual(payload["totals"]["late"], 1)

	def test_not_clocked_in_before_start_is_not_late(self):
		now = now_datetime()
		shift = setup_shift_type(
			shift_type="In Out Future Start Shift",
			start_time=(now + timedelta(hours=2)).strftime("%H:%M:%S"),
			end_time=(now + timedelta(hours=10)).strftime("%H:%M:%S"),
			enable_late_entry_marking=1,
			late_entry_grace_period=10,
		)
		employee = make_employee(
			"inout.today.waiting.ok@example.com",
			company=self.company,
			department=self.dept_a,
			first_name="WaitingOk",
			last_name="Today",
			default_shift=shift.name,
		)

		payload = get_in_out_today(department=self.dept_a)
		row = next(item for item in payload["details"] if item["employee"] == employee)
		self.assertEqual(row["status"], "OUT")
		self.assertFalse(row["late"])
		self.assertEqual(row["late_minutes"], 0)

	def test_approved_leave_is_not_late(self):
		now = now_datetime()
		shift = setup_shift_type(
			shift_type="In Out Leave Late Shift",
			start_time=(now - timedelta(hours=2)).strftime("%H:%M:%S"),
			end_time=(now + timedelta(hours=6)).strftime("%H:%M:%S"),
			enable_late_entry_marking=1,
			late_entry_grace_period=0,
		)
		employee = make_employee(
			"inout.today.leave.late@example.com",
			company=self.company,
			department=self.dept_b,
			first_name="LeaveLate",
			last_name="Today",
			default_shift=shift.name,
		)
		leave_type = create_leave_type(leave_type_name="_Test In Out Leave Not Late")
		today = getdate()
		leave = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": leave_type.name,
				"from_date": today,
				"to_date": today,
				"company": self.company,
				"status": "Approved",
			}
		)
		leave.flags.ignore_validate = True
		leave.insert(ignore_permissions=True)
		frappe.db.set_value(
			"Leave Application",
			leave.name,
			{"docstatus": 1, "status": "Approved"},
			update_modified=False,
		)

		payload = get_in_out_today(department=self.dept_b)
		row = next(item for item in payload["details"] if item["employee"] == employee)
		self.assertFalse(row["late"])
		self.assertEqual(row["leave_type"], leave_type.name)

	def test_format_late_label(self):
		self.assertEqual(format_late_label(15), "15 minutes")
		self.assertEqual(format_late_label(60), "1 hour")
		self.assertEqual(format_late_label(75), "1 hour 15 minutes")
		self.assertEqual(format_late_label(120), "2 hours")

	def test_pto_code_from_approved_leave(self):
		employee = make_employee(
			"inout.today.leave@example.com",
			company=self.company,
			department=self.dept_b,
			first_name="LeaveAgent",
			last_name="Today",
		)
		leave_type = create_leave_type(leave_type_name="_Test In Out Sick Leave")
		today = getdate()
		leave = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": leave_type.name,
				"from_date": today,
				"to_date": today,
				"company": self.company,
				"status": "Approved",
				"description": "DOCUMENT PROVIDED",
			}
		)
		leave.flags.ignore_validate = True
		leave.insert(ignore_permissions=True)
		frappe.db.set_value(
			"Leave Application",
			leave.name,
			{"docstatus": 1, "status": "Approved"},
			update_modified=False,
		)

		payload = get_in_out_today(department=self.dept_b)
		row = next(item for item in payload["details"] if item["employee"] == employee)
		self.assertEqual(row["status"], "OUT")
		self.assertIn("DOCUMENT PROVIDED", row["pto_code"])
		self.assertIn(leave_type.name, row["pto_code"])
		self.assertEqual(row["leave_type"], leave_type.name)

	def test_same_day_in_counts_when_time_looks_future(self):
		employee = make_employee(
			"inout.today.tzskew@example.com",
			company=self.company,
			department=self.dept_a,
			first_name="TzSkew",
			last_name="Today",
		)
		now = now_datetime()
		skewed_in = now + timedelta(hours=6)
		if getdate(skewed_in) != getdate(now):
			skewed_in = now.replace(hour=23, minute=45, second=0, microsecond=0)
		make_checkin(employee, time=skewed_in, log_type="IN")

		payload = get_in_out_today(department=self.dept_a)
		row = next(item for item in payload["details"] if item["employee"] == employee)
		self.assertEqual(row["status"], "IN")
		self.assertTrue(row["in_time"])

	def test_status_ignores_future_out_punch(self):
		employee = make_employee(
			"inout.today.future@example.com",
			company=self.company,
			department=self.dept_a,
			first_name="StillIn",
			last_name="Today",
		)
		now = now_datetime()
		make_checkin(employee, time=now - timedelta(hours=1), log_type="IN")
		make_checkin(employee, time=now + timedelta(hours=2), log_type="OUT")

		payload = get_in_out_today(department=self.dept_a)
		row = next(item for item in payload["details"] if item["employee"] == employee)
		self.assertEqual(row["status"], "IN")

	def test_status_from_attendance_when_no_checkins(self):
		employee = make_employee(
			"inout.today.attendance@example.com",
			company=self.company,
			department=self.dept_a,
			first_name="AttOnly",
			last_name="Today",
		)
		attendance = mark_attendance(employee, getdate(), "Present")
		frappe.db.set_value(
			"Attendance",
			attendance,
			"in_time",
			now_datetime() - timedelta(hours=2),
			update_modified=False,
		)

		payload = get_in_out_today(department=self.dept_a)
		row = next(item for item in payload["details"] if item["employee"] == employee)
		self.assertEqual(row["status"], "IN")
		self.assertTrue(row["time"])
		self.assertTrue(row["in_time"])

	def test_in_out_for_past_date(self):
		yesterday = add_days(getdate(), -1)
		employee = make_employee(
			"inout.today.yesterday@example.com",
			company=self.company,
			department=self.dept_a,
			first_name="Yesterday",
			last_name="Agent",
			date_of_joining=add_days(yesterday, -10),
		)
		in_time = datetime.combine(yesterday, datetime.min.time()).replace(hour=8, minute=0)
		out_time = datetime.combine(yesterday, datetime.min.time()).replace(hour=17, minute=0)
		make_checkin(employee, time=in_time, log_type="IN")
		make_checkin(employee, time=out_time, log_type="OUT")

		payload = get_in_out_today(department=self.dept_a, attendance_date=str(yesterday))
		self.assertEqual(payload["date"], str(yesterday))
		row = next(item for item in payload["details"] if item["employee"] == employee)
		self.assertEqual(row["status"], "OUT")
		self.assertTrue(row["in_time"])
		self.assertTrue(row["out_time"])
