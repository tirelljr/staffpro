# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from hrms.payroll.bpo_client_accounts import get_invoice_receivable_account

# Clients are billed in USD. Agent payroll stays in the company salary currency (BZD).
CLIENT_BILLING_CURRENCY = "USD"
BILLABLE_ATTENDANCE_STATUSES = ("Present", "Half Day", "Work From Home")


class ClientInvoice(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from hrms.payroll.doctype.client_invoice_item.client_invoice_item import ClientInvoiceItem

		agents: DF.Table[ClientInvoiceItem]
		amended_from: DF.Link | None
		billing_frequency: DF.Literal["Weekly", "Fortnightly", "Monthly"] | None
		company: DF.Link
		currency: DF.Link
		customer: DF.Link
		customer_name: DF.Data | None
		from_date: DF.Date
		naming_series: DF.Literal["CI-.YYYY.-"]
		payroll_entry: DF.Link | None
		posting_date: DF.Date
		sales_invoice: DF.Link | None
		status: DF.Literal["Draft", "Submitted", "Cancelled"]
		to_date: DF.Date
		total_amount: DF.Currency
		total_hours: DF.Float
	# end: auto-generated types

	def before_validate(self):
		self.set_billing_currency()
		self.fill_missing_agent_billing()
		self.calculate_totals()

	def validate(self):
		self.validate_dates()
		self.calculate_totals()
		if self.docstatus == 0:
			self.status = "Draft"

	def validate_dates(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From Date cannot be after To Date"))

	def set_billing_currency(self):
		self.currency = CLIENT_BILLING_CURRENCY

	def fill_missing_agent_billing(self):
		"""Fill hours and USD billing rate when an agent is added without values."""
		if not self.customer or not self.from_date or not self.to_date:
			return

		employees = [row.employee for row in self.agents if row.employee]
		hours_by_employee = get_hours_by_employee(employees, self.from_date, self.to_date)
		for row in self.agents:
			if not row.employee:
				continue
			if not flt(row.hours):
				row.hours = flt(hours_by_employee.get(row.employee))
			if not flt(row.billing_rate):
				row.billing_rate = get_employee_billing_rate(row.employee, self.customer)

	def calculate_totals(self):
		total_hours = 0.0
		total_amount = 0.0
		for row in self.agents:
			row.hours = flt(row.hours)
			row.billing_rate = flt(row.billing_rate)
			row.amount = flt(row.hours) * flt(row.billing_rate)
			total_hours += row.hours
			total_amount += row.amount
		self.total_hours = total_hours
		self.total_amount = total_amount

	@frappe.whitelist()
	def get_agent_billing_row(self, employee: str) -> dict:
		"""Hours, USD billing rate, and amount for one agent in this invoice period."""
		if not employee:
			return {"hours": 0, "billing_rate": 0, "amount": 0}

		hours = 0.0
		if self.from_date and self.to_date:
			hours = flt(get_hours_by_employee([employee], self.from_date, self.to_date).get(employee))
		rate = get_employee_billing_rate(employee, self.customer)
		employee_name = frappe.db.get_value("Employee", employee, "employee_name")
		return {
			"employee_name": employee_name,
			"hours": hours,
			"billing_rate": rate,
			"amount": flt(hours) * flt(rate),
		}

	@frappe.whitelist()
	def get_agents(self):
		"""Fill agents table from attendance for employees billed to this customer."""
		self.validate_dates()
		self.set_billing_currency()
		if not self.customer or not self.company:
			frappe.throw(_("Client and Company are required before fetching agents"))

		employees = frappe.get_all(
			"Employee",
			filters={
				"bill_to_customer": self.customer,
				"company": self.company,
				"status": "Active",
			},
			fields=["name", "employee_name", "billing_rate"],
		)
		if not employees:
			frappe.throw(
				_("No active agents are assigned to client {0}").format(frappe.bold(self.customer))
			)

		employee_names = [e.name for e in employees]
		hours_by_employee = get_hours_by_employee(employee_names, self.from_date, self.to_date)

		self.set("agents", [])
		for employee in employees:
			hours = flt(hours_by_employee.get(employee.name))
			if not hours:
				continue
			rate = get_employee_billing_rate(employee.name, self.customer, employee.billing_rate)
			if not rate:
				frappe.throw(
					_("Set a billing rate on agent {0} or a default billing rate on client {1}").format(
						frappe.bold(employee.employee_name or employee.name),
						frappe.bold(self.customer),
					)
				)
			self.append(
				"agents",
				{
					"employee": employee.name,
					"employee_name": employee.employee_name,
					"hours": hours,
					"billing_rate": rate,
					"amount": hours * rate,
				},
			)

		if not self.agents:
			frappe.throw(
				_("No billable attendance found for agents of {0} between {1} and {2}").format(
					frappe.bold(self.customer), self.from_date, self.to_date
				)
			)

		self.calculate_totals()
		return self

	def on_submit(self):
		if not self.agents:
			frappe.throw(_("Add at least one agent before submitting"))
		self.set_billing_currency()
		self.calculate_totals()
		sales_invoice = self.create_sales_invoice()
		self.db_set(
			{
				"sales_invoice": sales_invoice.name,
				"status": "Submitted",
			}
		)

	def on_cancel(self):
		if self.sales_invoice and frappe.db.exists("Sales Invoice", self.sales_invoice):
			si = frappe.get_doc("Sales Invoice", self.sales_invoice)
			if si.docstatus == 1:
				si.cancel()
		self.db_set("status", "Cancelled")

	def create_sales_invoice(self):
		item_code = frappe.db.get_single_value("Payroll Settings", "client_invoice_item")
		if not item_code:
			frappe.throw(
				_("Set Client Invoice Item in {0}").format(frappe.bold(_("Payroll Settings")))
			)
		if not frappe.db.exists("Item", item_code):
			frappe.throw(_("Client Invoice Item {0} does not exist").format(frappe.bold(item_code)))

		currency = self.currency or CLIENT_BILLING_CURRENCY
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		conversion_rate = get_conversion_rate(currency, company_currency, self.posting_date)

		si = frappe.new_doc("Sales Invoice")
		si.customer = self.customer
		si.company = self.company
		si.posting_date = self.posting_date
		si.due_date = self.posting_date
		if si.meta.has_field("from_date"):
			si.from_date = self.from_date
		if si.meta.has_field("to_date"):
			si.to_date = self.to_date
		if si.meta.has_field("billing_from"):
			si.billing_from = self.from_date
		if si.meta.has_field("billing_to"):
			si.billing_to = self.to_date
		si.currency = currency
		si.conversion_rate = conversion_rate
		si.plc_conversion_rate = conversion_rate
		si.set_posting_time = 1
		if si.meta.has_field("ignore_pricing_rule"):
			si.ignore_pricing_rule = 1
		receivable = get_invoice_receivable_account(self.company, self.customer, currency)
		if receivable:
			si.debit_to = receivable
		si.remarks = _("BPO agent hours from {0} to {1}").format(self.from_date, self.to_date)

		for row in self.agents:
			item_row = {
				"item_code": item_code,
				"item_name": _("Agent Hours — {0}").format(row.employee_name or row.employee),
				"description": _("BPO agent hours for {0} ({1} to {2})").format(
					row.employee_name or row.employee, self.from_date, self.to_date
				),
				"qty": flt(row.hours),
				"rate": flt(row.billing_rate),
				"uom": frappe.db.get_value("Item", item_code, "stock_uom") or "Hour",
			}
			income_account = frappe.get_cached_value("Company", self.company, "default_income_account")
			if income_account:
				item_row["income_account"] = income_account
			si.append("items", item_row)

		si.flags.ignore_permissions = True
		si.insert()
		si.submit()
		return si


def get_hours_by_employee(employees: list[str], from_date, to_date) -> dict[str, float]:
	if not employees or not from_date or not to_date:
		return {}

	standard_hours = flt(frappe.db.get_single_value("HR Settings", "standard_working_hours")) or 8.0
	attendance_rows = frappe.get_all(
		"Attendance",
		filters={
			"employee": ("in", employees),
			"attendance_date": ("between", [from_date, to_date]),
			"status": ("in", list(BILLABLE_ATTENDANCE_STATUSES)),
			"docstatus": ("<", 2),
		},
		fields=["employee", "status", "working_hours"],
	)

	hours_by_employee: dict[str, float] = {}
	for row in attendance_rows:
		hours = flt(row.working_hours)
		if not hours:
			if row.status == "Half Day":
				hours = standard_hours / 2.0
			else:
				hours = standard_hours
		hours_by_employee[row.employee] = hours_by_employee.get(row.employee, 0.0) + hours
	return hours_by_employee


def get_employee_billing_rate(employee: str, customer: str | None = None, known_rate=None) -> float:
	"""USD hourly rate billed to the client — not the agent's BZD pay rate."""
	rate = flt(known_rate)
	if not rate and employee:
		rate = flt(frappe.db.get_value("Employee", employee, "billing_rate"))
	if not rate and customer:
		rate = flt(frappe.db.get_value("Customer", customer, "default_billing_rate"))
	return rate


def get_conversion_rate(from_currency: str, to_currency: str, date) -> float:
	if not from_currency or not to_currency or from_currency == to_currency:
		return 1.0
	try:
		from erpnext.setup.utils import get_exchange_rate

		return flt(get_exchange_rate(from_currency, to_currency, date)) or 1.0
	except Exception:
		return 1.0
