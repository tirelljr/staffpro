# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import date

import frappe
from frappe.utils import add_days, add_months, flt, get_year_ending, get_year_start, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.holiday_list_assignment.test_holiday_list_assignment import (
	assign_holiday_list,
)
from hrms.hr.doctype.leave_type.test_leave_type import create_leave_type
from hrms.hr.pto_anniversary import (
	PTO_DAYS,
	PTO_LEAVE_TYPE,
	PAYOUT_COMPONENT,
	process_pto_anniversaries,
	pto_money_value,
	shift_hours,
	work_year_bounds,
)
from hrms.hr.report.employee_leave_balance.employee_leave_balance import execute, get_columns
from hrms.overrides.employee_profile import get_employee_profile_stats
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list, make_leave_application
from hrms.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure
from hrms.tests.utils import HRMSTestSuite


class TestPTOAnniversary(HRMSTestSuite):
	def test_work_year_resets_on_anniversary(self):
		start, end = work_year_bounds(date(2024, 2, 29), date(2025, 3, 1))
		self.assertEqual(start, date(2025, 2, 28))
		self.assertEqual(end, date(2026, 2, 27))

	def test_agent_under_three_months_has_no_pto(self):
		as_of = date(2026, 6, 15)
		employee = self._make_agent("pto.waiting@example.com", add_months(as_of, -1))
		process_pto_anniversaries(as_of=as_of, employee=employee)

		self.assertFalse(
			frappe.db.exists(
				"Leave Allocation",
				{"employee": employee, "leave_type": PTO_LEAVE_TYPE, "docstatus": 1},
			)
		)
		self.assertEqual(get_employee_profile_stats(employee)["leave_money_remaining"], 0)

	def test_pto_money_deducts_when_days_are_taken(self):
		as_of = date(2026, 6, 15)
		joining = add_months(as_of, -4)
		employee = self._make_agent("pto.using@example.com", joining)
		process_pto_anniversaries(as_of=as_of, employee=employee)

		allocation = frappe.get_doc(
			"Leave Allocation",
			{"employee": employee, "leave_type": PTO_LEAVE_TYPE, "docstatus": 1},
		)
		self.assertEqual(flt(allocation.new_leaves_allocated), PTO_DAYS)
		self.assertEqual(cint_carry(allocation.carry_forward), 0)
		self.assertEqual(shift_hours(employee), 8)
		self.assertEqual(pto_money_value(employee, PTO_DAYS), 1200)
		self.assertEqual(get_employee_profile_stats(employee)["leave_money_remaining"], 1200)

		holiday_list = make_holiday_list(
			"PTO Anniversary Holiday List",
			get_year_start(joining),
			get_year_ending(as_of),
		)
		leave_start = _next_weekday(allocation.from_date, 0)
		with assign_holiday_list(holiday_list, "_Test Company"):
			leave = make_leave_application(
				employee,
				leave_start,
				add_days(leave_start, 1),
				PTO_LEAVE_TYPE,
			)
		self.assertEqual(flt(leave.total_leave_days), 2)
		self.assertEqual(get_employee_profile_stats(employee)["leave_money_remaining"], 960)
		self.assertEqual(
			pto_money_value(employee, PTO_DAYS) - get_employee_profile_stats(employee)["leave_money_remaining"],
			2 * 8 * 15,
		)

		create_leave_type(leave_type_name="_PTO Other Leave")
		columns = [column["fieldname"] for column in get_columns()]
		self.assertLess(columns.index("pto_money_value"), columns.index("opening_balance"))

		_columns, data, _message, _chart = execute(
			frappe._dict(
				{
					"from_date": allocation.from_date,
					"to_date": allocation.to_date,
					"employee": employee,
					"consolidate_leave_types": 0,
				}
			)
		)
		paid = next(row for row in data if row.leave_type == PTO_LEAVE_TYPE and row.employee == employee)
		other = next(row for row in data if row.leave_type == "_PTO Other Leave" and row.employee == employee)
		self.assertEqual(paid.pto_money_value, 960)
		self.assertIsNone(other.pto_money_value)

	def test_anniversary_pays_unused_days_without_carry_forward(self):
		joining = date(2025, 3, 15)
		employee = self._make_agent("pto.anniversary@example.com", joining)
		process_pto_anniversaries(as_of=date(2025, 7, 1), employee=employee)

		first = frappe.get_doc(
			"Leave Allocation",
			{"employee": employee, "leave_type": PTO_LEAVE_TYPE, "docstatus": 1},
		)
		self.assertEqual(getdate(first.to_date), date(2026, 3, 14))

		anniversary = date(2026, 3, 15)
		process_pto_anniversaries(as_of=anniversary, employee=employee)
		process_pto_anniversaries(as_of=anniversary, employee=employee)

		payouts = frappe.get_all(
			"Additional Salary",
			filters={
				"employee": employee,
				"salary_component": PAYOUT_COMPONENT,
				"ref_doctype": "Leave Allocation",
				"ref_docname": first.name,
				"docstatus": 1,
			},
			fields=["amount", "payroll_date"],
		)
		self.assertEqual(len(payouts), 1)
		self.assertEqual(flt(payouts[0].amount), 1200)
		self.assertGreaterEqual(getdate(payouts[0].payroll_date), anniversary)

		current = frappe.get_all(
			"Leave Allocation",
			filters={
				"employee": employee,
				"leave_type": PTO_LEAVE_TYPE,
				"docstatus": 1,
				"from_date": anniversary,
			},
			fields=["new_leaves_allocated", "carry_forward", "carry_forwarded_leaves_count"],
		)
		self.assertEqual(len(current), 1)
		self.assertEqual(flt(current[0].new_leaves_allocated), PTO_DAYS)
		self.assertEqual(cint_carry(current[0].carry_forward), 0)
		self.assertEqual(flt(current[0].carry_forwarded_leaves_count), 0)

	def _make_agent(self, email: str, joining) -> str:
		self._ensure_shift()
		employee = make_employee(email, company="_Test Company", date_of_joining=joining)
		frappe.db.set_value(
			"Employee",
			employee,
			{"date_of_joining": joining, "ctc": 15, "default_shift": "PTO Test Shift", "status": "Active"},
		)
		make_salary_structure(
			"PTO Structure " + email.split("@")[0],
			"Weekly",
			employee=employee,
			from_date=joining,
			company="_Test Company",
			deductions=[],
			other_details={"hour_rate": 0},
		)
		return employee

	def _ensure_shift(self):
		if frappe.db.exists("Shift Type", "PTO Test Shift"):
			return
		frappe.get_doc(
			{
				"doctype": "Shift Type",
				"__newname": "PTO Test Shift",
				"start_time": "09:00:00",
				"end_time": "17:00:00",
			}
		).insert()


def _next_weekday(start, weekday: int):
	day = getdate(start)
	while day.weekday() != weekday:
		day = add_days(day, 1)
	return day


def cint_carry(value) -> int:
	return 1 if value else 0
