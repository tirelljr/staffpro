# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import io
import zipfile

import frappe
from frappe.utils import add_days, getdate
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.payroll.salary_slip_export import (
	_render_pdf_html,
	download_csv,
	download_zip,
)
from hrms.tests.utils import HRMSTestSuite


class TestSalarySlipExport(HRMSTestSuite):
	def _make_slip(self, email: str, earning: float = 400, deduction: float = 40):
		employee = make_employee(email, company="_Test Company")
		today = getdate()
		slip = frappe.get_doc(
			{
				"doctype": "Salary Slip",
				"employee": employee,
				"employee_name": frappe.db.get_value("Employee", employee, "employee_name"),
				"company": "_Test Company",
				"posting_date": today,
				"start_date": today,
				"end_date": add_days(today, 6),
				"currency": "USD",
				"payroll_frequency": "Weekly",
				"gross_pay": earning,
				"total_deduction": deduction,
				"net_pay": earning - deduction,
				"ss_employee_amount": 10,
				"payment_status": "Not Paid",
				"earnings": [{"salary_component": "Basic", "amount": earning}],
				"deductions": [{"salary_component": "Social Security", "amount": deduction}],
			}
		)
		slip.flags.ignore_validate = True
		slip.flags.ignore_mandatory = True
		slip.flags.ignore_links = True
		slip.insert(ignore_permissions=True)
		return slip

	def test_csv_includes_pay_stub_lines(self):
		slip = self._make_slip("export_slip_csv@example.com", 425, 35)
		download_csv("Salary Slip", [slip.name])
		content = frappe.response["filecontent"]
		self.assertTrue(frappe.response["filename"].endswith(".csv"))
		self.assertIn(slip.name, content)
		self.assertIn(slip.employee_name, content)
		self.assertIn("425", content)
		self.assertIn("Basic", content)
		self.assertIn("Social Security", content)

	def test_zip_export_requires_more_than_one_slip(self):
		slip = self._make_slip("export_slip_zip_one@example.com")
		with self.assertRaises(frappe.ValidationError):
			download_zip("Salary Slip", [slip.name])

	def test_zip_export_contains_one_csv_per_slip(self):
		first = self._make_slip("export_slip_zip_a@example.com", 300, 20)
		second = self._make_slip("export_slip_zip_b@example.com", 500, 50)
		download_zip("Salary Slip", [first.name, second.name])
		self.assertTrue(frappe.response["filename"].endswith(".zip"))
		raw = frappe.response["filecontent"]
		if isinstance(raw, str):
			raw = raw.encode()
		with zipfile.ZipFile(io.BytesIO(raw)) as archive:
			names = archive.namelist()
			self.assertEqual(len(names), 2)
			contents = " ".join(archive.read(name).decode() for name in names)
			self.assertIn(first.name, contents)
			self.assertIn(second.name, contents)

	def test_export_requires_a_salary_slip(self):
		with self.assertRaises(frappe.ValidationError):
			download_csv("Salary Slip", [])

	def test_pdf_html_contains_salary_slip_details(self):
		slip = self._make_slip("export_slip_pdf@example.com", 410, 30)
		html = _render_pdf_html([slip])
		self.assertIn("Salary Slip", html)
		self.assertIn(slip.name, html)
		self.assertIn(slip.employee_name, html)
