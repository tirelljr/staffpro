# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import add_days, flt, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.patches.v16_0.add_invoicing_workspace import ensure_bpo_agent_hours_item
from hrms.payroll.auto_client_invoice import (
	create_invoices_for_payroll_entry,
	get_automatic_invoice_status,
	process_automatic_invoices,
	set_automatic_invoice_interval,
)
from hrms.payroll.auto_payroll import get_pay_period
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
		return self._ensure_named_customer("_Test BPO Client")

	def _ensure_named_customer(self, name):
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
		start_date, end_date = get_pay_period(
			interval=10,
			as_of=getdate(),
			company="_Test Company",
			last_end="",
			cycle_start=None,
		)
		day = getdate(start_date)
		while day <= getdate(end_date):
			if day.weekday() < 5:
				self._mark_attendance(agent, day, "Present", 8)
			day = add_days(day, 1)

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
		self.assertEqual(getdate(invoice.from_date), getdate(start_date))
		self.assertEqual(getdate(invoice.to_date), getdate(end_date))

	def _insert_payroll_entry(self, start_date, end_date, frequency="Fortnightly"):
		company = frappe.get_cached_doc("Company", "_Test Company")
		cost_center = company.cost_center or frappe.db.get_value(
			"Cost Center", {"company": company.name, "is_group": 0}, "name", order_by="creation"
		)
		entry = frappe.get_doc(
			{
				"doctype": "Payroll Entry",
				"company": company.name,
				"customer": self.customer,
				"posting_date": getdate(),
				"start_date": start_date,
				"end_date": end_date,
				"payroll_frequency": frequency,
				"salary_slip_based_on_timesheet": 0,
				"currency": company.default_currency,
				"exchange_rate": 1,
				"cost_center": cost_center,
				"validate_attendance": 0,
			}
		)
		entry.flags.ignore_permissions = True
		entry.insert()
		return entry

	def test_payroll_entry_creates_client_invoice(self):
		agent = self._make_agent("test_payroll_creates_invoice@example.com", 22)
		start_date = getdate()
		end_date = add_days(start_date, 4)
		self._mark_attendance(agent, start_date, "Present", 8)

		entry = self._insert_payroll_entry(start_date, end_date)
		created = create_invoices_for_payroll_entry(entry)

		self.assertTrue(created)
		invoice = frappe.get_doc("Client Invoice", created[0])
		self.assertEqual(invoice.docstatus, 1)
		self.assertEqual(invoice.customer, self.customer)
		self.assertEqual(getdate(invoice.from_date), start_date)
		self.assertEqual(getdate(invoice.to_date), end_date)
		self.assertEqual(invoice.payroll_entry, entry.name)
		self.assertTrue(invoice.sales_invoice)

	def test_payroll_entry_creates_invoice_without_attendance(self):
		customer = self._ensure_named_customer("_Test Empty Hours Client")
		employee = make_employee("test_payroll_invoice_no_hours@example.com", company="_Test Company")
		frappe.db.set_value(
			"Employee",
			employee,
			{"bill_to_customer": customer, "billing_rate": 20},
		)
		start_date = getdate()
		end_date = add_days(start_date, 4)

		entry = self._insert_payroll_entry(start_date, end_date)
		entry.customer = customer
		created = create_invoices_for_payroll_entry(entry)

		self.assertTrue(created)
		invoice = frappe.get_doc("Client Invoice", created[0])
		self.assertEqual(invoice.docstatus, 1)
		self.assertEqual(invoice.customer, customer)
		self.assertFalse(invoice.sales_invoice)
		self.assertGreaterEqual(len(invoice.agents), 1)
		self.assertAlmostEqual(flt(invoice.total_hours), 0.0)

	def test_payroll_entry_does_not_duplicate_client_invoice(self):
		agent = self._make_agent("test_payroll_invoice_dedupe@example.com", 18)
		start_date = getdate()
		end_date = add_days(start_date, 4)
		self._mark_attendance(agent, start_date, "Present", 8)

		entry = self._insert_payroll_entry(start_date, end_date)
		first = create_invoices_for_payroll_entry(entry)
		second = create_invoices_for_payroll_entry(entry)

		self.assertEqual(len(first), 1)
		self.assertEqual(second, [])
		self.assertEqual(
			frappe.db.count(
				"Client Invoice",
				{
					"customer": self.customer,
					"from_date": start_date,
					"to_date": end_date,
					"docstatus": 1,
				},
			),
			1,
		)
