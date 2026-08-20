# Copyright (c) 2026, Staff Pro BPO and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.attendance.attendance import add_hours_entry, approve_hours_entries, get_hours_rows
from hrms.payroll.daily_pay import get_hour_rate
from hrms.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure
from hrms.tests.utils import HRMSTestSuite


class TestDailyPay(HRMSTestSuite):
	def test_hour_rate_from_structure_and_daily_pay(self):
		employee = make_employee("test_daily_pay_rate@example.com", company="_Test Company")
		make_salary_structure(
			"Daily Pay Hourly Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date=nowdate(),
			base=500,
			other_details={"hour_rate": 12.5},
		)

		self.assertEqual(flt(get_hour_rate(employee, nowdate()), 2), 12.5)

		name = add_hours_entry(employee, nowdate(), "09:00:00", "17:00:00")
		doc = frappe.get_doc("Attendance", name)
		self.assertEqual(flt(doc.working_hours), 8)
		self.assertEqual(flt(doc.daily_pay), 100)
		self.assertFalse(cint_hours_paid(doc))

		rows = get_hours_rows(from_date=nowdate(), to_date=nowdate(), employee=employee)
		self.assertEqual(flt(rows["rows"][0]["daily_pay"]), 100)
		self.assertIn("ss_deduction", rows["rows"][0])
		self.assertEqual(rows["rows"][0]["unpaid"], 8)
		self.assertEqual(rows["rows"][0]["paid"], 0)
		self.assertEqual(rows["approval"], "Not Approved Yet")

		self.assertEqual(approve_hours_entries([name]).get("approved"), [name])
		rows = get_hours_rows(from_date=nowdate(), to_date=nowdate(), employee=employee)
		self.assertEqual(rows["rows"][0]["paid"], 8)
		self.assertEqual(rows["rows"][0]["unpaid"], 0)
		self.assertEqual(rows["approval"], "Approved")

	def test_hour_rate_from_weekly_base(self):
		employee = make_employee("test_daily_pay_base@example.com", company="_Test Company")
		make_salary_structure(
			"Daily Pay Base Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date=nowdate(),
			base=400,
			other_details={"hour_rate": 0},
		)
		self.assertEqual(flt(get_hour_rate(employee, nowdate()), 2), 10)

	def test_ss_is_weekly_not_per_punch(self):
		from frappe.utils import add_days, get_first_day_of_week, getdate

		employee = make_employee("test_weekly_ss_hours@example.com", company="_Test Company")
		make_salary_structure(
			"Weekly SS Hours Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date=nowdate(),
			base=500,
			other_details={"hour_rate": 12.5},
		)
		week_start = getdate(get_first_day_of_week(nowdate()))
		day_two = add_days(week_start, 1)
		add_hours_entry(employee, week_start, "09:00:00", "17:00:00")
		add_hours_entry(employee, day_two, "09:00:00", "17:00:00")

		payload = get_hours_rows(from_date=week_start, to_date=day_two, employee=employee)
		self.assertEqual(len(payload["rows"]), 2)
		self.assertEqual(flt(payload["rows"][0]["daily_pay"]), 100)
		self.assertEqual(flt(payload["rows"][1]["daily_pay"]), 100)
		self.assertEqual(flt(payload["rows"][0]["ss_deduction"]), 0)
		self.assertEqual(flt(payload["rows"][1]["ss_deduction"]), 0)
		self.assertEqual(flt(payload["rows"][0]["week_ss"]), 5.94)
		self.assertEqual(flt(payload["rows"][1]["week_ss"]), 5.94)
		self.assertEqual(flt(payload["totals"]["ss_deduction"]), 5.94)

		one_day = get_hours_rows(from_date=week_start, to_date=week_start, employee=employee)
		self.assertEqual(flt(one_day["totals"]["ss_deduction"]), 5.94)


def cint_hours_paid(doc):
	return int(doc.get("hours_paid") or 0)
