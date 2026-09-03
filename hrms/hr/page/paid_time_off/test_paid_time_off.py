# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.desk_dashboard import get_upcoming_absences
from hrms.hr.doctype.leave_type.test_leave_type import create_leave_type
from hrms.hr.page.paid_time_off.paid_time_off import allocate_pto, book_time_off, get_page_context
from hrms.tests.utils import HRMSTestSuite


class TestPaidTimeOff(HRMSTestSuite):
	def setUp(self):
		self.company = "_Test Company"
		if frappe.db.exists("Leave Type", "_Test PTO Vacation"):
			self.leave_type = "_Test PTO Vacation"
		else:
			self.leave_type = create_leave_type(leave_type_name="_Test PTO Vacation").name

	def _make_agent(self, email):
		return make_employee(email, company=self.company, first_name="PTO", last_name=email.split("@")[0])

	def test_page_context_lists_agent_and_reasons(self):
		employee = self._make_agent("pto.page.list@example.com")
		payload = get_page_context()
		employee_ids = {row["name"] for row in payload["employees"]}
		leave_types = {row["name"] for row in payload["leave_types"]}

		self.assertIn(employee, employee_ids)
		self.assertIn(self.leave_type, leave_types)
		self.assertTrue(payload["from_date"] < payload["to_date"])

	def test_allocate_then_book_updates_balance_and_absences(self):
		employee = self._make_agent("pto.page.book@example.com")
		from_date = getdate()
		to_date = add_days(from_date, 1)

		allocated = allocate_pto(employee, self.leave_type, days=8)
		self.assertTrue(allocated["name"])
		self.assertTrue(frappe.db.exists("Leave Allocation", allocated["name"]))

		after_allocate = get_page_context(employee)
		vacation = next(row for row in after_allocate["balances"] if row["leave_type"] == self.leave_type)
		self.assertGreaterEqual(vacation["leaves_allocated"], 8)
		self.assertGreaterEqual(vacation["closing_balance"], 8)

		booked = book_time_off(employee, self.leave_type, from_date, to_date)
		self.assertTrue(booked["name"])
		self.assertEqual(frappe.db.get_value("Leave Application", booked["name"], "status"), "Approved")

		after_book = get_page_context(employee)
		vacation = next(row for row in after_book["balances"] if row["leave_type"] == self.leave_type)
		self.assertGreater(vacation["leaves_taken"], 0)

		absence_names = {row["leave_application"] for row in after_book["absences"]}
		self.assertIn(booked["name"], absence_names)

		dashboard = get_upcoming_absences(period="yearly", company=self.company)
		dashboard_leaves = {row["leave_application"] for row in dashboard["rows"]}
		self.assertIn(booked["name"], dashboard_leaves)

	def test_allocate_adds_to_existing_grant(self):
		employee = self._make_agent("pto.page.alloc@example.com")
		first = allocate_pto(employee, self.leave_type, days=5)
		second = allocate_pto(employee, self.leave_type, days=3)

		self.assertEqual(first["name"], second["name"])
		self.assertEqual(
			frappe.db.get_value("Leave Allocation", first["name"], "new_leaves_allocated"),
			8,
		)
