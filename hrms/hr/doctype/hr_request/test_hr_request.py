# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import flt
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

	def test_letter_uses_honorific_salary_and_no_re_subject(self):
		from hrms.hr.job_letter import (
			employment_subject,
			honorific_for,
			position_label,
			salary_amounts,
			strip_re_prefix,
		)

		self.assertEqual(honorific_for("Male", "Single"), "Mr.")
		self.assertEqual(honorific_for("Female", "Married"), "Mrs.")
		self.assertEqual(honorific_for("Female", "Single"), "Ms.")
		self.assertEqual(salary_amounts(10), (20800, 800))
		self.assertEqual(salary_amounts(12.25), (25480, 980))
		self.assertEqual(position_label("Full-time", "AI Software Engineer"), "Full-Time AI Software Engineer")
		self.assertNotIn("RE:", employment_subject("Mr.", "Alex Tun"))
		self.assertEqual(strip_re_prefix("RE: Employment Verification for Mr. Alex Tun"), "Employment Verification for Mr. Alex Tun")

		employee = self._make_agent("hrreq.letter@example.com")
		self._set_letter_profile(employee.name)
		frappe.set_user(employee.user_id)
		from hrms.hr.job_letter import submit_job_letter

		created = submit_job_letter("Atlantic Bank Ltd.", "Cor. Columbus Park\nSan Ignacio")
		frappe.set_user("Administrator")
		request = frappe.get_doc("HR Request", created["name"])

		self.assertEqual(request.status, "Open")
		self.assertEqual(request.subject, "Employment Verification for Mr. Alex Tun")
		self.assertNotIn("RE:", request.subject)
		self.assertNotIn("RE:", request.letter_html)
		self.assertIn("Employment Verification for Mr. Alex Tun", request.letter_html)
		self.assertIn("<strong>Mr. Alex Tun</strong>", request.letter_html)
		self.assertIn("#607e4c", request.letter_html)
		self.assertIn("data:image/jpeg;base64,", request.letter_html)
		self.assertIn("Mr. Tun", request.letter_html)
		self.assertIn("June 22, 2026", request.letter_html)
		self.assertIn("$20,800", request.letter_html)
		self.assertIn("$800.00", request.letter_html)
		self.assertIn("Atlantic Bank Ltd.", request.letter_html)
		self.assertIn("AI Software Engineer", request.letter_html)
		if frappe.get_meta("Employee").has_field("employment_type"):
			self.assertIn("Full-Time AI Software Engineer", request.letter_html)

	def test_agent_salary_is_calculated_from_hourly_rate(self):
		employee = self._make_agent("hrreq.pay@example.com")
		self._set_letter_profile(employee.name)
		frappe.set_user(employee.user_id)
		request = frappe.get_doc(
			{
				"doctype": "HR Request",
				"employee": employee.name,
				"company": self.company,
				"request_type": "Job Letter",
				"subject": "Job Letter Request",
				"description": "Please issue a job letter for my bank.",
				"addressed_to": "Atlantic Bank Ltd.",
				"annual_salary": 1,
				"biweekly_salary": 1,
			}
		)
		request.insert()
		self.assertEqual(flt(request.annual_salary), 20800)
		self.assertEqual(flt(request.biweekly_salary), 800)

	def test_agent_cannot_attach_file_to_job_letter(self):
		from hrms.hr.job_letter import reject_agent_job_letter_attachment

		employee = self._make_agent("hrreq.attach@example.com")
		request = self._create_request(employee, as_user=employee.user_id)
		frappe.set_user(employee.user_id)
		attachment = frappe._dict(attached_to_doctype="HR Request", attached_to_name=request.name)
		self.assertRaises(frappe.ValidationError, reject_agent_job_letter_attachment, attachment)

		frappe.set_user("Administrator")
		reject_agent_job_letter_attachment(attachment)

	def test_approve_files_letter_and_office_print(self):
		from hrms.hr.job_letter import request_office_print, review_job_letter

		employee = self._make_agent("hrreq.print@example.com")
		self._set_letter_profile(employee.name)
		frappe.set_user(employee.user_id)
		from hrms.hr.job_letter import submit_job_letter

		created = submit_job_letter("Belize Bank", "Belize City")
		frappe.set_user("Administrator")
		with patch("hrms.hr.job_letter._pdf_bytes", return_value=b"%PDF-1.4"):
			reviewed = review_job_letter(created["name"], "Approve", "Issued")
		self.assertEqual(reviewed["status"], "Resolved")
		self.assertTrue(reviewed["letter_document"])
		stored = frappe.get_doc("Agent Document", reviewed["letter_document"])
		self.assertEqual(stored.category, "Job Letter")
		self.assertEqual(stored.hr_request, created["name"])
		self.assertTrue(stored.file)

		frappe.set_user(employee.user_id)
		printed = request_office_print(created["name"])
		frappe.set_user("Administrator")
		self.assertEqual(printed["request_type"], "Office Print")
		self.assertEqual(printed["status"], "Open")
		self.assertEqual(printed["source_request"], created["name"])
		self.assertNotIn("RE:", printed["subject"])

	def _set_letter_profile(self, employee):
		if not frappe.db.exists("Gender", "Male"):
			frappe.get_doc({"doctype": "Gender", "gender": "Male"}).insert(ignore_permissions=True)
		if not frappe.db.exists("Designation", "AI Software Engineer"):
			frappe.get_doc(
				{"doctype": "Designation", "designation_name": "AI Software Engineer"}
			).insert(ignore_permissions=True)
		if not frappe.db.exists("Employment Type", "Full-time"):
			frappe.get_doc({"doctype": "Employment Type", "employee_type_name": "Full-time"}).insert(
				ignore_permissions=True
			)
		frappe.db.set_value(
			"Employee",
			employee,
			{
				"first_name": "Alex",
				"last_name": "Tun",
				"employee_name": "Alex Tun",
				"gender": "Male",
				"marital_status": "Single",
				"ctc": 10,
				"date_of_joining": "2026-06-22",
				"designation": "AI Software Engineer",
				"employment_type": "Full-time",
			},
		)

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
