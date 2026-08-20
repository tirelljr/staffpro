# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import add_days, flt, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.patches.v16_0.add_invoicing_workspace import ensure_bpo_agent_hours_item
from hrms.payroll.doctype.client_invoice.client_invoice import CLIENT_BILLING_CURRENCY
from hrms.setup import get_custom_fields
from hrms.tests.utils import HRMSTestSuite


class TestClientInvoice(HRMSTestSuite):
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
		values = {
			"bill_to_customer": self.customer,
			"billing_rate": rate,
		}
		if frappe.get_meta("Employee").has_field("billing_currency"):
			values["billing_currency"] = CLIENT_BILLING_CURRENCY
		frappe.db.set_value("Employee", employee, values)
		return employee

	def _mark_attendance(self, employee: str, date, status: str, working_hours: float | None = None):
		# Clear prior attendance for this employee/date so the test is re-runnable
		frappe.db.delete(
			"Attendance",
			{"employee": employee, "attendance_date": date},
		)
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

	def test_get_agents_and_submit_creates_sales_invoice(self):
		agent_a = self._make_agent("test_client_invoice_a@example.com", 25)
		agent_b = self._make_agent("test_client_invoice_b@example.com", 30)

		# Agent A: 8h Present + Half Day with blank hours → 8 + 4 = 12
		self._mark_attendance(agent_a, self.from_date, "Present", 8)
		self._mark_attendance(agent_a, add_days(self.from_date, 1), "Half Day", None)

		# Agent B: one Present day with 7.5 hours
		self._mark_attendance(agent_b, self.from_date, "Present", 7.5)

		invoice = frappe.get_doc(
			{
				"doctype": "Client Invoice",
				"customer": self.customer,
				"company": "_Test Company",
				"from_date": self.from_date,
				"to_date": self.to_date,
				"posting_date": self.to_date,
			}
		)
		invoice.insert()
		invoice.get_agents()
		invoice.save()

		self.assertEqual(invoice.currency, CLIENT_BILLING_CURRENCY)
		self.assertEqual(len(invoice.agents), 2)

		by_employee = {row.employee: row for row in invoice.agents}
		self.assertAlmostEqual(flt(by_employee[agent_a].hours), 12.0)
		self.assertAlmostEqual(flt(by_employee[agent_a].billing_rate), 25.0)
		self.assertAlmostEqual(flt(by_employee[agent_a].amount), 300.0)

		self.assertAlmostEqual(flt(by_employee[agent_b].hours), 7.5)
		self.assertAlmostEqual(flt(by_employee[agent_b].billing_rate), 30.0)
		self.assertAlmostEqual(flt(by_employee[agent_b].amount), 225.0)

		self.assertAlmostEqual(flt(invoice.total_hours), 19.5)
		self.assertAlmostEqual(flt(invoice.total_amount), 525.0)

		invoice.submit()
		invoice.reload()

		self.assertEqual(invoice.status, "Submitted")
		self.assertTrue(invoice.sales_invoice)

		si = frappe.get_doc("Sales Invoice", invoice.sales_invoice)
		self.assertEqual(si.docstatus, 1)
		self.assertEqual(si.customer, self.customer)
		self.assertEqual(si.currency, CLIENT_BILLING_CURRENCY)
		self.assertEqual(len(si.items), 2)
		self.assertAlmostEqual(flt(si.grand_total), 525.0)

		# Cancel rolls back the Sales Invoice
		invoice.cancel()
		invoice.reload()
		self.assertEqual(invoice.status, "Cancelled")
		si.reload()
		self.assertEqual(si.docstatus, 2)

	def test_adding_agent_fills_hours_rate_and_usd_amount(self):
		agent = self._make_agent("test_client_invoice_manual@example.com", 20)
		self._mark_attendance(agent, self.from_date, "Present", 6.5)

		invoice = frappe.get_doc(
			{
				"doctype": "Client Invoice",
				"customer": self.customer,
				"company": "_Test Company",
				"from_date": self.from_date,
				"to_date": self.to_date,
				"posting_date": self.to_date,
				"agents": [{"employee": agent}],
			}
		)
		invoice.insert()

		self.assertEqual(invoice.currency, CLIENT_BILLING_CURRENCY)
		self.assertEqual(len(invoice.agents), 1)
		self.assertAlmostEqual(flt(invoice.agents[0].hours), 6.5)
		self.assertAlmostEqual(flt(invoice.agents[0].billing_rate), 20.0)
		self.assertAlmostEqual(flt(invoice.agents[0].amount), 130.0)
		self.assertAlmostEqual(flt(invoice.total_hours), 6.5)
		self.assertAlmostEqual(flt(invoice.total_amount), 130.0)

		company_currency = frappe.db.get_value("Company", "_Test Company", "default_currency")
		if company_currency and company_currency != CLIENT_BILLING_CURRENCY:
			self.assertNotEqual(invoice.currency, company_currency)
