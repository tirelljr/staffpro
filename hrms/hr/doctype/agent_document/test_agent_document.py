# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import base64

import frappe
from frappe.utils.user import add_role

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.agent_filesystem import (
	delete_file,
	get_my_filesystem,
	list_agents,
	list_files,
	upload_file,
)
from hrms.hr.doctype.document_category.document_category import seed_document_categories
from hrms.tests.utils import HRMSTestSuite

PDF_BYTES = b"%PDF-1.1\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


class TestAgentDocument(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		seed_document_categories()

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in frappe.get_all(
			"Agent Document",
			filters={"file_name": ["like", "filesystem-test%"]},
			pluck="name",
		):
			frappe.delete_doc("Agent Document", name, ignore_permissions=True, force=True)

	def test_seed_includes_default_categories(self):
		names = set(frappe.get_all("Document Category", pluck="name"))
		self.assertIn("Social Security", names)
		self.assertIn("Identification", names)
		self.assertIn("Bank Salary Declaration", names)
		self.assertIn("Writeups", names)

	def test_agent_uploads_are_private_and_scoped(self):
		owner = self._make_agent("filesystem.owner@example.com")
		other = self._make_agent("filesystem.other@example.com")

		frappe.set_user(owner.user_id)
		uploaded = upload_file(
			employee=owner.name,
			category="Identification",
			filename="filesystem-test-id.pdf",
			content=base64.b64encode(PDF_BYTES).decode(),
		)
		self.assertTrue(uploaded["file_url"])
		self.assertTrue(uploaded["can_delete"])

		file_doc = frappe.db.get_value(
			"File",
			{"attached_to_doctype": "Agent Document", "attached_to_name": uploaded["name"]},
			["is_private", "folder"],
			as_dict=True,
		)
		self.assertTrue(file_doc.is_private)
		self.assertIn("Identification", file_doc.folder)
		self.assertIn(owner.name, file_doc.folder)

		own_files = list_files(owner.name, "Identification")
		self.assertTrue(any(row["name"] == uploaded["name"] for row in own_files))
		mine = get_my_filesystem()
		self.assertEqual(mine["employee"], owner.name)
		identification = next(row for row in mine["categories"] if row["name"] == "Identification")
		self.assertTrue(any(row["name"] == uploaded["name"] for row in identification["files"]))

		self.assertRaises(frappe.PermissionError, list_files, other.name, "Identification")
		self.assertRaises(frappe.PermissionError, list_agents)
		self.assertRaises(
			frappe.PermissionError,
			upload_file,
			employee=other.name,
			category="Identification",
			filename="filesystem-test-other.pdf",
			content=base64.b64encode(PDF_BYTES).decode(),
		)

		frappe.set_user("Administrator")
		hr_upload = upload_file(
			employee=owner.name,
			category="Writeups",
			filename="filesystem-test-writeup.pdf",
			content=base64.b64encode(PDF_BYTES).decode(),
		)
		agents = list_agents(search=owner.employee_name)
		match = next(row for row in agents if row.name == owner.name)
		self.assertGreaterEqual(match.file_count, 2)

		frappe.set_user(owner.user_id)
		self.assertRaises(frappe.PermissionError, delete_file, hr_upload["name"])
		delete_file(uploaded["name"])
		self.assertFalse(frappe.db.exists("Agent Document", uploaded["name"]))
		self.assertTrue(frappe.db.exists("Agent Document", hr_upload["name"]))

	def _make_agent(self, email):
		employee_name = make_employee(email, company=self.company)
		employee = frappe.get_doc("Employee", employee_name)
		add_role(employee.user_id, "Employee")
		return employee
