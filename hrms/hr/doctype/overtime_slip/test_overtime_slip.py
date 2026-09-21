# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.overtime_slip.overtime_slip import (
	DEFAULT_OVERTIME_THRESHOLD_HOURS,
	filter_employees_for_overtime_slip_creation,
	get_employee_overtime_threshold,
	get_pay_period_overtime,
	ordinary_overtime_hours,
)
from hrms.tests.utils import HRMSTestSuite


class TestOvertimeSlip(HRMSTestSuite):
	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("HR Settings", "overtime_threshold_hours", 80)
		frappe.db.set_single_value("HR Settings", "overtime_pay_multiplier", 1.5)

	def test_hours_past_period_threshold_are_overtime(self):
		self.assertEqual(ordinary_overtime_hours(9, 0, 80), 0)
		self.assertEqual(ordinary_overtime_hours(10, 70, 80), 0)
		self.assertEqual(ordinary_overtime_hours(10, 71, 80), 1)
		self.assertEqual(ordinary_overtime_hours(10, 79, 80), 9)
		self.assertEqual(ordinary_overtime_hours(10, 80, 80), 10)
		self.assertEqual(ordinary_overtime_hours(6, 80, 80), 6)
		self.assertEqual(ordinary_overtime_hours(8, 80, 80), 8)
		self.assertEqual(ordinary_overtime_hours(9.5, 0, 8), 1.5)

	def test_pay_period_threshold_boundaries(self):
		start = getdate("2026-01-05")
		employee = self.make_employee("ot-boundaries@example.com")
		self.make_attendance_days(employee, start, [9] * 5)

		result = get_pay_period_overtime(employee, start, add_days(start, 4), ensure_holidays=False)
		self.assertEqual(result["total_hours"], 45)
		self.assertEqual(result["total_overtime_duration"], 0)

		self.make_attendance_days(employee, add_days(start, 5), [8] * 5)
		result = get_pay_period_overtime(employee, start, add_days(start, 9), ensure_holidays=False)
		self.assertEqual(result["total_hours"], 85)
		self.assertEqual(result["total_overtime_duration"], 5)

		self.make_attendance(employee, add_days(start, 10), 10)
		result = get_pay_period_overtime(employee, start, add_days(start, 10), ensure_holidays=False)
		self.assertEqual(result["total_overtime_duration"], 15)
		self.assertEqual(result["allocations"][-1]["date"], add_days(start, 10))

	def test_no_overtime_at_or_below_threshold(self):
		start = getdate("2026-01-05")
		employee = self.make_employee("ot-at-threshold@example.com")
		self.make_attendance_days(employee, start, [10] * 8)
		result = get_pay_period_overtime(employee, start, add_days(start, 7), ensure_holidays=False)
		self.assertEqual(result["total_hours"], 80)
		self.assertEqual(result["total_overtime_duration"], 0)
		self.assertEqual(result["ordinary_overtime_duration"], 0)

	def test_eight_hour_days_overtime_after_eighty(self):
		start = getdate("2026-01-05")
		employee = self.make_employee("ot-80-period@example.com")
		self.make_attendance_days(employee, start, [8] * 10)
		result = get_pay_period_overtime(employee, start, add_days(start, 9), ensure_holidays=False)
		self.assertEqual(result["total_hours"], 80)
		self.assertEqual(result["total_overtime_duration"], 0)

		self.make_attendance(employee, add_days(start, 10), 8)
		result = get_pay_period_overtime(employee, start, add_days(start, 10), ensure_holidays=False)
		self.assertEqual(result["total_hours"], 88)
		self.assertEqual(result["ordinary_overtime_duration"], 8)
		self.assertEqual(result["total_overtime_duration"], 8)

	def test_pay_period_hours_do_not_carry_from_earlier_period(self):
		employee = self.make_employee("ot-month-carry@example.com")
		self.make_attendance_days(employee, getdate("2026-09-01"), [8] * 10)
		week_day = getdate("2026-09-16")
		self.make_attendance(employee, week_day, 10)

		week = get_pay_period_overtime(employee, week_day, add_days(week_day, 6), ensure_holidays=False)
		self.assertEqual(week["total_hours"], 10)
		self.assertEqual(week["total_overtime_duration"], 0)

		same_day = get_pay_period_overtime(employee, week_day, week_day, ensure_holidays=False)
		self.assertEqual(same_day["total_overtime_duration"], 0)

	def test_employee_threshold_overrides_global_default(self):
		start = getdate("2026-02-02")
		employee = self.make_employee("ot-override@example.com")
		frappe.db.set_value("Employee", employee, "overtime_threshold_hours", 60)
		self.make_attendance_days(employee, start, [8] * 7)
		self.make_attendance(employee, add_days(start, 7), 10)

		result = get_pay_period_overtime(employee, start, add_days(start, 7), ensure_holidays=False)
		self.assertEqual(result["threshold_hours"], 60)
		self.assertEqual(result["total_overtime_duration"], 6)

	def test_paid_holiday_hours_count_without_stacking_ordinary_ot(self):
		start = getdate("2026-03-02")
		employee = self.make_employee("ot-holiday@example.com")
		self.make_attendance_days(employee, start, [8] * 11)
		holiday_date = add_days(start, 10)

		def holiday_context(_employee, on_date):
			return {"pay_time_and_a_half": True, "pay_double_time": False} if getdate(on_date) == holiday_date else None

		with patch(
			"hrms.payroll.daily_pay.get_public_holiday_pay_context",
			side_effect=holiday_context,
		):
			result = get_pay_period_overtime(
				employee, start, holiday_date, ensure_holidays=False
			)

		self.assertEqual(result["total_overtime_duration"], 8)
		self.assertEqual(result["holiday_overtime_duration"], 8)
		self.assertEqual(result["ordinary_overtime_duration"], 0)
		self.assertTrue(result["allocations"][0]["is_holiday"])

	def test_overtime_slip_is_record_only(self):
		start = getdate("2026-04-06")
		employee = self.make_employee("ot-slip@example.com")
		self.make_attendance_days(employee, start, [8] * 10)
		self.make_attendance(employee, add_days(start, 10), 10)

		slip = frappe.get_doc(
			{
				"doctype": "Overtime Slip",
				"employee": employee,
				"company": "_Test Company",
				"posting_date": add_days(start, 10),
				"start_date": start,
				"end_date": add_days(start, 10),
			}
		)
		slip.get_emp_and_overtime_details()
		self.assertEqual(slip.total_overtime_duration, 10)
		self.assertEqual(len(slip.overtime_details), 1)
		slip.submit()

		self.assertFalse(
			frappe.db.exists("Additional Salary", {"ref_docname": slip.name})
		)

	def test_payroll_eligibility_uses_threshold_and_excludes_existing_period(self):
		start = getdate("2026-05-04")
		employee = self.make_employee("ot-eligibility@example.com")
		self.make_attendance_days(employee, start, [8] * 10)
		self.make_attendance(employee, add_days(start, 10), 10)
		end = add_days(start, 10)

		self.assertEqual(
			filter_employees_for_overtime_slip_creation(start, end, [employee]),
			[employee],
		)

		slip = frappe.get_doc(
			{
				"doctype": "Overtime Slip",
				"employee": employee,
				"company": "_Test Company",
				"posting_date": end,
				"start_date": start,
				"end_date": end,
			}
		)
		slip.get_emp_and_overtime_details()
		self.assertEqual(
			filter_employees_for_overtime_slip_creation(start, end, [employee]),
			[],
		)

	def test_missing_hr_settings_field_uses_default(self):
		employee = self.make_employee("ot-missing-field@example.com")
		if frappe.get_meta("Employee").has_field("overtime_threshold_hours"):
			frappe.db.set_value("Employee", employee, "overtime_threshold_hours", None)
		employee_meta = frappe.get_meta("Employee")
		hr_meta = frappe._dict(has_field=lambda _name: False)
		with patch("hrms.hr.doctype.overtime_slip.overtime_slip.frappe.get_meta") as get_meta:
			get_meta.side_effect = lambda doctype: hr_meta if doctype == "HR Settings" else employee_meta
			self.assertEqual(get_employee_overtime_threshold(employee), DEFAULT_OVERTIME_THRESHOLD_HOURS)

	def make_employee(self, email):
		employee = make_employee(email, company="_Test Company")
		if frappe.get_meta("Employee").has_field("overtime_threshold_hours"):
			frappe.db.set_value("Employee", employee, "overtime_threshold_hours", 80)
		return employee

	def make_attendance_days(self, employee, start, hours):
		for offset, value in enumerate(hours):
			self.make_attendance(employee, add_days(start, offset), value)

	def make_attendance(self, employee, attendance_date, hours):
		doc = frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": employee,
				"company": "_Test Company",
				"attendance_date": attendance_date,
				"status": "Present",
				"working_hours": hours,
			}
		)
		doc.insert()
		doc.submit()
		return doc
