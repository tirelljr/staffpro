# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import io
import zipfile

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import add_days, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.patches.v16_0.add_invoicing_workspace import ensure_bpo_agent_hours_item
from hrms.payroll.doctype.client_invoice.client_invoice import CLIENT_BILLING_CURRENCY
from hrms.payroll.invoice_export import _load_invoices, _render_pdf_html, download_csv, download_zip
from hrms.setup import get_custom_fields
from hrms.tests.utils import HRMSTestSuite


class TestInvoiceExport(HRMSTestSuite):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_custom_fields(get_custom_fields(), ignore_validate=True)

	def setUp(self):
		frappe.db.set_single_value("HR Settings", "standard_working_hours", 8)
		ensure_bpo_agent_hours_item()
		self.customer = self._ensure_customer()
		self.from_date = getdate()
		self.to_date = add_days(self.from_date, 2)

	def _ensure_customer(self, name="_Test BPO Export Client"):
		if not frappe.db.exists("Customer", name):
			customer_group = (
				frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
			)
			territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": name,
					"customer_type": "Company",
					"customer_group": customer_group,
					"territory": territory,
					"default_billing_rate": 10,
				}
			).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Customer", name, "default_billing_rate", 10)
		return name

	def _make_agent(self, email: str, rate: float, customer: str | None = None) -> str:
		employee = make_employee(email, company="_Test Company")
		values = {
			"bill_to_customer": customer or self.customer,
			"billing_rate": rate,
		}
		if frappe.get_meta("Employee").has_field("billing_currency"):
			values["billing_currency"] = CLIENT_BILLING_CURRENCY
		frappe.db.set_value("Employee", employee, values)
		return employee

	def _mark_attendance(self, employee: str, date, status: str, working_hours: float | None = None):
		frappe.db.delete("Attendance", {"employee": employee, "attendance_date": date})
		attendance = frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": date,
				"status": status,
				"company": "_Test Company",
				"working_hours": working_hours,
			}
		)
		attendance.insert()
		attendance.submit()
		return attendance

	def _make_client_invoice(self, customer: str, email: str, hours: float, rate: float):
		agent = self._make_agent(email, rate, customer)
		self._mark_attendance(agent, self.from_date, "Present", hours)
		invoice = frappe.get_doc(
			{
				"doctype": "Client Invoice",
				"customer": customer,
				"company": "_Test Company",
				"from_date": self.from_date,
				"to_date": self.to_date,
				"posting_date": self.to_date,
			}
		)
		invoice.insert()
		invoice.get_agents()
		invoice.save()
		return invoice

	def test_client_invoice_csv_includes_agent_hours(self):
		invoice = self._make_client_invoice(self.customer, "export_csv_agent@example.com", 8, 25)
		download_csv("Client Invoice", [invoice.name])
		content = frappe.response["filecontent"]
		self.assertTrue(frappe.response["filename"].endswith(".csv"))
		self.assertIn(invoice.name, content)
		self.assertIn(self.customer, content)
		self.assertIn("25", content)

	def test_zip_export_requires_more_than_one_invoice(self):
		invoice = self._make_client_invoice(self.customer, "export_zip_one@example.com", 8, 20)
		with self.assertRaises(frappe.ValidationError):
			download_zip("Client Invoice", [invoice.name])

	def test_zip_export_contains_one_csv_per_invoice(self):
		first = self._make_client_invoice(self.customer, "export_zip_a@example.com", 8, 20)
		other_customer = self._ensure_customer("_Test BPO Export Client B")
		second = self._make_client_invoice(other_customer, "export_zip_b@example.com", 6, 30)
		download_zip("Client Invoice", [first.name, second.name])
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

	def test_pdf_html_contains_client_invoice_details(self):
		invoice = self._make_client_invoice(self.customer, "export_pdf_agent@example.com", 7.5, 18)
		invoices = _load_invoices("Client Invoice", [invoice.name])
		html = _render_pdf_html("Client Invoice", invoices)
		self.assertIn("Client Invoice", html)
		self.assertIn(invoice.name, html)
		self.assertIn(self.customer, html)

	def test_posted_invoice_csv_uses_sales_invoice_rows(self):
		invoice = self._make_client_invoice(self.customer, "export_posted_agent@example.com", 8, 22)
		invoice.submit()
		invoice.reload()
		self.assertTrue(invoice.sales_invoice)

		download_csv("Sales Invoice", [invoice.sales_invoice])
		content = frappe.response["filecontent"]
		self.assertTrue(frappe.response["filename"].endswith(".csv"))
		self.assertIn(invoice.sales_invoice, content)
		self.assertIn(self.customer, content)
		self.assertIn("Outstanding", content)
