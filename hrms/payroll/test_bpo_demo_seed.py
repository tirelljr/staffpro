# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.bpo_employee_labels import BELIZE_EMPLOYEE_BANKS
from hrms.import_hr_demo_data import (
	DEMO_BANK_ACCOUNTS,
	EMPLOYEES,
	_apply_employee_bank_fields,
	_demo_day_plan,
	_demo_ss_number,
	_punches_until_now,
	_seed_history_day,
	_stamp_attendance_exceptions,
	_submit_open_attendance,
)
from hrms.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure
from hrms.tests.utils import HRMSTestSuite


class TestBpoDemoSeed(HRMSTestSuite):
	def test_ss_numbers_are_unique_nine_digits(self):
		first = _demo_ss_number("maria.santos@staffpro.local")
		second = _demo_ss_number("carlos.mendoza@staffpro.local")
		self.assertEqual(len(first), 9)
		self.assertTrue(first.isdigit())
		self.assertNotEqual(first, second)

	def test_demo_employees_have_unique_belize_banks(self):
		self.assertEqual(len(DEMO_BANK_ACCOUNTS), len(EMPLOYEES))
		account_nos = []
		banks = set()
		for emp in EMPLOYEES:
			row = DEMO_BANK_ACCOUNTS[emp["email"]]
			self.assertIn(row["bank"], BELIZE_EMPLOYEE_BANKS)
			self.assertTrue(row["account_no"].isdigit())
			self.assertGreaterEqual(len(row["account_no"]), 8)
			account_nos.append(row["account_no"])
			banks.add(row["bank"])
		self.assertEqual(len(account_nos), len(set(account_nos)))
		self.assertEqual(banks, set(BELIZE_EMPLOYEE_BANKS))

	def test_demo_employee_bank_fields_are_written(self):
		email = "maria.santos@staffpro.local"
		employee = make_employee(email, company="_Test Company")
		_apply_employee_bank_fields({email: employee})
		expected = DEMO_BANK_ACCOUNTS[email]
		row = frappe.db.get_value(
			"Employee", employee, ["bank_name", "bank_ac_no", "salary_mode"], as_dict=True
		)
		self.assertEqual(row.salary_mode, "Bank")
		self.assertEqual(row.bank_name, expected["bank"])
		self.assertEqual(row.bank_ac_no, expected["account_no"])

	def test_today_is_always_present_on_the_floor(self):
		self.assertEqual(_demo_day_plan(3, getdate()), "present")

	def test_live_punches_drop_clocks_in_the_future(self):
		punches = [
			("00:00:01", "IN"),
			("23:59:59", "OUT"),
		]
		kept = _punches_until_now(punches)
		self.assertTrue(kept)
		self.assertEqual(kept[0], ("00:00:01", "IN"))
		self.assertNotIn(("23:59:59", "OUT"), kept)

	def test_history_day_submits_hours_for_dashboard_cards(self):
		employee = make_employee("test_bpo_demo_hours@example.com", company="_Test Company")
		make_salary_structure(
			"BPO Demo Hours Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date=nowdate(),
			base=500,
			other_details={"hour_rate": 12.5},
		)
		day = getdate()
		if day.weekday() >= 5:
			day = add_days(day, -(day.weekday() - 4))
		self.assertTrue(_seed_history_day(0, employee, day))
		submitted = _submit_open_attendance("_Test Company", day, day)
		self.assertGreaterEqual(submitted, 1)
		name = frappe.db.get_value(
			"Attendance", {"employee": employee, "attendance_date": day, "docstatus": 1}
		)
		self.assertTrue(name)
		attendance = frappe.get_doc("Attendance", name)
		self.assertGreater(flt(attendance.working_hours), 0)
		self.assertEqual(attendance.status, "Present")

	def test_late_flag_from_sofia_start_time(self):
		employee = make_employee("test_bpo_demo_late@example.com", company="_Test Company")
		day = getdate()
		if day.weekday() >= 5:
			day = add_days(day, -(day.weekday() - 4))
		self.assertTrue(_seed_history_day(4, employee, day))
		_stamp_attendance_exceptions("_Test Company", [employee])
		row = frappe.db.get_value(
			"Attendance",
			{"employee": employee, "attendance_date": day},
			["late_entry", "in_time"],
			as_dict=True,
		)
		self.assertTrue(row)
		if row.in_time and (row.in_time.hour > 9 or (row.in_time.hour == 9 and row.in_time.minute >= 10)):
			self.assertEqual(cint_late(row.late_entry), 1)


def cint_late(value):
	from frappe.utils import cint

	return cint(value)
