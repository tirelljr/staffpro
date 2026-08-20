# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import add_days, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.patches.v16_0.add_invoicing_workspace import ensure_bpo_agent_hours_item
from hrms.payroll.auto_client_invoice import (
	get_automatic_invoice_status,
	process_automatic_invoices,
	set_automatic_invoice_interval,
)
from hrms.setup import get_custom_fields
from hrms.tests.utils import HRMSTestSuite


class TestAutoClientInvoice(HRMSTestSuite):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_custom_fields(get_custom_fields(), ignore_validate=True)

	def setUp(self):
		ensure_bpo_agent_hours_item()
		self.customer = self._ensure_customer()
		self._previous = {
			"enable_automatic_client_invoice": frappe.db.get_single_value(
				"Payroll Settings", "enable_automatic_client_invoice"
			),
			"automatic_invoice_weekly_days": frappe.db.get_single_value(
				"Payroll Settings", "automatic_invoice_weekly_days"
			),
			"automatic_invoice_fortnightly_days": frappe.db.get_single_value(
				"Payroll Settings", "automatic_invoice_fortnightly_days"
			),
			"automatic_invoice_monthly_days": frappe.db.get_single_value(
				"Payroll Settings", "automatic_invoice_monthly_days"
			),
			"automatic_payroll_company": frappe.db.get_single_value(
				"Payroll Settings", "automatic_payroll_company"
			),
			"client_invoice_item": frappe.db.get_single_value("Payroll Settings", "client_invoice_item"),
		}

	def tearDown(self):
		frappe.db.set_single_value("Payroll Settings", self._previous, update_modified=False)

	def _ensure_customer(self):
		name = "_Test BPO Client"
		if not frappe.db.exists("Customer", name):
			customer_group = (
				frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
			)
			territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
			doc = frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": name,
					"customer_type": "Company",
					"customer_group": customer_group,
					"territory": territory,
					"default_billing_rate": 10,
				}
			)
			doc.insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Customer", name, "default_billing_rate", 10)
		return name

	def _make_agent(self, email: str, rate: float) -> str:
		employee = make_employee(email, company="_Test Company")
		frappe.db.set_value(
			"Employee",
			employee,
			{
				"bill_to_customer": self.customer,
				"billing_rate": rate,
			},
		)
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

	def test_skips_when_disabled(self):
		frappe.db.set_single_value("Payroll Settings", "enable_automatic_client_invoice", 0)
		result = process_automatic_invoices(force=False)
		self.assertFalse(result["created"])
		self.assertIn("turned off", result["message"].lower())

	def test_set_automatic_invoice_interval(self):
		result = set_automatic_invoice_interval(
			weekly_days=7, fortnightly_days=14, monthly_days=30, enable=1
		)
		self.assertEqual(result["weekly_days"], 7)
		self.assertEqual(result["fortnightly_days"], 14)
		self.assertEqual(result["monthly_days"], 30)
		self.assertTrue(result["enabled"])
		self.assertEqual(
			frappe.db.get_single_value("Payroll Settings", "automatic_invoice_fortnightly_days"),
			14,
		)

	def test_status_reports_period_end(self):
		frappe.db.set_single_value(
			"Payroll Settings",
			{
				"enable_automatic_client_invoice": 1,
				"automatic_invoice_weekly_days": 0,
				"automatic_invoice_fortnightly_days": 10,
				"automatic_invoice_monthly_days": 0,
				"automatic_payroll_company": "_Test Company",
			},
			update_modified=False,
		)
		status = get_automatic_invoice_status()
		self.assertTrue(status["enabled"])
		self.assertEqual(status["interval_days"], 10)
		self.assertTrue(status["period_end"] or status["next_end"])

	def test_force_creates_invoice_from_attendance(self):
		agent = self._make_agent("test_auto_client_invoice@example.com", 20)
		end_date = add_days(getdate(), -1)
		start_date = add_days(end_date, -9)
		for offset in range(10):
			self._mark_attendance(agent, add_days(start_date, offset), "Present", 8)

		frappe.db.set_single_value(
			"Payroll Settings",
			{
				"enable_automatic_client_invoice": 1,
				"automatic_invoice_weekly_days": 0,
				"automatic_invoice_fortnightly_days": 10,
				"automatic_invoice_monthly_days": 0,
				"automatic_payroll_company": "_Test Company",
			},
			update_modified=False,
		)

		result = process_automatic_invoices(force=True)
		self.assertTrue(result["created"], result["message"])

		invoice = frappe.get_doc("Client Invoice", result["created"][0])
		self.assertEqual(invoice.docstatus, 1)
		self.assertEqual(invoice.customer, self.customer)
		self.assertTrue(invoice.sales_invoice)
		self.assertEqual((getdate(invoice.to_date) - getdate(invoice.from_date)).days, 9)
