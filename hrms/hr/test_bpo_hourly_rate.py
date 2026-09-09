# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import date
from unittest.mock import patch

import frappe
from frappe.utils import flt, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.bpo_hourly_rate import apply_hourly_rate, find_hourly_rate_targets
from hrms.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure
from hrms.tests.utils import HRMSTestSuite


class TestBPOHourlyRate(HRMSTestSuite):
	def test_apply_hourly_rate_to_other_agents(self):
		source = make_employee("hourly_source@example.com", company="_Test Company")
		other = make_employee("hourly_other@example.com", company="_Test Company")
		frappe.db.set_value("Employee", source, "ctc", 14.5)

		result = apply_hourly_rate(
			source_employee=source,
			hourly_rate=14.5,
			employees=[other],
			company="_Test Company",
		)
		self.assertEqual(result["updated"], 2)
		self.assertEqual(flt(frappe.db.get_value("Employee", other, "ctc")), 14.5)
		self.assertEqual(flt(frappe.db.get_value("Employee", source, "ctc")), 14.5)

	def test_change_this_agent_hourly_rate(self):
		source = make_employee("hourly_self@example.com", company="_Test Company")
		frappe.db.set_value("Employee", source, "ctc", 18)

		result = apply_hourly_rate(
			source_employee=source,
			hourly_rate=20.5,
			company="_Test Company",
		)
		self.assertEqual(result["updated"], 1)
		self.assertEqual(flt(frappe.db.get_value("Employee", source, "ctc")), 20.5)

	def test_apply_hourly_rate_by_branch(self):
		branch = "Hourly Rate Branch"
		if not frappe.db.exists("Branch", branch):
			frappe.get_doc({"doctype": "Branch", "branch": branch}).insert()

		source = make_employee("hourly_branch_src@example.com", company="_Test Company")
		teammate = make_employee(
			"hourly_branch_peer@example.com",
			company="_Test Company",
			branch=branch,
		)
		frappe.db.set_value("Employee", teammate, "branch", branch)

		targets = find_hourly_rate_targets(
			source_employee=source,
			branches=[branch],
			company="_Test Company",
		)
		self.assertIn(teammate, targets)
		self.assertNotIn(source, targets)

		apply_hourly_rate(
			source_employee=source,
			hourly_rate=11,
			branches=[branch],
			company="_Test Company",
		)
		self.assertEqual(flt(frappe.db.get_value("Employee", teammate, "ctc")), 11)
		self.assertEqual(flt(frappe.db.get_value("Employee", source, "ctc")), 11)

	def test_setting_agent_hourly_assigns_salary_structure(self):
		employee = make_employee("hourly_auto_ssa@example.com", company="_Test Company")
		frappe.db.sql(
			"delete from `tabSalary Structure Assignment` where employee = %s",
			employee,
		)
		make_salary_structure(
			"Hourly Auto SSA Structure",
			"Weekly",
			company="_Test Company",
			deductions=[],
			other_details={"hour_rate": 0, "is_default": "Yes"},
		)

		frappe.db.set_value("Employee", employee, "ctc", 0)
		doc = frappe.get_doc("Employee", employee)
		doc.date_of_joining = "2026-08-01"
		doc.ctc = 10
		with (
			patch(
				"hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment._salary_structure_for_employee",
				return_value="Hourly Auto SSA Structure",
			),
			patch(
				"hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment._next_unpaid_period_start",
				return_value=date(2026, 7, 20),
			),
		):
			doc.save()

		assignment = frappe.get_last_doc(
			"Salary Structure Assignment",
			filters={"employee": employee, "docstatus": 1},
		)
		self.assertEqual(assignment.salary_structure, "Hourly Auto SSA Structure")
		self.assertEqual(flt(assignment.ctc), 10)
		self.assertEqual(getdate(assignment.from_date), date(2026, 8, 1))

	def test_apply_hourly_rate_assigns_missing_structure(self):
		employee = make_employee("hourly_apply_ssa@example.com", company="_Test Company")
		frappe.db.sql(
			"delete from `tabSalary Structure Assignment` where employee = %s",
			employee,
		)
		make_salary_structure(
			"Hourly Apply SSA Structure",
			"Weekly",
			company="_Test Company",
			deductions=[],
			other_details={"hour_rate": 0, "is_default": "Yes"},
		)

		with patch(
			"hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment._salary_structure_for_employee",
			return_value="Hourly Apply SSA Structure",
		):
			result = apply_hourly_rate(
				source_employee=employee,
				hourly_rate=12.25,
				company="_Test Company",
			)
		self.assertTrue(result.get("assignments"))
		self.assertEqual(
			flt(frappe.db.get_value("Salary Structure Assignment", result["assignments"][0], "ctc")),
			12.25,
		)

	def test_from_date_uses_next_payroll_period_when_later_than_joining(self):
		employee = make_employee("hourly_period_ssa@example.com", company="_Test Company")
		frappe.db.sql(
			"delete from `tabSalary Structure Assignment` where employee = %s",
			employee,
		)
		make_salary_structure(
			"Hourly Period SSA Structure",
			"Weekly",
			company="_Test Company",
			deductions=[],
			other_details={"hour_rate": 0, "is_default": "Yes"},
		)

		frappe.db.set_value("Employee", employee, "ctc", 0)
		doc = frappe.get_doc("Employee", employee)
		doc.date_of_joining = "2026-01-15"
		doc.ctc = 9
		with (
			patch(
				"hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment._salary_structure_for_employee",
				return_value="Hourly Period SSA Structure",
			),
			patch(
				"hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment._next_unpaid_period_start",
				return_value=date(2026, 9, 7),
			),
		):
			doc.save()

		assignment = frappe.get_last_doc(
			"Salary Structure Assignment",
			filters={"employee": employee, "docstatus": 1},
		)
		self.assertEqual(getdate(assignment.from_date), date(2026, 9, 7))
