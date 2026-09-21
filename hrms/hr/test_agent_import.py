# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import base64
import csv
import io

import frappe
from frappe.utils import getdate

from erpnext.setup.doctype.designation.test_designation import create_designation
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.agent_import import (
	build_preview,
	download_template,
	import_agents,
	map_headers,
	normalize_header,
	preview_agent_import,
	read_import_table,
)
from hrms.tests.test_utils import create_department
from hrms.tests.utils import HRMSTestSuite


def _filedata(headers, rows, filename="agents.csv"):
	buffer = io.StringIO()
	writer = csv.writer(buffer)
	writer.writerow(headers)
	for row in rows:
		writer.writerow(row)
	content = buffer.getvalue().encode("utf-8")
	return filename, base64.b64encode(content).decode()


class TestAgentImport(HRMSTestSuite):
	def setUp(self):
		self.company = "_Test Company"
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", "emp_created_by", "Full Name")
		for gender in ("Male", "Female", "Other"):
			if not frappe.db.exists("Gender", gender):
				frappe.get_doc({"doctype": "Gender", "gender": gender}).insert()
		create_department("Import Team", self.company)
		create_designation(designation_name="Import Role")

	def test_header_aliases_match_bpo_labels(self):
		self.assertEqual(normalize_header("Agent Hourly"), "agent_hourly")
		mapping, unknown = map_headers(
			["First Name", "Last Name", "Team", "Role", "Campaign", "Agent Hourly", "Mystery"]
		)
		self.assertEqual(unknown, ["Mystery"])
		self.assertEqual(mapping[0], "first_name")
		self.assertEqual(mapping[2], "department")
		self.assertEqual(mapping[3], "designation")
		self.assertEqual(mapping[4], "grade")
		self.assertEqual(mapping[5], "ctc")

	def test_preview_marks_missing_required_cells(self):
		headers, body = read_import_table(
			*_filedata(
				["First Name", "Last Name", "Gender", "Date of Birth", "Date of Joining"],
				[["", "Santos", "Female", "1995-04-12", "2024-03-01"]],
			)
		)
		preview = build_preview(headers, body)
		self.assertEqual(preview["ready_count"], 0)
		self.assertTrue(any("First Name" in error for error in preview["rows"][0]["errors"]))

	def test_preview_and_import_create_agent(self):
		stamp = frappe.generate_hash(length=6)
		first = f"Import{stamp}"
		last = "Agent"
		email = f"import.{stamp}@example.com"
		filename, filedata = _filedata(
			["First Name", "Last Name", "Gender", "Date of Birth", "Date of Joining", "Company Email", "Team", "Role"],
			[[first, last, "Female", "1994-02-18", str(getdate()), email, "Import Team", "Import Role"]],
		)
		preview = preview_agent_import(filename=filename, filedata=filedata)
		self.assertEqual(preview["ready_count"], 1, preview["rows"][0]["errors"])
		self.assertEqual(preview["rows"][0]["preview"]["first_name"], first)

		result = import_agents(filename=filename, filedata=filedata)
		self.assertEqual(result["created_count"], 1)
		name = result["created"][0]["name"]
		doc = frappe.get_doc("Employee", name)
		self.assertEqual(doc.first_name, first)
		self.assertEqual(doc.last_name, last)
		self.assertEqual(doc.company_email, email)
		self.assertTrue(doc.department)
		self.assertEqual(doc.designation, "Import Role")

	def test_import_is_blocked_until_preview_has_ready_rows(self):
		filename, filedata = _filedata(
			["First Name", "Last Name", "Gender", "Date of Birth", "Date of Joining"],
			[["NoGender", "Row", "", "1990-01-01", "2020-01-01"]],
		)
		with self.assertRaises(frappe.ValidationError):
			import_agents(filename=filename, filedata=filedata)

	def test_existing_agent_name_is_flagged_in_preview(self):
		employee = make_employee(
			"already.imported@example.com",
			company=self.company,
			first_name="Already",
			last_name="Imported",
		)
		doc = frappe.get_doc("Employee", employee)
		filename, filedata = _filedata(
			["First Name", "Last Name", "Gender", "Date of Birth", "Date of Joining"],
			[[doc.first_name, doc.last_name, "Male", "1991-06-06", "2021-01-01"]],
		)
		preview = preview_agent_import(filename=filename, filedata=filedata)
		self.assertEqual(preview["ready_count"], 0)
		self.assertTrue(any("already exists" in error.lower() for error in preview["rows"][0]["errors"]))

	def test_xlsx_template_headers_match_import_columns(self):
		download_template("xlsx")
		content = frappe.response["filecontent"]
		headers, body = read_import_table(
			"Agent_Import_Template.xlsx",
			base64.b64encode(content).decode(),
		)
		self.assertIn("First Name", headers)
		self.assertIn("Agent Hourly", headers)
		self.assertIn("Social Security Number", headers)
		self.assertTrue(body)
		_mapping, unknown = map_headers(headers)
		self.assertEqual(unknown, [])
