# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils.user import add_role

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import get_hr_request_summary, get_hr_request_types, get_hr_requests
from hrms.hr.doctype.hr_request_type.hr_request_type import seed_hr_request_types
from hrms.tests.utils import HRMSTestSuite


class TestHRRequest(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		seed_hr_request_types()
		self.company = "_Test Company"

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_seed_includes_job_letter(self):
		types = {row.name for row in get_hr_request_types()}
		self.assertIn("Job Letter", types)
		self.assertIn("General Inquiry", types)

	def test_employee_can_create_job_letter_request(self):
		employee = self._make_agent("hrreq.agent@example.com")
		request = self._create_request(employee, as_user=employee.user_id)

		self.assertEqual(request.employee, employee.name)
		self.assertEqual(request.request_type, "Job Letter")
		self.assertEqual(request.status, "Open")
		self.assertTrue(request.name.startswith("HR-REQ-"))

	def test_employee_cannot_resolve_own_request(self):
		employee = self._make_agent("hrreq.noresolve@example.com")
		request = self._create_request(employee, as_user=employee.user_id)

		frappe.set_user(employee.user_id)
		request.status = "Resolved"
		self.assertRaises(frappe.ValidationError, request.save)

	def test_hr_can_assign_and_resolve(self):
		employee = self._make_agent("hrreq.resolve@example.com")
		request = self._create_request(employee)

		request.assigned_to = "Administrator"
		request.status = "In Progress"
		request.save()

		request.status = "Resolved"
		request.resolution = "Job letter issued"
		request.save()
		request.reload()

		self.assertEqual(request.status, "Resolved")
		self.assertEqual(request.assigned_to, "Administrator")
		self.assertTrue(request.resolved_on)

	def test_list_and_summary_return_only_own_rows(self):
		employee_one = self._make_agent("hrreq.one@example.com")
		employee_two = self._make_agent("hrreq.two@example.com")
		self._create_request(employee_one, subject="Agent One Letter")
		self._create_request(employee_two, subject="Agent Two Letter")

		frappe.set_user(employee_one.user_id)
		rows = get_hr_requests()
		self.assertTrue(rows)
		self.assertTrue(all(row.employee == employee_one.name for row in rows))
		self.assertTrue(any(row.subject == "Agent One Letter" for row in rows))
		self.assertFalse(any(row.subject == "Agent Two Letter" for row in rows))

		summary = get_hr_request_summary()
		self.assertGreaterEqual(summary["open"], 1)
		self.assertEqual(summary["resolved"], 0)

		letters = get_hr_requests(request_type="Job Letter")
		self.assertTrue(all(row.request_type == "Job Letter" for row in letters))

	def _make_agent(self, email):
		employee_name = make_employee(email, company=self.company)
		employee = frappe.get_doc("Employee", employee_name)
		add_role(employee.user_id, "Employee")
		return employee

	def _create_request(self, employee, as_user=None, subject="Job Letter Request"):
		if as_user:
			frappe.set_user(as_user)
		request = frappe.get_doc(
			{
				"doctype": "HR Request",
				"employee": employee.name,
				"company": self.company,
				"request_type": "Job Letter",
				"subject": subject,
				"description": "Please issue a job letter for my bank.",
				"letter_purpose": "Bank account",
				"addressed_to": "To Whom It May Concern",
			}
		)
		request.insert()
		if as_user:
			frappe.set_user("Administrator")
		return request
