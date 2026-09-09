# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import datetime
import json

from dateutil.relativedelta import relativedelta

import frappe
from frappe import _
from frappe.desk.reportview import get_match_cond
from frappe.model.document import Document
from frappe.query_builder.functions import Coalesce, Count
from frappe.utils import (
	DATE_FORMAT,
	add_days,
	add_to_date,
	cint,
	comma_and,
	date_diff,
	flt,
	fmt_money,
	formatdate,
	get_link_to_form,
	getdate,
)

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.utils import get_fiscal_year

from hrms.payroll.doctype.salary_slip.salary_slip_loan_utils import if_lending_app_installed
from hrms.payroll.doctype.salary_withholding.salary_withholding import link_bank_entry_in_salary_withholdings

ALL_CLIENTS = "All Clients"


def is_all_clients(customer) -> bool:
	"""Legacy Payroll Entry.customer sentinel. Not a real Customer/Client."""
	if not customer:
		return False
	return str(customer).strip().lower() in {ALL_CLIENTS.lower(), "all agents"}


def is_all_agents_payroll(customer) -> bool:
	"""Payroll is for agents, not clients. Empty or leftover All Clients means every agent."""
	return not customer or is_all_clients(customer)


class PayrollEntry(Document):
	# These docs keep their own records after payroll is cancelled or deleted.
	ignore_linked_doctypes = ("Client Invoice", "Payroll Settings")

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from hrms.payroll.doctype.payroll_employee_detail.payroll_employee_detail import PayrollEmployeeDetail

		amended_from: DF.Link | None
		bank_account: DF.Link | None
		branch: DF.Link | None
		company: DF.Link
		cost_center: DF.Link
		currency: DF.Link
		customer: DF.Link | None
		deduct_social_security: DF.Check
		deduct_tax_for_unsubmitted_tax_exemption_proof: DF.Check
		department: DF.Link | None
		designation: DF.Link | None
		employees: DF.Table[PayrollEmployeeDetail]
		end_date: DF.Date
		error_message: DF.SmallText | None
		exchange_rate: DF.Float
		grade: DF.Link | None
		number_of_employees: DF.Int
		overtime_step: DF.Literal["", "Create", "Submit"]
		payment_account: DF.Link | None
		payroll_frequency: DF.Literal["Weekly", "Fortnightly", "Monthly"]
		payroll_payable_account: DF.Link | None
		posting_date: DF.Date
		project: DF.Link | None
		salary_slip_based_on_timesheet: DF.Check
		salary_slips_created: DF.Check
		salary_slips_submitted: DF.Check
		start_date: DF.Date
		status: DF.Literal["Draft", "Submitted", "Cancelled", "Queued", "Failed"]
		validate_attendance: DF.Check
	# end: auto-generated types

	def onload(self):
		if self.docstatus == 0 and not self.salary_slips_created and self.employees:
			[employees_eligible_for_overtime, unsubmitted_overtime_slips] = self.get_overtime_slip_details()
			overtime_step = None
			if unsubmitted_overtime_slips:
				overtime_step = "Submit"
			elif employees_eligible_for_overtime:
				overtime_step = "Create"

			self.overtime_step = overtime_step

		if not self.docstatus == 1 or self.salary_slips_submitted:
			return

		# check if salary slips were manually submitted
		entries = frappe.db.count("Salary Slip", {"payroll_entry": self.name, "docstatus": 1})
		if cint(entries) == len(self.employees):
			self.set_onload("submitted_ss", True)

	def before_validate(self):
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default(
				"company"
			)
		# Never persist the fake "All Clients" Customer link — payroll is agent-based.
		if is_all_clients(self.customer):
			self.customer = None
		self.set_cost_center()

	def get_invalid_links(self, *args, **kwargs):
		result = super().get_invalid_links(*args, **kwargs)
		if not is_all_clients(self.customer):
			return result
		if not (isinstance(result, tuple) and len(result) == 2):
			return result
		invalid_links, cancelled_links = result
		return (
			[row for row in (invalid_links or []) if not _link_row_is_field(row, "customer")],
			[row for row in (cancelled_links or []) if not _link_row_is_field(row, "customer")],
		)

	def validate(self):
		self.number_of_employees = len(self.employees)
		self.deduct_social_security = 1
		self.sync_payment_account_from_bank()
		self.set_status()

	def sync_payment_account_from_bank(self):
		if not self.bank_account:
			return
		gl_account = frappe.db.get_value("Bank Account", self.bank_account, "account")
		if gl_account:
			self.payment_account = gl_account

	def set_cost_center(self):
		if self.cost_center or not self.company:
			return

		self.cost_center = frappe.get_cached_value("Company", self.company, "cost_center")
		if not self.cost_center:
			self.cost_center = frappe.db.get_value(
				"Cost Center", {"company": self.company, "is_group": 0}, "name", order_by="creation"
			)

	def set_status(self, status=None, update=False):
		if not status:
			status = {0: "Draft", 1: "Submitted", 2: "Cancelled"}[self.docstatus or 0]

		if update:
			self.db_set("status", status)
		else:
			self.status = status

	def before_submit(self):
		self.validate_existing_salary_slips()
		if self.get_employees_with_unmarked_attendance():
			frappe.throw(_("Cannot submit. Attendance is not marked for some employees."))

	def on_submit(self):
		self.set_status(update=True, status="Submitted")
		self.create_salary_slips()

	def validate_existing_salary_slips(self):
		if not self.employees:
			return

		existing_salary_slips = []
		SalarySlip = frappe.qb.DocType("Salary Slip")

		existing_salary_slips = (
			frappe.qb.from_(SalarySlip)
			.select(SalarySlip.employee, SalarySlip.name)
			.where(
				(SalarySlip.employee.isin([emp.employee for emp in self.employees]))
				& (SalarySlip.start_date == self.start_date)
				& (SalarySlip.end_date == self.end_date)
				& (SalarySlip.docstatus != 2)
			)
		).run(as_dict=True)

		if len(existing_salary_slips):
			msg = _("Salary Slip already exists for {0} for the given dates").format(
				comma_and([frappe.bold(d.employee) for d in existing_salary_slips])
			)
			msg += "<br><br>"
			msg += _("Reference: {0}").format(
				comma_and([get_link_to_form("Salary Slip", d.name) for d in existing_salary_slips])
			)
			frappe.throw(
				msg,
				title=_("Duplicate Entry"),
			)

	def validate_payroll_payable_account(self):
		"""Payroll Payable is no longer used; agents are paid via Bank or Cash directly."""
		return

	def before_cancel(self):
		self._allow_standalone_links()
		self.detach_standalone_links()

	def on_cancel(self):
		self._allow_standalone_links()
		self.detach_standalone_links()

		self.delete_linked_salary_slips()
		self.cancel_linked_journal_entries()
		self.cancel_linked_payment_ledger_entries()

		# reset flags & update status
		self.db_set("salary_slips_created", 0)
		self.db_set("salary_slips_submitted", 0)
		self.set_status(update=True, status="Cancelled")
		self.db_set("error_message", "")

	def on_discard(self):
		self.detach_standalone_links()
		self.db_set("status", "Cancelled")

	def delete(self):
		self.detach_standalone_links()
		return super().delete()

	def _allow_standalone_links(self):
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Salary Slip",
			"Journal Entry",
			"Client Invoice",
			"Payroll Settings",
		)

	def detach_standalone_links(self):
		"""Drop informational links so invoices and settings can stand alone."""
		self._detach_client_invoices()
		self._detach_payroll_settings()

	def _detach_client_invoices(self):
		if not self.name or not frappe.db.exists("DocType", "Client Invoice"):
			return
		if not frappe.get_meta("Client Invoice").has_field("payroll_entry"):
			return
		for invoice in frappe.get_all("Client Invoice", {"payroll_entry": self.name}, pluck="name"):
			frappe.db.set_value("Client Invoice", invoice, "payroll_entry", None, update_modified=False)

	def _detach_payroll_settings(self):
		if not self.name or not frappe.db.exists("DocType", "Payroll Settings"):
			return
		if not frappe.get_meta("Payroll Settings").has_field("last_automatic_payroll_entry"):
			return
		if frappe.db.get_single_value("Payroll Settings", "last_automatic_payroll_entry") != self.name:
			return
		frappe.db.set_single_value(
			"Payroll Settings", "last_automatic_payroll_entry", None, update_modified=False
		)

	def cancel(self):
		if len(self.get_linked_salary_slips()) > 50:
			msg = _("Payroll Entry cancellation is queued. It may take a few minutes")
			msg += "<br>"
			msg += _(
				"In case of any error during this background process, the system will add a comment about the error on this Payroll Entry and revert to the Submitted status"
			)
			frappe.msgprint(
				msg,
				indicator="blue",
				title=_("Cancellation Queued"),
			)
			self.queue_action("cancel", timeout=3000)
		else:
			self._cancel()

	def delete_linked_salary_slips(self):
		salary_slips = self.get_linked_salary_slips()

		# cancel & delete salary slips
		for salary_slip in salary_slips:
			if salary_slip.docstatus == 1:
				frappe.get_doc("Salary Slip", salary_slip.name).cancel()
			frappe.delete_doc("Salary Slip", salary_slip.name)

	def cancel_linked_journal_entries(self):
		journal_entries = frappe.get_all(
			"Journal Entry Account",
			{"reference_type": self.doctype, "reference_name": self.name, "docstatus": 1},
			pluck="parent",
			distinct=True,
		)

		# cancel Journal Entries
		for je in journal_entries:
			journal_entry_payment_ledgers = frappe.get_all(
				"Payment Ledger Entry",
				{"voucher_type": "Journal Entry", "voucher_no": je, "docstatus": 1},
				distinct=True,
			)
			# cancel linked payment ledger entry
			for pl in journal_entry_payment_ledgers:
				payment_ledger_entry = frappe.get_doc("Payment Ledger Entry", pl)
				payment_ledger_entry.flags.ignore_permissions = True
				payment_ledger_entry.cancel()

			journal_entry = frappe.get_doc("Journal Entry", je)
			journal_entry.flags.ignore_permissions = True
			journal_entry.cancel()

	def cancel_linked_payment_ledger_entries(self):
		payment_ledgers = frappe.get_all(
			"Payment Ledger Entry",
			{"against_voucher_type": self.doctype, "against_voucher_no": self.name, "docstatus": 1},
			distinct=True,
		)

		# cancel payment ledger entry
		for pl in payment_ledgers:
			payment_ledger_entry = frappe.get_doc("Payment Ledger Entry", pl)
			payment_ledger_entry.flags.ignore_permissions = True
			payment_ledger_entry.cancel()

	def get_linked_salary_slips(self):
		return frappe.get_all("Salary Slip", {"payroll_entry": self.name}, ["name", "docstatus"])

	def make_filters(self):
		filters = frappe._dict(
			company=self.company,
			customer=self.customer,
			branch=self.branch,
			department=self.department,
			designation=self.designation,
			grade=self.grade,
			currency=self.currency,
			start_date=self.start_date,
			end_date=self.end_date,
			salary_slip_based_on_timesheet=self.salary_slip_based_on_timesheet,
			payroll_frequency=self.payroll_frequency,
		)

		return filters

	@frappe.whitelist()
	def fill_employee_details(
		self, raise_if_empty: int | bool = True, customer_is_unassigned: int | bool = False
	) -> list[dict] | None:
		filters = self.make_filters()
		if cint(customer_is_unassigned):
			filters.customer_is_unassigned = 1
		employees = get_employee_list(filters=filters, as_dict=True, ignore_match_conditions=True)
		self.set("employees", [])

		if not employees:
			error_msg = _("No agents found for the mentioned criteria:")
			if self.customer and not is_all_clients(self.customer):
				error_msg += "<br>" + _("Client: {0}").format(frappe.bold(self.customer))
			if self.branch:
				error_msg += "<br>" + _("Branch: {0}").format(frappe.bold(self.branch))
			if self.department:
				error_msg += "<br>" + _("Department: {0}").format(frappe.bold(self.department))
			if self.designation:
				error_msg += "<br>" + _("Designation: {0}").format(frappe.bold(self.designation))
			if cint(raise_if_empty):
				frappe.throw(error_msg, title=_("No agents found"))
			self.number_of_employees = 0
			return None

		self.set("employees", employees)
		self.number_of_employees = len(self.employees)
		self.update_employees_with_withheld_salaries()

		return self.get_employees_with_unmarked_attendance()

	def update_employees_with_withheld_salaries(self):
		withheld_salaries = get_salary_withholdings(self.start_date, self.end_date, pluck="employee")

		for employee in self.employees:
			if employee.employee in withheld_salaries:
				employee.is_salary_withheld = 1

	@frappe.whitelist()
	def create_salary_slips(self) -> None:
		"""
		Creates salary slip for selected employees if already not created
		"""
		self.check_permission("write")
		employees = [emp.employee for emp in self.employees]

		if employees:
			args = frappe._dict(
				{
					"salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet,
					"payroll_frequency": self.payroll_frequency,
					"start_date": self.start_date,
					"end_date": self.end_date,
					"company": self.company,
					"posting_date": self.posting_date,
					"deduct_tax_for_unsubmitted_tax_exemption_proof": self.deduct_tax_for_unsubmitted_tax_exemption_proof,
					"payroll_entry": self.name,
					"exchange_rate": self.exchange_rate,
					"currency": self.currency,
				}
			)
			enqueue = (len(employees) > 30 or frappe.flags.enqueue_payroll_entry) and not getattr(
				frappe.flags, "skip_payroll_enqueue", False
			)
			if enqueue:
				self.db_set("status", "Queued")
				frappe.enqueue(
					create_salary_slips_for_employees,
					timeout=3000,
					employees=employees,
					args=args,
					publish_progress=False,
				)
				frappe.msgprint(
					_("Salary Slip creation is queued. It may take a few minutes"),
					alert=True,
					indicator="blue",
				)
			else:
				create_salary_slips_for_employees(employees, args, publish_progress=False)
				# since this method is called via frm.call this doc needs to be updated manually
				if frappe.db.exists(self.doctype, self.name):
					self.reload()

	def get_sal_slip_list(self, ss_status, as_dict=False):
		"""
		Returns list of salary slips based on selected criteria
		"""

		ss = frappe.qb.DocType("Salary Slip")
		ss_list = (
			frappe.qb.from_(ss)
			.select(ss.name, ss.salary_structure)
			.where(
				(ss.docstatus == ss_status)
				& (ss.start_date >= self.start_date)
				& (ss.end_date <= self.end_date)
				& (ss.payroll_entry == self.name)
				& ((ss.journal_entry.isnull()) | (ss.journal_entry == ""))
				& (Coalesce(ss.salary_slip_based_on_timesheet, 0) == self.salary_slip_based_on_timesheet)
			)
		).run(as_dict=as_dict)

		return ss_list

	@frappe.whitelist()
	def submit_salary_slips(self) -> None:
		self.check_permission("write")
		salary_slips = self.get_sal_slip_list(ss_status=0)

		enqueue = (len(salary_slips) > 30 or frappe.flags.enqueue_payroll_entry) and not getattr(
			frappe.flags, "skip_payroll_enqueue", False
		)
		if enqueue:
			self.db_set("status", "Queued")
			frappe.enqueue(
				submit_salary_slips_for_employees,
				timeout=3000,
				payroll_entry=self,
				salary_slips=salary_slips,
				publish_progress=False,
			)
			frappe.msgprint(
				_("Salary Slip submission is queued. It may take a few minutes"),
				alert=True,
				indicator="blue",
			)
		else:
			submit_salary_slips_for_employees(self, salary_slips, publish_progress=False)

	def email_salary_slip(self, submitted_ss):
		if frappe.db.get_single_value("Payroll Settings", "email_salary_slip_to_employee"):
			for ss in submitted_ss:
				ss.email_salary_slip()

	def get_salary_component_account(self, salary_component):
		account = frappe.db.get_value(
			"Salary Component Account",
			{"parent": salary_component, "company": self.company},
			"account",
		)

		if not account:
			account = self._ensure_salary_component_account(salary_component)

		if not account:
			frappe.throw(
				_("Please set account in Salary Component {0}").format(
					get_link_to_form("Salary Component", salary_component)
				)
			)

		return account

	def _ensure_salary_component_account(self, salary_component: str) -> str | None:
		from hrms.payroll.doctype.bonus_type.bonus_type import (
			ATTENDANCE_DEDUCTION_COMPONENT,
			BONUS_SALARY_COMPONENT,
			ensure_bonus_component_accounts,
		)
		from hrms.payroll.social_security import (
			SS_EMPLOYEE_COMPONENT,
			SS_EMPLOYER_COMPONENT,
			ensure_ss_component_accounts,
		)

		if salary_component in {SS_EMPLOYEE_COMPONENT, SS_EMPLOYER_COMPONENT}:
			ensure_ss_component_accounts(self.company)
		elif salary_component in {BONUS_SALARY_COMPONENT, ATTENDANCE_DEDUCTION_COMPONENT}:
			ensure_bonus_component_accounts(self.company)
		else:
			return None
		return frappe.db.get_value(
			"Salary Component Account",
			{"parent": salary_component, "company": self.company},
			"account",
		)

	def get_salary_components(self, component_type):
		salary_slips = self.get_sal_slip_list(ss_status=1, as_dict=True)

		if salary_slips:
			ss = frappe.qb.DocType("Salary Slip")
			ssd = frappe.qb.DocType("Salary Detail")
			salary_components = (
				frappe.qb.from_(ss)
				.join(ssd)
				.on(ss.name == ssd.parent)
				.select(
					ssd.salary_component,
					ssd.amount,
					ssd.parentfield,
					ssd.additional_salary,
					ss.salary_structure,
					ss.employee,
				)
				.where(
					(ssd.parentfield == component_type)
					& (ss.name.isin([d.name for d in salary_slips]))
					& (
						(ssd.do_not_include_in_total == 0)
						| ((ssd.do_not_include_in_total == 1) & (ssd.do_not_include_in_accounts == 0))
					)
				)
			).run(as_dict=True)

			return salary_components

	def get_salary_component_total(
		self,
		component_type=None,
		employee_wise_accounting_enabled=False,
	):
		salary_components = self.get_salary_components(component_type)
		if salary_components:
			component_dict = {}

			for item in salary_components:
				employee_cost_centers = self.get_payroll_cost_centers_for_employee(
					item.employee, item.salary_structure
				)
				employee_advance = self.get_advance_deduction(component_type, item)

				for cost_center, percentage in employee_cost_centers.items():
					amount_against_cost_center = flt(item.amount) * percentage / 100

					if employee_advance:
						self.add_advance_deduction_entry(
							item, amount_against_cost_center, cost_center, employee_advance
						)
					else:
						key = (item.salary_component, cost_center)
						component_dict[key] = component_dict.get(key, 0) + amount_against_cost_center

					if employee_wise_accounting_enabled:
						self.set_employee_based_payroll_payable_entries(
							component_type, item.employee, amount_against_cost_center
						)

			account_details = self.get_account(component_dict=component_dict)

			return account_details

	def get_advance_deduction(self, component_type: str, item: dict) -> str | None:
		if component_type == "deductions" and item.additional_salary:
			ref_doctype, ref_docname = frappe.db.get_value(
				"Additional Salary",
				item.additional_salary,
				["ref_doctype", "ref_docname"],
			)

			if ref_doctype == "Employee Advance":
				return ref_docname
		return

	def add_advance_deduction_entry(
		self,
		item: dict,
		amount: float,
		cost_center: str,
		employee_advance: str,
	) -> None:
		self._advance_deduction_entries.append(
			{
				"employee": item.employee,
				"account": self.get_salary_component_account(item.salary_component),
				"amount": amount,
				"cost_center": cost_center,
				"reference_type": "Employee Advance",
				"reference_name": employee_advance,
			}
		)

	def set_accounting_entries_for_advance_deductions(
		self,
		accounts: list,
		currencies: list,
		company_currency: str,
		accounting_dimensions: list,
		precision: int,
		payable_amount: float,
	):
		for entry in self._advance_deduction_entries:
			payable_amount = self.get_accounting_entries_and_payable_amount(
				entry.get("account"),
				entry.get("cost_center"),
				entry.get("amount"),
				currencies,
				company_currency,
				payable_amount,
				accounting_dimensions,
				precision,
				entry_type="credit",
				accounts=accounts,
				party=entry.get("employee"),
				reference_type="Employee Advance",
				reference_name=entry.get("reference_name"),
				is_advance="Yes",
			)

		return payable_amount

	def set_employee_based_payroll_payable_entries(
		self, component_type, employee, amount, salary_structure=None
	):
		employee_details = self.employee_based_payroll_payable_entries.setdefault(employee, {})

		employee_details.setdefault(component_type, 0)
		employee_details[component_type] += amount

		if salary_structure and "salary_structure" not in employee_details:
			employee_details["salary_structure"] = salary_structure

	def get_payroll_cost_centers_for_employee(self, employee, salary_structure):
		if not hasattr(self, "employee_cost_centers"):
			self.employee_cost_centers = {}

		if not self.employee_cost_centers.get(employee):
			SalaryStructureAssignment = frappe.qb.DocType("Salary Structure Assignment")
			EmployeeCostCenter = frappe.qb.DocType("Employee Cost Center")
			assignment_subquery = (
				frappe.qb.from_(SalaryStructureAssignment)
				.select(SalaryStructureAssignment.name)
				.where(
					(SalaryStructureAssignment.employee == employee)
					& (SalaryStructureAssignment.salary_structure == salary_structure)
					& (SalaryStructureAssignment.docstatus == 1)
					& (SalaryStructureAssignment.from_date <= self.end_date)
				)
				.orderby(SalaryStructureAssignment.from_date, order=frappe.qb.desc)
				.limit(1)
			)
			cost_centers = dict(
				(
					frappe.qb.from_(EmployeeCostCenter)
					.select(EmployeeCostCenter.cost_center, EmployeeCostCenter.percentage)
					.where(EmployeeCostCenter.parent == assignment_subquery)
				).run(as_list=True)
			)

			if not cost_centers:
				default_cost_center, department = frappe.get_cached_value(
					"Employee", employee, ["payroll_cost_center", "department"]
				)

				if not default_cost_center and department:
					default_cost_center = frappe.get_cached_value(
						"Department", department, "payroll_cost_center"
					)

				if not default_cost_center:
					default_cost_center = self.cost_center

				cost_centers = {default_cost_center: 100}

			self.employee_cost_centers.setdefault(employee, cost_centers)

		return self.employee_cost_centers.get(employee, {})

	def get_account(self, component_dict=None):
		account_dict = {}
		for key, amount in component_dict.items():
			component, cost_center = key
			account = self.get_salary_component_account(component)
			accounting_key = (account, cost_center)

			account_dict[accounting_key] = account_dict.get(accounting_key, 0) + amount

		return account_dict

	def make_accrual_jv_entry(self, submitted_salary_slips):
		self.check_permission("write")
		employee_wise_accounting_enabled = frappe.db.get_single_value(
			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
		)
		self.employee_based_payroll_payable_entries = {}
		self._advance_deduction_entries = []

		# Always track per-employee amounts so net pay can be split by Bank vs Cash
		earnings = (
			self.get_salary_component_total(
				component_type="earnings",
				employee_wise_accounting_enabled=True,
			)
			or {}
		)

		deductions = (
			self.get_salary_component_total(
				component_type="deductions",
				employee_wise_accounting_enabled=True,
			)
			or {}
		)

		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		if earnings or deductions:
			accounts = []
			currencies = []
			payable_amount = 0
			accounting_dimensions = get_accounting_dimensions() or []
			company_currency = erpnext.get_company_currency(self.company)

			payable_amount = self.get_payable_amount_for_earnings_and_deductions(
				accounts,
				earnings,
				deductions,
				currencies,
				company_currency,
				accounting_dimensions,
				precision,
				payable_amount,
				employee_wise_accounting_enabled,
			)

			payable_amount = self.set_accounting_entries_for_advance_deductions(
				accounts,
				currencies,
				company_currency,
				accounting_dimensions,
				precision,
				payable_amount,
			)

			payment_accounts = self.set_payable_amount_against_payment_accounts(
				accounts,
				currencies,
				company_currency,
				accounting_dimensions,
				precision,
				payable_amount,
				employee_wise_accounting_enabled,
			)

			voucher_type = self.get_direct_payment_voucher_type(payment_accounts)
			title_account = next(iter(payment_accounts), self.payment_account)

			self.make_journal_entry(
				accounts,
				currencies,
				title_account,
				voucher_type=voucher_type,
				user_remark=_("Payment Journal Entry for salaries from {0} to {1}").format(
					self.start_date, self.end_date
				),
				submit_journal_entry=True,
				submitted_salary_slips=submitted_salary_slips,
				employee_wise_accounting_enabled=employee_wise_accounting_enabled,
			)

	def get_selected_bank_gl_account(self) -> str | None:
		"""GL account for the BPO bank selected on this payroll run."""
		if self.bank_account:
			gl_account = frappe.db.get_value("Bank Account", self.bank_account, "account")
			if gl_account:
				return gl_account
		if self.payment_account:
			account_type = frappe.db.get_value("Account", self.payment_account, "account_type")
			if account_type == "Bank":
				return self.payment_account
		return None

	def get_direct_payment_account(self, salary_mode: str | None) -> str:
		"""Credit the selected BPO bank for Bank Transfer agents, or Company cash for Cash agents."""
		mode = (salary_mode or "Bank").strip()
		if mode == "Cash":
			account = frappe.db.get_value("Company", self.company, "default_cash_account")
			label = _("Default Cash Account")
			if not account:
				account_type = (
					frappe.db.get_value("Account", self.payment_account, "account_type")
					if self.payment_account
					else None
				)
				if account_type == "Cash":
					account = self.payment_account
		else:
			account = self.get_selected_bank_gl_account()
			label = _("Pay From Bank Account")
			if not account:
				from hrms.hr.belize_banks import ensure_company_default_bank_account

				account = ensure_company_default_bank_account(self.company)
				label = _("Default Bank Account")

		if not account:
			frappe.throw(
				_("Set {0} on Company {1} for payroll payments.").format(
					frappe.bold(label), frappe.bold(self.company)
				)
			)

		return account

	def get_direct_payment_voucher_type(self, payment_accounts: set | list) -> str:
		if not payment_accounts:
			return "Journal Entry"

		account_types = {
			frappe.db.get_value("Account", account, "account_type") for account in payment_accounts
		}
		account_types.discard(None)

		if account_types == {"Cash"}:
			return "Cash Entry"
		if account_types == {"Bank"}:
			return "Bank Entry"
		return "Journal Entry"

	def get_employee_salary_modes(self, employees: list[str]) -> dict[str, str]:
		if not employees:
			return {}

		modes = {}
		for row in frappe.get_all(
			"Employee", filters={"name": ("in", employees)}, fields=["name", "salary_mode"]
		):
			modes[row.name] = row.salary_mode or "Bank"
		return modes

	def set_payable_amount_against_payment_accounts(
		self,
		accounts,
		currencies,
		company_currency,
		accounting_dimensions,
		precision,
		payable_amount,
		employee_wise_accounting_enabled,
	) -> set[str]:
		"""Credit Bank/Cash directly instead of Payroll Payable, split by salary_mode."""
		employees = list(self.employee_based_payroll_payable_entries.keys())
		salary_modes = self.get_employee_salary_modes(employees)
		payment_accounts_used: set[str] = set()
		amounts_by_account: dict[str, float] = {}

		if self.employee_based_payroll_payable_entries:
			for employee, employee_details in self.employee_based_payroll_payable_entries.items():
				amount = (employee_details.get("earnings", 0) or 0) - (
					employee_details.get("deductions", 0) or 0
				)
				if not amount:
					continue
				payment_account = self.get_direct_payment_account(salary_modes.get(employee))
				amounts_by_account[payment_account] = amounts_by_account.get(payment_account, 0) + amount
		elif payable_amount:
			payment_account = self.get_direct_payment_account("Bank")
			amounts_by_account[payment_account] = payable_amount

		selected_bank_gl = self.get_selected_bank_gl_account()
		for payment_account, amount in amounts_by_account.items():
			payment_accounts_used.add(payment_account)
			# When tagging is enabled, still credit Bank/Cash without Employee party
			# (party belongs on liability accounts, not bank/cash).
			self.get_accounting_entries_and_payable_amount(
				payment_account,
				self.cost_center,
				amount,
				currencies,
				company_currency,
				0,
				accounting_dimensions,
				precision,
				entry_type="payable",
				accounts=accounts,
				bank_account=self.bank_account if payment_account == selected_bank_gl else None,
			)

		return payment_accounts_used

	def make_journal_entry(
		self,
		accounts,
		currencies,
		payroll_payable_account=None,
		voucher_type="Journal Entry",
		user_remark="",
		submitted_salary_slips: list | None = None,
		submit_journal_entry=False,
		employee_wise_accounting_enabled=False,
	) -> str:
		multi_currency = 0
		if len(currencies) > 1:
			multi_currency = 1

		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.voucher_type = voucher_type
		journal_entry.user_remark = user_remark
		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date
		# Direct Bank/Cash credits do not use Employee party on payment accounts
		journal_entry.party_not_required = True

		journal_entry.set("accounts", accounts)
		journal_entry.multi_currency = multi_currency

		if payroll_payable_account:
			journal_entry.title = payroll_payable_account

		if voucher_type in ("Bank Entry", "Cash Entry") and submit_journal_entry:
			if not journal_entry.cheque_no:
				journal_entry.cheque_no = self.name
			if not journal_entry.cheque_date:
				journal_entry.cheque_date = self.posting_date

		journal_entry.save(ignore_permissions=True)

		try:
			if submit_journal_entry:
				journal_entry.submit()

			if submitted_salary_slips:
				self.set_journal_entry_in_salary_slips(submitted_salary_slips, jv_name=journal_entry.name)

		except Exception as e:
			if type(e) in (str, list, tuple):
				frappe.msgprint(e)

			self.log_error("Journal Entry creation against Salary Slip failed")
			raise

		return journal_entry

	def get_payable_amount_for_earnings_and_deductions(
		self,
		accounts,
		earnings,
		deductions,
		currencies,
		company_currency,
		accounting_dimensions,
		precision,
		payable_amount,
		employee_wise_accounting_enabled,
	):
		# Earnings
		for acc_cc, amount in earnings.items():
			payable_amount = self.get_accounting_entries_and_payable_amount(
				acc_cc[0],
				acc_cc[1] or self.cost_center,
				amount,
				currencies,
				company_currency,
				payable_amount,
				accounting_dimensions,
				precision,
				entry_type="debit",
				accounts=accounts,
			)

		# Deductions
		for acc_cc, amount in deductions.items():
			payable_amount = self.get_accounting_entries_and_payable_amount(
				acc_cc[0],
				acc_cc[1] or self.cost_center,
				amount,
				currencies,
				company_currency,
				payable_amount,
				accounting_dimensions,
				precision,
				entry_type="credit",
				accounts=accounts,
			)

		return payable_amount

	def set_payable_amount_against_payroll_payable_account(
		self,
		accounts,
		currencies,
		company_currency,
		accounting_dimensions,
		precision,
		payable_amount,
		payroll_payable_account,
		employee_wise_accounting_enabled,
	):
		# Payable amount
		if employee_wise_accounting_enabled:
			"""
			employee_based_payroll_payable_entries = {
			                'HREMP00004': {
			                                'earnings': 83332.0,
			                                'deductions': 2000.0
			                },
			                'HREMP00005': {
			                                'earnings': 50000.0,
			                                'deductions': 2000.0
			                }
			}
			"""
			for employee, employee_details in self.employee_based_payroll_payable_entries.items():
				payable_amount = (employee_details.get("earnings", 0) or 0) - (
					employee_details.get("deductions", 0) or 0
				)

				payable_amount = self.get_accounting_entries_and_payable_amount(
					payroll_payable_account,
					self.cost_center,
					payable_amount,
					currencies,
					company_currency,
					0,
					accounting_dimensions,
					precision,
					entry_type="payable",
					party=employee,
					accounts=accounts,
				)
		else:
			payable_amount = self.get_accounting_entries_and_payable_amount(
				payroll_payable_account,
				self.cost_center,
				payable_amount,
				currencies,
				company_currency,
				0,
				accounting_dimensions,
				precision,
				entry_type="payable",
				accounts=accounts,
			)

	def get_accounting_entries_and_payable_amount(
		self,
		account,
		cost_center,
		amount,
		currencies,
		company_currency,
		payable_amount,
		accounting_dimensions,
		precision,
		entry_type="credit",
		party=None,
		accounts=None,
		reference_type=None,
		reference_name=None,
		is_advance=None,
		bank_account=None,
	):
		exchange_rate, amt = self.get_amount_and_exchange_rate_for_journal_entry(
			account, amount, company_currency, currencies
		)

		row = {
			"account": account,
			"exchange_rate": flt(exchange_rate),
			"cost_center": cost_center,
			"project": self.project,
		}
		if bank_account:
			row["bank_account"] = bank_account

		if entry_type == "debit":
			payable_amount += flt(amount, precision)
			row.update(
				{
					"debit_in_account_currency": flt(amt, precision),
				}
			)
		elif entry_type == "credit":
			payable_amount -= flt(amount, precision)
			row.update(
				{
					"credit_in_account_currency": flt(amt, precision),
				}
			)
		else:
			row.update(
				{
					"credit_in_account_currency": flt(amt, precision),
					"reference_type": self.doctype,
					"reference_name": self.name,
				}
			)

		if party:
			row.update(
				{
					"party_type": "Employee",
					"party": party,
				}
			)

		if reference_type:
			row.update(
				{
					"reference_type": reference_type,
					"reference_name": reference_name,
					"is_advance": is_advance,
				}
			)

		self.update_accounting_dimensions(
			row,
			accounting_dimensions,
		)

		if amt:
			accounts.append(row)

		return payable_amount

	def update_accounting_dimensions(self, row, accounting_dimensions):
		for dimension in accounting_dimensions:
			row.update({dimension: self.get(dimension)})

		return row

	def get_amount_and_exchange_rate_for_journal_entry(self, account, amount, company_currency, currencies):
		conversion_rate = 1
		exchange_rate = self.exchange_rate
		account_currency = frappe.db.get_value("Account", account, "account_currency")

		if account_currency not in currencies:
			currencies.append(account_currency)

		if company_currency not in currencies:
			currencies.append(company_currency)

		if account_currency == company_currency:
			conversion_rate = self.exchange_rate
			exchange_rate = 1

		amount = flt(amount) * flt(conversion_rate)

		return exchange_rate, amount

	@frappe.whitelist()
	def has_bank_entries(self) -> dict[str, bool]:
		je = frappe.qb.DocType("Journal Entry")
		jea = frappe.qb.DocType("Journal Entry Account")

		# Direct payment posts Bank Entry, Cash Entry, or Journal Entry on slip submit
		payment_entries = (
			frappe.qb.from_(je)
			.inner_join(jea)
			.on(je.name == jea.parent)
			.select(je.name)
			.where(
				(
					(je.voucher_type == "Bank Entry")
					| (je.voucher_type == "Cash Entry")
					| (je.voucher_type == "Journal Entry")
				)
				& (jea.reference_name == self.name)
				& (jea.reference_type == "Payroll Entry")
				& (je.docstatus < 2)
			)
		).run(as_dict=True)

		return {
			"has_bank_entries": bool(payment_entries),
			"has_bank_entries_for_withheld_salaries": not any(
				employee.is_salary_withheld for employee in self.employees
			),
		}

	@frappe.whitelist()
	def make_bank_entry(self, for_withheld_salaries: bool = False) -> Document | None:
		self.check_permission("write")
		self.employee_based_payroll_payable_entries = {}
		employee_wise_accounting_enabled = frappe.db.get_single_value(
			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
		)

		salary_slip_total = 0
		salary_details = self.get_salary_slip_details(for_withheld_salaries)

		for salary_detail in salary_details:
			statistical_component = frappe.db.get_value(
				"Salary Component", salary_detail.salary_component, "statistical_component", cache=True
			)
			if not statistical_component:
				parent_field = salary_detail.parentfield
				if parent_field in ("earnings", "deductions"):
					if employee_wise_accounting_enabled:
						self.set_employee_based_payroll_payable_entries(
							salary_detail.parentfield,
							salary_detail.employee,
							salary_detail.amount,
							salary_detail.salary_structure,
						)
					if parent_field == "earnings":
						salary_slip_total += salary_detail.amount
					elif parent_field == "deductions":
						salary_slip_total -= salary_detail.amount

		total_loan_repayment = self.process_loan_repayments_for_bank_entry(salary_details) or 0
		salary_slip_total -= total_loan_repayment

		bank_entry = None

		if salary_slip_total > 0:
			remark = "withheld salaries" if for_withheld_salaries else "salaries"
			bank_entry = self.set_accounting_entries_for_bank_entry(
				salary_slip_total, remark, employee_wise_accounting_enabled
			)

			if for_withheld_salaries:
				link_bank_entry_in_salary_withholdings(salary_details, bank_entry.name)

		return bank_entry

	def get_salary_slip_details(self, for_withheld_salaries=False):
		SalarySlip = frappe.qb.DocType("Salary Slip")
		SalaryDetail = frappe.qb.DocType("Salary Detail")

		query = (
			frappe.qb.from_(SalarySlip)
			.join(SalaryDetail)
			.on(SalarySlip.name == SalaryDetail.parent)
			.select(
				SalarySlip.name,
				SalarySlip.employee,
				SalarySlip.salary_structure,
				SalarySlip.salary_withholding_cycle,
				SalaryDetail.salary_component,
				SalaryDetail.amount,
				SalaryDetail.parentfield,
			)
			.where(
				(SalarySlip.docstatus == 1)
				& (SalarySlip.start_date >= self.start_date)
				& (SalarySlip.end_date <= self.end_date)
				& (SalarySlip.payroll_entry == self.name)
				& (
					(SalaryDetail.do_not_include_in_total == 0)
					| (
						(SalaryDetail.do_not_include_in_total == 1)
						& (SalaryDetail.do_not_include_in_accounts == 0)
					)
				)
			)
		)

		if "lending" in frappe.get_installed_apps():
			query = query.select(SalarySlip.total_loan_repayment)

		if for_withheld_salaries:
			query = query.where(SalarySlip.status == "Withheld")
		else:
			query = query.where(SalarySlip.status != "Withheld")
		return query.run(as_dict=True)

	@if_lending_app_installed
	def process_loan_repayments_for_bank_entry(self, salary_details: list[dict]) -> float:
		unique_salary_slips = {row["employee"]: row for row in salary_details}.values()
		total_loan_repayment = sum(flt(slip.get("total_loan_repayment", 0)) for slip in unique_salary_slips)

		if self.employee_based_payroll_payable_entries:
			for salary_slip in unique_salary_slips:
				if salary_slip.get("total_loan_repayment"):
					self.set_employee_based_payroll_payable_entries(
						"total_loan_repayment",
						salary_slip.employee,
						salary_slip.total_loan_repayment,
						salary_slip.salary_structure,
					)

		return total_loan_repayment

	def set_accounting_entries_for_bank_entry(
		self, je_payment_amount, user_remark, employee_wise_accounting_enabled
	):
		payroll_payable_account = self.payroll_payable_account
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		accounts = []
		currencies = []
		company_currency = erpnext.get_company_currency(self.company)
		accounting_dimensions = get_accounting_dimensions() or []

		exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
			self.payment_account, je_payment_amount, company_currency, currencies
		)
		accounts.append(
			self.update_accounting_dimensions(
				{
					"account": self.payment_account,
					"bank_account": self.bank_account,
					"credit_in_account_currency": flt(amount, precision),
					"exchange_rate": flt(exchange_rate),
					"cost_center": self.cost_center,
				},
				accounting_dimensions,
			)
		)

		if self.employee_based_payroll_payable_entries:
			for employee, employee_details in self.employee_based_payroll_payable_entries.items():
				je_payment_amount = (
					(employee_details.get("earnings", 0) or 0)
					- (employee_details.get("deductions", 0) or 0)
					- (employee_details.get("total_loan_repayment", 0) or 0)
				)

				if not je_payment_amount:
					continue

				exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
					self.payment_account, je_payment_amount, company_currency, currencies
				)

				cost_centers = self.get_payroll_cost_centers_for_employee(
					employee, employee_details.get("salary_structure")
				)

				for cost_center, percentage in cost_centers.items():
					amount_against_cost_center = flt(amount) * percentage / 100
					accounts.append(
						self.update_accounting_dimensions(
							{
								"account": payroll_payable_account,
								"debit_in_account_currency": flt(amount_against_cost_center, precision),
								"exchange_rate": flt(exchange_rate),
								"reference_type": self.doctype,
								"reference_name": self.name,
								"party_type": "Employee",
								"party": employee,
								"cost_center": cost_center,
							},
							accounting_dimensions,
						)
					)
		else:
			exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
				payroll_payable_account, je_payment_amount, company_currency, currencies
			)
			accounts.append(
				self.update_accounting_dimensions(
					{
						"account": payroll_payable_account,
						"debit_in_account_currency": flt(amount, precision),
						"exchange_rate": flt(exchange_rate),
						"reference_type": self.doctype,
						"reference_name": self.name,
						"cost_center": self.cost_center,
					},
					accounting_dimensions,
				)
			)

		return self.make_journal_entry(
			accounts,
			currencies,
			voucher_type="Cash Entry"
			if frappe.get_cached_value("Account", self.payment_account, "account_type") == "Cash"
			else "Bank Entry",
			user_remark=_("Payment of {0} from {1} to {2}").format(
				_(user_remark), self.start_date, self.end_date
			),
			employee_wise_accounting_enabled=employee_wise_accounting_enabled,
		)

	def set_journal_entry_in_salary_slips(self, submitted_salary_slips, jv_name=None):
		from hrms.hr.belize_banks import bank_label_for_account

		SalarySlip = frappe.qb.DocType("Salary Slip")
		paid = [slip.name for slip in submitted_salary_slips if not slip.salary_withholding]
		withheld = [slip.name for slip in submitted_salary_slips if slip.salary_withholding]
		paid_from_bank = bank_label_for_account(self.bank_account) if self.bank_account else None

		def _update(names, payment_status):
			if not names:
				return
			query = frappe.qb.update(SalarySlip).set(SalarySlip.journal_entry, jv_name)
			if frappe.get_meta("Salary Slip").has_field("payment_status"):
				query = query.set(SalarySlip.payment_status, payment_status)
			if self.bank_account and frappe.get_meta("Salary Slip").has_field("paid_from_bank_account"):
				query = query.set(SalarySlip.paid_from_bank_account, self.bank_account)
			if paid_from_bank and frappe.get_meta("Salary Slip").has_field("paid_from_bank"):
				query = query.set(SalarySlip.paid_from_bank, paid_from_bank)
			if payment_status == "Paid":
				from frappe.utils import nowdate, nowtime

				if frappe.get_meta("Salary Slip").has_field("payment_date"):
					query = query.set(SalarySlip.payment_date, nowdate())
				if frappe.get_meta("Salary Slip").has_field("payment_time"):
					query = query.set(SalarySlip.payment_time, nowtime())
			else:
				if frappe.get_meta("Salary Slip").has_field("payment_date"):
					query = query.set(SalarySlip.payment_date, None)
				if frappe.get_meta("Salary Slip").has_field("payment_time"):
					query = query.set(SalarySlip.payment_time, None)
			query.where(SalarySlip.name.isin(names)).run()

		_update(paid, "Paid")
		_update(withheld, "Not Paid")

	def set_start_end_dates(self):
		self.update(
			get_start_end_dates(self.payroll_frequency, self.start_date or self.posting_date, self.company)
		)

	@frappe.whitelist()
	def get_employees_with_unmarked_attendance(self) -> list[dict] | None:
		if not self.validate_attendance:
			return

		unmarked_attendance = []
		employee_details = self.get_employee_and_attendance_details()
		default_holiday_list = frappe.db.get_value(
			"Company", self.company, "default_holiday_list", cache=True
		)

		for emp in self.employees:
			details = next((record for record in employee_details if record.name == emp.employee), None)
			if not details:
				continue

			start_date, end_date = self.get_payroll_dates_for_employee(details)
			holidays = self.get_holidays_count(
				details.holiday_list or default_holiday_list, start_date, end_date
			)
			payroll_days = date_diff(end_date, start_date) + 1
			unmarked_days = payroll_days - (holidays + details.attendance_count)

			if unmarked_days > 0:
				unmarked_attendance.append(
					{
						"employee": emp.employee,
						"employee_name": emp.employee_name,
						"unmarked_days": unmarked_days,
					}
				)

		return unmarked_attendance

	def get_employee_and_attendance_details(self) -> list[dict]:
		"""Returns a list of employee and attendance details like
		[
		        {
		                "name": "HREMP00001",
		                "date_of_joining": "2019-01-01",
		                "relieving_date": "2022-01-01",
		                "holiday_list": "Holiday List Company",
		                "attendance_count": 22
		        }
		]
		"""
		employees = [emp.employee for emp in self.employees]

		Employee = frappe.qb.DocType("Employee")
		Attendance = frappe.qb.DocType("Attendance")

		return (
			frappe.qb.from_(Employee)
			.left_join(Attendance)
			.on(
				(Employee.name == Attendance.employee)
				& (Attendance.attendance_date.between(self.start_date, self.end_date))
				& (Attendance.docstatus == 1)
			)
			.select(
				Employee.name,
				Employee.date_of_joining,
				Employee.relieving_date,
				Employee.holiday_list,
				Count(Attendance.name).as_("attendance_count"),
			)
			.where(Employee.name.isin(employees))
			.groupby(Employee.name)
		).run(as_dict=True)

	def get_payroll_dates_for_employee(self, employee_details: dict) -> tuple[str, str]:
		start_date = self.start_date
		if employee_details.date_of_joining > getdate(self.start_date):
			start_date = employee_details.date_of_joining

		end_date = self.end_date
		if employee_details.relieving_date and employee_details.relieving_date < getdate(self.end_date):
			end_date = employee_details.relieving_date

		return start_date, end_date

	def get_holidays_count(self, holiday_list: str, start_date: str, end_date: str) -> float:
		"""Returns number of holidays between start and end dates in the holiday list"""
		if not hasattr(self, "_holidays_between_dates"):
			self._holidays_between_dates = {}

		key = f"{start_date}-{end_date}-{holiday_list}"
		if key in self._holidays_between_dates:
			return self._holidays_between_dates[key]

		holidays = frappe.db.get_all(
			"Holiday",
			filters={"parent": holiday_list, "holiday_date": ("between", [start_date, end_date])},
			fields=[{"COUNT": "*", "as": "holidays_count"}],
		)[0]

		if holidays:
			self._holidays_between_dates[key] = holidays.holidays_count

		return self._holidays_between_dates.get(key) or 0

	@frappe.whitelist()
	def create_overtime_slips(self) -> None:
		self.check_permission("write")

		from hrms.hr.doctype.overtime_slip.overtime_slip import (
			create_overtime_slips_for_employees,
			filter_employees_for_overtime_slip_creation,
		)

		employee_list = [emp.employee for emp in self.employees]
		employees = filter_employees_for_overtime_slip_creation(self.start_date, self.end_date, employee_list)

		if employees:
			args = frappe._dict(
				{
					"posting_date": self.posting_date,
					"start_date": self.start_date,
					"end_date": self.end_date,
					"company": self.company,
					"currency": self.currency,
					"payroll_entry": self.name,
				}
			)
			if len(employees) > 30 or frappe.flags.enqueue_payroll_entry:
				self.db_set("status", "Queued")
				frappe.enqueue(
					create_overtime_slips_for_employees,
					timeout=3000,
					employees=employees,
					args=args,
				)
				frappe.msgprint(
					_("Overtime Slip creation is queued. It may take a few minutes"),
					alert=True,
					indicator="blue",
				)
			else:
				create_overtime_slips_for_employees(employees, args)

	@frappe.whitelist()
	def submit_overtime_slips(self) -> None:
		self.check_permission("write")

		from hrms.hr.doctype.overtime_slip.overtime_slip import (
			submit_overtime_slips_for_employees,
		)

		overtime_slips = self.get_unsubmitted_overtime_slips()
		if overtime_slips:
			if len(overtime_slips) > 30 or frappe.flags.enqueue_payroll_entry:
				self.db_set("status", "Queued")
				frappe.enqueue(
					submit_overtime_slips_for_employees,
					timeout=3000,
					overtime_slips=overtime_slips,
					payroll_entry=self.name,
				)
				frappe.msgprint(
					_("Overtime Slip submission is queued. It may take a few minutes"),
					alert=True,
					indicator="blue",
				)
			else:
				submit_overtime_slips_for_employees(overtime_slips, self.name)

	@frappe.whitelist()
	def get_unsubmitted_overtime_slips(self, limit: int | None = None) -> list[str]:
		OvertimeSlip = frappe.qb.DocType("Overtime Slip")
		query = (
			frappe.qb.from_(OvertimeSlip)
			.select(OvertimeSlip.name)
			.where((OvertimeSlip.docstatus == 0) & (OvertimeSlip.payroll_entry == self.name))
		)
		if limit:
			query = query.limit(limit)

		return query.run(pluck="name")

	@frappe.whitelist()
	def get_overtime_slip_details(self) -> list[bool]:
		from hrms.hr.doctype.overtime_slip.overtime_slip import filter_employees_for_overtime_slip_creation

		employee_eligible_for_overtime = unsubmitted_overtime_slips = []

		if frappe.db.get_single_value("Payroll Settings", "create_overtime_slip"):
			employees = [emp.employee for emp in self.employees]
			employee_eligible_for_overtime = filter_employees_for_overtime_slip_creation(
				self.start_date, self.end_date, employees
			)
			unsubmitted_overtime_slips = self.get_unsubmitted_overtime_slips(limit=1)

		return [len(employee_eligible_for_overtime) > 0, len(unsubmitted_overtime_slips) > 0]


def _payroll_entry_from_request(docs=None, name: str | None = None) -> "PayrollEntry":
	if not docs:
		docs = frappe.form_dict.get("docs")
	if docs:
		docs = frappe.parse_json(docs)
		if isinstance(docs, list):
			docs = docs[0] if docs else None
		if docs:
			return frappe.get_doc(docs)

	name = name or frappe.form_dict.get("name")
	if name and frappe.db.exists("Payroll Entry", name):
		return frappe.get_doc("Payroll Entry", name)

	frappe.throw(_("Could not load Payroll Entry to fetch agents."))


@frappe.whitelist()
def fill_employee_details(
	raise_if_empty: int | bool = True,
	docs: dict | list | str | None = None,
	name: str | None = None,
):
	"""Module-level wrapper so Desk can call this as a form command, not only as a doc method."""
	doc = _payroll_entry_from_request(docs=docs, name=name)
	result = doc.fill_employee_details(raise_if_empty=cint(raise_if_empty))
	if not frappe.response.get("docs"):
		frappe.response.docs = []
	frappe.response.docs.append(doc)
	return result


def get_salary_structure(
	company: str, currency: str, salary_slip_based_on_timesheet: int, payroll_frequency: str
) -> list[str]:
	SalaryStructure = frappe.qb.DocType("Salary Structure")

	query = (
		frappe.qb.from_(SalaryStructure)
		.select(SalaryStructure.name)
		.where(
			(SalaryStructure.docstatus == 1)
			& (SalaryStructure.is_active == "Yes")
			& (SalaryStructure.company == company)
			& (SalaryStructure.currency == currency)
		)
	)

	if payroll_frequency:
		query = query.where(SalaryStructure.payroll_frequency == payroll_frequency)
	elif salary_slip_based_on_timesheet:
		query = query.where(SalaryStructure.salary_slip_based_on_timesheet == 1)

	return query.run(pluck=True)


def get_employees_for_client(
	filters,
	searchfield=None,
	search_string=None,
	fields=None,
	as_dict=False,
	limit=None,
	offset=None,
	ignore_match_conditions=False,
) -> list:
	"""Agents billed to the selected client. Currency and pay period are not used."""
	Employee = frappe.qb.DocType("Employee")

	query = (
		frappe.qb.from_(Employee)
		.where((Employee.status != "Inactive") & (Employee.company == filters.company))
	)

	query = set_fields_to_select(query, fields)
	query = set_searchfield(query, searchfield, search_string, qb_object=Employee)
	query = set_filter_conditions(query, filters, qb_object=Employee)

	if not ignore_match_conditions:
		query = set_match_conditions(query=query, qb_object=Employee)

	if limit:
		query = query.limit(limit)

	if offset:
		query = query.offset(offset)

	return query.run(as_dict=as_dict)


def get_filtered_employees(
	sal_struct,
	filters,
	searchfield=None,
	search_string=None,
	fields=None,
	as_dict=False,
	limit=None,
	offset=None,
	ignore_match_conditions=False,
) -> list:
	SalaryStructureAssignment = frappe.qb.DocType("Salary Structure Assignment")
	Employee = frappe.qb.DocType("Employee")

	query = (
		frappe.qb.from_(Employee)
		.join(SalaryStructureAssignment)
		.on(Employee.name == SalaryStructureAssignment.employee)
		.where(
			(SalaryStructureAssignment.docstatus == 1)
			& (Employee.status != "Inactive")
			& (Employee.company == filters.company)
			& ((Employee.date_of_joining <= filters.end_date) | (Employee.date_of_joining.isnull()))
			& ((Employee.relieving_date >= filters.start_date) | (Employee.relieving_date.isnull()))
			& (SalaryStructureAssignment.salary_structure.isin(sal_struct))
			& (filters.end_date >= SalaryStructureAssignment.from_date)
		)
	)

	if filters.get("payroll_payable_account"):
		query = query.where(
			SalaryStructureAssignment.payroll_payable_account == filters.payroll_payable_account
		)

	query = set_fields_to_select(query, fields)
	query = set_searchfield(query, searchfield, search_string, qb_object=Employee)
	query = set_filter_conditions(query, filters, qb_object=Employee)

	if not ignore_match_conditions:
		query = set_match_conditions(query=query, qb_object=Employee)

	if limit:
		query = query.limit(limit)

	if offset:
		query = query.offset(offset)

	return query.run(as_dict=as_dict)


def set_fields_to_select(query, fields: list[str] | None = None):
	default_fields = ["employee", "employee_name", "department", "designation"]
	meta = frappe.get_meta("Employee")
	for extra in ("bank_name", "bank_ac_no"):
		if meta.has_field(extra):
			default_fields.append(extra)

	if fields:
		query = query.select(*fields).distinct()
	else:
		query = query.select(*default_fields).distinct()

	return query


def set_searchfield(query, searchfield, search_string, qb_object):
	if searchfield:
		query = query.where(
			(qb_object[searchfield].like("%" + search_string + "%"))
			| (qb_object.employee_name.like("%" + search_string + "%"))
		)

	return query


def set_filter_conditions(query, filters, qb_object):
	"""Append optional filters to employee query"""
	if filters.get("employees"):
		query = query.where(qb_object.name.notin(filters.get("employees")))

	for fltr_key in ["branch", "department", "designation", "grade"]:
		if filters.get(fltr_key):
			query = query.where(qb_object[fltr_key] == filters[fltr_key])

	if frappe.get_meta("Employee").has_field("bill_to_customer"):
		if cint(filters.get("customer_is_unassigned")):
			# "Not set" is represented as NULL for link fields.
			query = query.where(
				(qb_object["bill_to_customer"].isnull()) | (qb_object["bill_to_customer"] == "")
			)
		elif filters.get("customer") and not is_all_clients(filters.get("customer")):
			query = query.where(qb_object["bill_to_customer"] == filters.customer)

	return query


def set_match_conditions(query, qb_object):
	match_conditions = get_match_cond("Employee", as_condition=False)

	for cond in match_conditions:
		if isinstance(cond, dict):
			for key, value in cond.items():
				if isinstance(value, list):
					query = query.where(qb_object[key].isin(value))
				else:
					query = query.where(qb_object[key] == value)

	return query


def remove_payrolled_employees(emp_list, start_date, end_date):
	SalarySlip = frappe.qb.DocType("Salary Slip")

	employees_with_payroll = (
		frappe.qb.from_(SalarySlip)
		.select(SalarySlip.employee)
		.where(
			(SalarySlip.docstatus == 1)
			& (SalarySlip.start_date == start_date)
			& (SalarySlip.end_date == end_date)
		)
	).run(pluck=True)

	return [emp_list[emp] for emp in emp_list if emp not in employees_with_payroll]


@frappe.whitelist()
def get_payroll_source_banks(company: str | None = None) -> list[dict]:
	"""Belize company bank accounts the BPO can wire agent payroll from."""
	from hrms.hr.belize_banks import get_company_payment_banks

	return get_company_payment_banks(company)


@frappe.whitelist()
def get_start_end_dates(
	payroll_frequency: str, start_date: str | datetime.date | None = None, company: str | None = None
) -> frappe._dict:
	"""Returns dict of start and end dates for given payroll frequency based on start_date"""
	from hrms.payroll.auto_payroll import add_working_days, canonical_frequency, days_for_frequency

	payroll_frequency = canonical_frequency(payroll_frequency)

	if payroll_frequency in ("Weekly", "Fortnightly"):
		interval = days_for_frequency(payroll_frequency)
		end_date = add_working_days(getdate(start_date), interval)
		return frappe._dict({"start_date": start_date, "end_date": end_date})

	if payroll_frequency == "Monthly":
		interval = days_for_frequency(payroll_frequency)
		if interval not in (28, 29, 30, 31):
			end_date = add_working_days(getdate(start_date), interval)
			return frappe._dict({"start_date": start_date, "end_date": end_date})

	if payroll_frequency == "Monthly" or payroll_frequency == "Bimonthly" or payroll_frequency == "":
		fiscal_year = get_fiscal_year(start_date, company=company)[0]
		month = "%02d" % getdate(start_date).month
		m = get_month_details(fiscal_year, month)
		if payroll_frequency == "Bimonthly":
			if getdate(start_date).day <= 15:
				start_date = m["month_start_date"]
				end_date = m["month_mid_end_date"]
			else:
				start_date = m["month_mid_start_date"]
				end_date = m["month_end_date"]
		else:
			start_date = m["month_start_date"]
			end_date = m["month_end_date"]

	if payroll_frequency == "Weekly":
		end_date = add_working_days(start_date, days_for_frequency("Weekly"))

	if payroll_frequency == "Fortnightly":
		end_date = add_working_days(start_date, days_for_frequency("Fortnightly"))

	if payroll_frequency == "Daily":
		end_date = start_date

	return frappe._dict({"start_date": start_date, "end_date": end_date})


def get_frequency_kwargs(frequency_name):
	frequency_dict = {
		"monthly": {"months": 1},
		"fortnightly": {"days": 14},
		"weekly": {"days": 7},
		"daily": {"days": 1},
	}
	return frequency_dict.get(frequency_name)


@frappe.whitelist()
def get_end_date(start_date: str | datetime.date, frequency: str) -> dict:
	from hrms.payroll.auto_payroll import add_working_days, canonical_frequency, days_for_frequency

	start_date = getdate(start_date)
	frequency = canonical_frequency(frequency) or "Monthly"
	if frequency in ("Weekly", "Fortnightly") or (
		frequency == "Monthly" and days_for_frequency(frequency) not in (28, 29, 30, 31)
	):
		end_date = add_working_days(start_date, days_for_frequency(frequency))
		return dict(end_date=end_date.strftime(DATE_FORMAT))

	frequency_key = frequency.lower() if frequency else "monthly"
	kwargs = get_frequency_kwargs(frequency_key) if frequency_key != "bimonthly" else get_frequency_kwargs("monthly")

	# weekly, fortnightly and daily intervals have fixed days so no problems
	end_date = add_to_date(start_date, **kwargs) - relativedelta(days=1)
	if frequency_key != "bimonthly":
		return dict(end_date=end_date.strftime(DATE_FORMAT))

	else:
		return dict(end_date="")


def get_month_details(year, month):
	ysd = frappe.db.get_value("Fiscal Year", year, "year_start_date")
	if ysd:
		import calendar
		import datetime

		diff_mnt = cint(month) - cint(ysd.month)
		if diff_mnt < 0:
			diff_mnt = 12 - int(ysd.month) + cint(month)
		msd = ysd + relativedelta(months=diff_mnt)  # month start date
		month_days = cint(calendar.monthrange(cint(msd.year), cint(month))[1])  # days in month
		mid_start = datetime.date(msd.year, cint(month), 16)  # month mid start date
		mid_end = datetime.date(msd.year, cint(month), 15)  # month mid end date
		med = datetime.date(msd.year, cint(month), month_days)  # month end date
		return frappe._dict(
			{
				"year": msd.year,
				"month_start_date": msd,
				"month_end_date": med,
				"month_mid_start_date": mid_start,
				"month_mid_end_date": mid_end,
				"month_days": month_days,
			}
		)
	else:
		frappe.throw(_("Fiscal Year {0} not found").format(year))


def log_payroll_failure(process, payroll_entry, error):
	error_log = frappe.log_error(
		title=_("Salary Slip {0} failed for Payroll Entry {1}").format(process, payroll_entry.name)
	)
	message_log = frappe.message_log.pop() if frappe.message_log else str(error)

	try:
		if isinstance(message_log, str):
			error_message = json.loads(message_log).get("message")
		else:
			error_message = message_log.get("message")
	except Exception:
		error_message = message_log

	error_message += "\n" + _("Check Error Log {0} for more details.").format(
		get_link_to_form("Error Log", error_log.name)
	)

	payroll_entry.db_set({"error_message": error_message, "status": "Failed"})


def _is_missing_salary_structure_error(error) -> bool:
	message = str(error).lower()
	if "salary structure" not in message:
		return False
	return any(
		phrase in message
		for phrase in (
			"not found",
			"found for employee",
			"assign",
			"missing",
			"applicable from",
		)
	)


def _employee_skip_labels(employees) -> list[str]:
	labels = []
	for emp in employees:
		details = frappe.db.get_value("Employee", emp, ["employee_name", "name"], as_dict=True) or {}
		labels.append(details.get("employee_name") or details.get("name") or emp)
	return labels


def _skipped_salary_structure_message(employees) -> str:
	return _("No Salary Structure for {0}. They were skipped and salary slips were not created.").format(
		comma_and(_employee_skip_labels(employees))
	)


def _notify_skipped_salary_structures(payroll_entry, skipped):
	message = _skipped_salary_structure_message(skipped)
	frappe.msgprint(
		_("No Salary Structure for {0}. They were skipped and salary slips were not created.").format(
			comma_and([frappe.bold(label) for label in _employee_skip_labels(skipped)])
		),
		title=_("Salary Structure Missing"),
		indicator="orange",
	)
	try:
		payroll_entry.add_comment("Comment", text=message)
	except Exception:
		frappe.log_error(title=_("Payroll skip notice failed"))


def create_salary_slips_for_employees(employees, args, publish_progress=True):
	payroll_entry = frappe.get_cached_doc("Payroll Entry", args.payroll_entry)
	savepoint = "payroll_salary_slip_creation"

	try:
		frappe.db.savepoint(savepoint)
		salary_slips_exist_for = get_existing_salary_slips(employees, args)
		count = 0
		skipped = []

		employees = list(set(employees) - set(salary_slips_exist_for))
		for emp in employees:
			slip_args = {
				"doctype": "Salary Slip",
				"employee": emp,
				"salary_slip_based_on_timesheet": args.get("salary_slip_based_on_timesheet"),
				"payroll_frequency": args.get("payroll_frequency"),
				"start_date": args.get("start_date"),
				"end_date": args.get("end_date"),
				"company": args.get("company"),
				"posting_date": args.get("posting_date"),
				"deduct_tax_for_unsubmitted_tax_exemption_proof": args.get(
					"deduct_tax_for_unsubmitted_tax_exemption_proof"
				),
				"payroll_entry": args.get("payroll_entry"),
				"exchange_rate": args.get("exchange_rate"),
				"currency": args.get("currency"),
			}
			frappe.db.savepoint("before_salary_slip")
			try:
				frappe.get_doc(slip_args).insert()
			except Exception as e:
				frappe.db.rollback(save_point="before_salary_slip")
				if _is_missing_salary_structure_error(e):
					if frappe.message_log:
						frappe.message_log.pop()
					skipped.append(emp)
					continue
				raise

			count += 1
			if publish_progress and employees:
				frappe.publish_progress(
					count * 100 / len(employees),
					title=_("Creating Salary Slips..."),
				)

		skip_message = _skipped_salary_structure_message(skipped) if skipped else ""
		payroll_entry.db_set(
			{
				"status": "Submitted",
				"salary_slips_created": 1 if count or salary_slips_exist_for else 0,
				"error_message": skip_message,
			}
		)

		if skipped:
			_notify_skipped_salary_structures(payroll_entry, skipped)

		if salary_slips_exist_for:
			frappe.msgprint(
				_(
					"Salary Slips already exist for employees {}, and will not be processed by this payroll."
				).format(frappe.bold(", ".join(emp for emp in salary_slips_exist_for))),
				title=_("Message"),
				indicator="orange",
			)

	except Exception as e:
		frappe.db.rollback(save_point=savepoint)
		log_payroll_failure("creation", payroll_entry, e)

	finally:
		if not frappe.in_test:
			frappe.db.commit()  # nosemgrep
		frappe.publish_realtime("completed_salary_slip_creation", user=frappe.session.user)


def show_payroll_submission_status(submitted, unsubmitted, payroll_entry):
	if not submitted and not unsubmitted:
		frappe.msgprint(
			_(
				"No salary slip found to submit for the above selected criteria OR salary slip already submitted"
			)
		)
	elif submitted and not unsubmitted:
		frappe.msgprint(
			_("Salary Slips submitted for period from {0} to {1}").format(
				payroll_entry.start_date, payroll_entry.end_date
			),
			title=_("Success"),
			indicator="green",
		)
	elif unsubmitted:
		frappe.msgprint(
			_("Could not submit some Salary Slips: {}").format(
				", ".join(get_link_to_form("Salary Slip", entry) for entry in unsubmitted)
			),
			title=_("Failure"),
			indicator="red",
		)


def get_existing_salary_slips(employees, args):
	SalarySlip = frappe.qb.DocType("Salary Slip")

	return (
		frappe.qb.from_(SalarySlip)
		.select(SalarySlip.employee)
		.distinct()
		.where(
			(SalarySlip.docstatus != 2)
			& (SalarySlip.company == args.company)
			& (SalarySlip.payroll_entry == args.payroll_entry)
			& (SalarySlip.start_date >= args.start_date)
			& (SalarySlip.end_date <= args.end_date)
			& (SalarySlip.employee.isin(employees))
		)
	).run(pluck=True)


def submit_salary_slips_for_employees(payroll_entry, salary_slips, publish_progress=True):
	savepoint = "payroll_salary_slip_submission"
	try:
		frappe.db.savepoint(savepoint)
		submitted = []
		unsubmitted = []
		frappe.flags.via_payroll_entry = True
		count = 0

		for entry in salary_slips:
			salary_slip = frappe.get_doc("Salary Slip", entry[0])
			if salary_slip.net_pay < 0:
				unsubmitted.append(entry[0])
			else:
				try:
					salary_slip.submit()
					submitted.append(salary_slip)
				except frappe.ValidationError:
					unsubmitted.append(entry[0])

			count += 1
			if publish_progress:
				frappe.publish_progress(
					count * 100 / len(salary_slips), title=_("Submitting Salary Slips...")
				)

		if submitted:
			payroll_entry.make_accrual_jv_entry(submitted)
			payroll_entry.email_salary_slip(submitted)
			payroll_entry.db_set({"salary_slips_submitted": 1, "status": "Submitted", "error_message": ""})

		show_payroll_submission_status(submitted, unsubmitted, payroll_entry)

	except Exception as e:
		frappe.db.rollback(save_point=savepoint)
		log_payroll_failure("submission", payroll_entry, e)

	finally:
		if not frappe.in_test:
			frappe.db.commit()  # nosemgrep
		frappe.publish_realtime("completed_salary_slip_submission", user=frappe.session.user)

	frappe.flags.via_payroll_entry = False


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_payroll_entries_for_jv(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict
) -> list:
	PayrollEntry = frappe.qb.DocType("Payroll Entry")
	JournalEntryAccount = frappe.qb.DocType("Journal Entry Account")

	linked_entries = (
		frappe.qb.from_(JournalEntryAccount)
		.select(JournalEntryAccount.reference_name)
		.where(JournalEntryAccount.reference_type == "Payroll Entry")
	)

	return (
		frappe.qb.from_(PayrollEntry)
		.select(PayrollEntry.name)
		.where(PayrollEntry.docstatus == 1)
		.where(PayrollEntry[searchfield].like("%%%s%%" % txt))
		.where(PayrollEntry.name.notin(linked_entries))
		.orderby(PayrollEntry.name)
		.limit(page_len)
		.offset(start)
	).run()


def _link_row_is_field(row, fieldname: str) -> bool:
	if isinstance(row, dict):
		return row.get("fieldname") == fieldname or row.get("field") == fieldname
	if isinstance(row, (list, tuple)):
		return bool(row) and row[0] == fieldname
	return False


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def payroll_client_query(doctype, txt, searchfield, start, page_len, filters):
	"""Optional client filter. Leave blank to include every agent."""
	start = cint(start)
	page_len = cint(page_len)
	txt = txt or ""
	meta = frappe.get_meta("Customer")
	conditions = ["1=1"]
	values = {"txt": f"%{txt}%", "start": start, "page_len": page_len}
	if meta.has_field("disabled"):
		conditions.append("ifnull(disabled, 0) = 0")
	search_fields = [field for field in (searchfield, "name", "customer_name") if field]
	search_clause = " or ".join(f"`{field}` like %(txt)s" for field in dict.fromkeys(search_fields))
	if search_clause:
		conditions.append(f"({search_clause})")

	if page_len < 1:
		return []

	return frappe.db.sql(
		f"""
		select name, customer_name
		from `tabCustomer`
		where {" and ".join(conditions)}
		{get_match_cond(doctype)}
		order by name
		limit %(start)s, %(page_len)s
		""",
		values,
	)


def get_employee_list(
	filters: frappe._dict,
	searchfield=None,
	search_string=None,
	fields: list[str] | None = None,
	as_dict=True,
	limit=None,
	offset=None,
	ignore_match_conditions=False,
) -> list:
	if is_all_agents_payroll(filters.get("customer")) and frappe.get_meta("Employee").has_field(
		"bill_to_customer"
	):
		all_agent_filters = frappe._dict(filters)
		all_agent_filters.customer = None
		return get_employees_for_client(
			all_agent_filters,
			searchfield=searchfield,
			search_string=search_string,
			fields=fields,
			as_dict=as_dict,
			limit=limit,
			offset=offset,
			ignore_match_conditions=ignore_match_conditions,
		)

	if filters.get("customer") and frappe.get_meta("Employee").has_field("bill_to_customer"):
		return get_employees_for_client(
			filters,
			searchfield=searchfield,
			search_string=search_string,
			fields=fields,
			as_dict=as_dict,
			limit=limit,
			offset=offset,
			ignore_match_conditions=ignore_match_conditions,
		)

	sal_struct = get_salary_structure(
		filters.company,
		filters.currency,
		filters.salary_slip_based_on_timesheet,
		filters.payroll_frequency,
	)

	if not sal_struct:
		return []

	emp_list = get_filtered_employees(
		sal_struct,
		filters,
		searchfield,
		search_string,
		fields,
		as_dict=as_dict,
		limit=limit,
		offset=offset,
		ignore_match_conditions=ignore_match_conditions,
	)

	if as_dict:
		employees_to_check = {emp.employee: emp for emp in emp_list}
	else:
		employees_to_check = {emp[0]: emp for emp in emp_list}

	return remove_payrolled_employees(employees_to_check, filters.start_date, filters.end_date)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def employee_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict
) -> list:
	filters = frappe._dict(filters)

	client_filter = filters.get("customer") and not is_all_clients(filters.get("customer"))
	if not (client_filter and frappe.get_meta("Employee").has_field("bill_to_customer")):
		if not filters.payroll_frequency:
			frappe.throw(_("Select Payroll Frequency."))

	employee_list = get_employee_list(
		filters,
		searchfield=searchfield,
		search_string=txt,
		fields=["name", "employee_name"],
		as_dict=False,
		limit=page_len,
		offset=start,
	)

	return employee_list


def get_salary_withholdings(
	start_date: str,
	end_date: str,
	employee: str | None = None,
	pluck: str | None = None,
) -> list[str] | list[dict]:
	Withholding = frappe.qb.DocType("Salary Withholding")
	WithholdingCycle = frappe.qb.DocType("Salary Withholding Cycle")
	withheld_salaries = (
		frappe.qb.from_(Withholding)
		.join(WithholdingCycle)
		.on(WithholdingCycle.parent == Withholding.name)
		.select(
			Withholding.employee,
			Withholding.name.as_("salary_withholding"),
			WithholdingCycle.name.as_("salary_withholding_cycle"),
		)
		.where(
			(WithholdingCycle.from_date == start_date)
			& (WithholdingCycle.to_date == end_date)
			& (WithholdingCycle.docstatus == 1)
			& (WithholdingCycle.is_salary_released != 1)
		)
	)

	if employee:
		withheld_salaries = withheld_salaries.where(Withholding.employee == employee)

	if pluck:
		return withheld_salaries.run(pluck=pluck)
	return withheld_salaries.run(as_dict=True)


PAYROLL_EXCEL_COLUMNS = (
	{"key": "agent_name", "label": "Agent Name", "align": "left"},
	{"key": "pay_period", "label": "Pay Period", "align": "left"},
	{"key": "regular_hours", "label": "Regular Hours", "align": "right"},
	{"key": "overtime_hours", "label": "Overtime Hours", "align": "right"},
	{"key": "holiday_pay", "label": "Holiday Pay", "align": "right"},
	{"key": "hourly_rate", "label": "Hourly Rate", "align": "right"},
	{"key": "bonus", "label": "Bonus", "align": "right"},
	{"key": "gross_pay", "label": "Gross Pay", "align": "right"},
	{"key": "income_tax_wh", "label": "Income Tax W/H", "align": "right"},
	{"key": "wage_band", "label": "Wage Band", "align": "left"},
	{"key": "weekly_insurable_earnings", "label": "Weekly Insurable Earnings", "align": "right"},
	{"key": "employee_social_security", "label": "Employee Social Security", "align": "right"},
	{"key": "employer_social_security", "label": "Employer Social Security", "align": "right"},
	{"key": "pay_period_ee_social", "label": "Pay Period EE Social", "align": "right"},
	{"key": "pay_period_er_social", "label": "Pay Period ER Social", "align": "right"},
	{"key": "net_pay", "label": "Net Pay", "align": "right"},
)

PAYROLL_EXCEL_EDITABLE_FIELDS = frozenset(
	{
		"regular_hours",
		"overtime_hours",
		"holiday_pay",
		"hourly_rate",
		"bonus",
		"income_tax_wh",
	}
)


@frappe.whitelist()
def get_payroll_excel_data(name: str | None = None) -> dict:
	"""One row per agent for the Payroll Entry spreadsheet view."""
	name = name or frappe.form_dict.get("name")
	if not name:
		frappe.throw(_("Payroll Entry is required"))

	if not frappe.db.exists("Payroll Entry", name):
		frappe.throw(_("Payroll Entry {0} not found").format(name))

	entry = frappe.get_doc("Payroll Entry", name)
	entry.check_permission("read")

	period_label = _format_pay_period(entry.start_date, entry.end_date)
	slips = _get_excel_salary_slips(entry)
	working_by_employee = _working_hours_by_employee(entry)
	overtime_by_employee = _overtime_hours_by_employee(entry)
	holiday_hours_by_employee = _holiday_hours_by_employee(entry)
	holiday_pay_by_employee = _holiday_pay_by_employee(entry)
	bonus_by_slip = _bonus_by_salary_slip([row.name for row in slips])
	ytd_social_by_employee = _ytd_social_by_employee(entry)
	rate_by_employee = _hourly_rate_by_employee(entry, slips)

	employees = [slip.employee for slip in slips] + [
		emp.employee for emp in (entry.employees or []) if emp.employee
	]
	names_by_id = _employee_name_parts_by_id(employees)

	rows = []
	seen = set()
	for slip in slips:
		seen.add(slip.employee)
		agent_name = _payroll_agent_name(slip.employee, slip.employee_name, names_by_id)
		overtime_hours, regular_hours = _excel_hours_for_employee(
			slip.employee,
			slip.total_working_hours,
			working_by_employee,
			overtime_by_employee,
			prefer_attendance=not flt(slip.hour_rate),
		)
		hourly_rate = _excel_hourly_rate(slip, rate_by_employee.get(slip.employee))
		holiday_pay = flt(holiday_pay_by_employee.get(slip.employee))
		holiday_hours = flt(holiday_hours_by_employee.get(slip.employee))
		bonus = flt(bonus_by_slip.get(slip.name))
		gross_pay = _excel_gross_pay(
			slip,
			regular_hours,
			overtime_hours,
			hourly_rate,
			holiday_pay,
			bonus,
			employee=slip.employee,
			holiday_hours=holiday_hours,
		)
		ee_period, er_period = _slip_social_amounts(slip)
		ee_ytd, er_ytd = ytd_social_by_employee.get(slip.employee) or (ee_period, er_period)
		net_pay = _excel_net_pay(slip, gross_pay)
		rows.append(
			{
				"employee": slip.employee,
				"salary_slip": slip.name,
				"agent_name": agent_name,
				"pay_period": _format_pay_period(slip.start_date, slip.end_date) or period_label,
				"regular_hours": regular_hours,
				"overtime_hours": overtime_hours,
				"holiday_pay": holiday_pay,
				"hourly_rate": hourly_rate,
				"bonus": bonus,
				"gross_pay": gross_pay,
				"income_tax_wh": _slip_income_tax(slip),
				"wage_band": slip.ss_wage_band or "",
				"weekly_insurable_earnings": flt(slip.ss_insurable_earnings),
				"employee_social_security": ee_ytd,
				"employer_social_security": er_ytd,
				"pay_period_ee_social": ee_period,
				"pay_period_er_social": er_period,
				"net_pay": net_pay,
			}
		)

	# Agents queued in this run whose salary slip does not exist yet.
	for emp in entry.employees or []:
		if emp.employee in seen:
			continue
		agent_name = _payroll_agent_name(emp.employee, emp.employee_name, names_by_id)
		ee_ytd, er_ytd = ytd_social_by_employee.get(emp.employee) or (0.0, 0.0)
		overtime_hours, regular_hours = _excel_hours_for_employee(
			emp.employee,
			0,
			working_by_employee,
			overtime_by_employee,
			prefer_attendance=True,
		)
		hourly_rate = flt(rate_by_employee.get(emp.employee))
		holiday_pay = flt(holiday_pay_by_employee.get(emp.employee))
		holiday_hours = flt(holiday_hours_by_employee.get(emp.employee))
		gross_pay = _excel_gross_pay(
			None,
			regular_hours,
			overtime_hours,
			hourly_rate,
			holiday_pay,
			0,
			employee=emp.employee,
			holiday_hours=holiday_hours,
		)
		rows.append(
			{
				"employee": emp.employee,
				"salary_slip": "",
				"agent_name": agent_name,
				"pay_period": period_label,
				"regular_hours": regular_hours,
				"overtime_hours": overtime_hours,
				"holiday_pay": holiday_pay,
				"hourly_rate": hourly_rate,
				"bonus": 0,
				"gross_pay": gross_pay,
				"income_tax_wh": 0,
				"wage_band": "",
				"weekly_insurable_earnings": 0,
				"employee_social_security": ee_ytd,
				"employer_social_security": er_ytd,
				"pay_period_ee_social": 0,
				"pay_period_er_social": 0,
				"net_pay": gross_pay,
			}
		)

	rows.sort(
		key=lambda row: (
			(row.get("agent_name") or "").lower(),
			row.get("employee") or "",
		)
	)

	return {
		"columns": [
			{
				"id": col["key"],
				"name": _(col["label"]),
				"align": col["align"],
				"editable": col["key"] in PAYROLL_EXCEL_EDITABLE_FIELDS,
			}
			for col in PAYROLL_EXCEL_COLUMNS
		],
		"rows": rows,
		"meta": {
			"payroll_entry": entry.name,
			"pay_period": period_label,
			"currency": entry.currency,
			"branch": entry.branch,
			"status": entry.status,
		},
	}


@frappe.whitelist()
def save_payroll_excel_cell(
	name: str | None = None,
	employee: str | None = None,
	field: str | None = None,
	value=None,
) -> dict:
	"""Persist one editable spreadsheet cell to the agent's draft salary slip."""
	name = name or frappe.form_dict.get("name")
	employee = employee or frappe.form_dict.get("employee")
	field = field or frappe.form_dict.get("field")
	if not name or not employee or not field:
		frappe.throw(_("Payroll Entry, employee, and field are required"))
	if field not in PAYROLL_EXCEL_EDITABLE_FIELDS:
		frappe.throw(_("Field {0} cannot be edited from the spreadsheet").format(field))

	entry = frappe.get_doc("Payroll Entry", name)
	entry.check_permission("write")

	slip_name = frappe.db.get_value(
		"Salary Slip",
		{"payroll_entry": name, "employee": employee, "docstatus": ("<", 2)},
		"name",
		order_by="creation desc",
	)
	if not slip_name:
		frappe.throw(_("Create salary slips before editing the spreadsheet."))

	slip = frappe.get_doc("Salary Slip", slip_name)
	if slip.docstatus != 0:
		frappe.throw(_("Only draft salary slips can be edited from the spreadsheet."))

	numeric_value = flt(value)
	if field == "hourly_rate":
		slip.hour_rate = numeric_value
	elif field == "income_tax_wh":
		if slip.meta.has_field("current_month_income_tax"):
			slip.current_month_income_tax = numeric_value
		slip.total_income_tax = numeric_value
	elif field in ("regular_hours", "overtime_hours"):
		overtime = flt(_overtime_hours_by_employee(entry).get(employee))
		total = flt(slip.total_working_hours)
		regular = max(total - overtime, 0.0) if total else 0.0
		if field == "regular_hours":
			regular = numeric_value
		else:
			overtime = numeric_value
		slip.total_working_hours = regular + overtime
	elif field == "bonus":
		_set_slip_bonus_amount(slip, numeric_value)
	elif field == "holiday_pay":
		_set_slip_holiday_pay_amount(slip, numeric_value)

	slip.flags.ignore_validate = True
	if hasattr(slip, "calculate_net_pay"):
		slip.calculate_net_pay()
	slip.save(ignore_permissions=True)

	return get_payroll_excel_data(name)


def _payroll_agent_name(employee: str, employee_name: str | None, names_by_id: dict) -> str:
	if employee_name and employee_name.strip() and employee_name != employee:
		return employee_name.strip()
	first_name, last_name = names_by_id.get(employee) or _split_full_name(employee_name or employee)
	return " ".join(part for part in (first_name, last_name) if part) or employee


def _set_slip_bonus_amount(slip, amount: float) -> None:
	for row in slip.earnings or []:
		component = frappe.db.get_value("Salary Component", row.salary_component, "earning_category")
		if component == "Bonus":
			row.amount = amount
			return
	if amount:
		bonus_component = frappe.db.get_value("Salary Component", {"earning_category": "Bonus"}, "name")
		if bonus_component:
			slip.append("earnings", {"salary_component": bonus_component, "amount": amount})


def _set_slip_holiday_pay_amount(slip, amount: float) -> None:
	for row in slip.earnings or []:
		if "holiday" in (row.salary_component or "").lower():
			row.amount = amount
			return
	if amount:
		holiday_component = frappe.db.get_value(
			"Salary Component", {"name": ("like", "%Holiday%")}, "name"
		)
		if holiday_component:
			slip.append("earnings", {"salary_component": holiday_component, "amount": amount})


@frappe.whitelist()
def get_bank_payroll_data(name: str | None = None) -> dict:
	"""Rows for the Heritage Bank remittance sheet: name, account, SAV, net pay, bank code."""
	from hrms.hr.belize_banks import bank_code_for

	payload = get_payroll_excel_data(name)
	employees = [row.get("employee") for row in payload.get("rows") or [] if row.get("employee")]
	bank_by_id = _employee_bank_details_by_id(employees)
	slip_bank_by_id = _salary_slip_bank_details_by_id((payload.get("meta") or {}).get("payroll_entry"), employees)
	names_by_id = _employee_name_parts_by_id(employees)

	rows = []
	for row in payload.get("rows") or []:
		employee = row.get("employee")
		first_name, last_name = names_by_id.get(employee) or _split_full_name(
			row.get("agent_name") or employee
		)
		bank = bank_by_id.get(employee) or {}
		slip_bank = slip_bank_by_id.get(employee) or {}
		if not bank.get("bank_name"):
			bank["bank_name"] = slip_bank.get("bank_name")
		if not bank.get("bank_ac_no"):
			bank["bank_ac_no"] = slip_bank.get("bank_account_no")
		account_type = (bank.get("bank_account_type") or "").strip()
		is_savings = account_type.lower() in {"savings", "saving", "sav"}
		rows.append(
			{
				"employee": employee,
				"first_name": first_name,
				"last_name": last_name,
				"bank_account_no": bank.get("bank_ac_no") or "",
				"account_type": "SAV" if is_savings else "",
				"net_pay": flt(row.get("net_pay")),
				"payment_type": "SALARY",
				"bank_code": bank_code_for(bank.get("bank_name")),
			}
		)

	rows.sort(
		key=lambda item: (
			(item.get("first_name") or "").lower(),
			(item.get("last_name") or "").lower(),
			item.get("employee") or "",
		)
	)
	return {
		"rows": rows,
		"meta": payload.get("meta") or {},
	}


def _employee_bank_details_by_id(employees: list[str]) -> dict[str, dict]:
	names = {name for name in employees if name}
	if not names:
		return {}

	fields = ["name", "bank_name", "bank_ac_no"]
	meta = frappe.get_meta("Employee")
	if meta.has_field("bank_account_type"):
		fields.append("bank_account_type")

	out = {}
	for row in frappe.get_all("Employee", filters={"name": ("in", list(names))}, fields=fields):
		out[row.name] = row
	return out


def _salary_slip_bank_details_by_id(payroll_entry: str | None, employees: list[str]) -> dict[str, dict]:
	if not payroll_entry or not employees:
		return {}
	rows = frappe.get_all(
		"Salary Slip",
		filters={"payroll_entry": payroll_entry, "employee": ("in", employees), "docstatus": ("<", 2)},
		fields=["employee", "bank_name", "bank_account_no"],
	)
	return {row.employee: row for row in rows}


@frappe.whitelist()
def download_bank_payroll(name: str | None = None) -> None:
	payload = get_bank_payroll_data(name)
	xlsx_file = _bank_payroll_xlsx(payload.get("rows") or [])
	period = (payload.get("meta") or {}).get("pay_period") or "Payroll"
	safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(period))
	_respond_payroll_file(f"Bank_Payroll_{safe}.xlsx", xlsx_file.getvalue())


def _bank_payroll_xlsx(rows: list[dict]):
	"""Build the bank remittance workbook. Column E is a number with 2 decimals."""
	from io import BytesIO

	import xlsxwriter

	xlsx_file = BytesIO()
	workbook = xlsxwriter.Workbook(xlsx_file, {"constant_memory": True})
	worksheet = workbook.add_worksheet("HERITAGE BANK SHEET")
	money = workbook.add_format({"num_format": "0.00"})
	worksheet.set_column(4, 4, 12, money)

	for row_idx, row in enumerate(rows):
		worksheet.write(row_idx, 0, row.get("first_name") or "")
		worksheet.write(row_idx, 1, row.get("last_name") or "")
		worksheet.write(row_idx, 2, row.get("bank_account_no") or "")
		worksheet.write(row_idx, 3, row.get("account_type") or "")
		worksheet.write_number(row_idx, 4, round(flt(row.get("net_pay")), 2), money)
		worksheet.write(row_idx, 5, row.get("payment_type") or "SALARY")
		worksheet.write(row_idx, 6, row.get("bank_code") or "")

	workbook.close()
	xlsx_file.seek(0)
	return xlsx_file


@frappe.whitelist()
def download_payroll_excel(name: str | None = None) -> None:
	payload = get_payroll_excel_data(name)
	from frappe.utils.xlsxutils import make_xlsx

	xlsx_file = make_xlsx(_payroll_export_table(payload), "Payroll Entry")
	_respond_payroll_file(_payroll_export_filename(payload, "xlsx"), xlsx_file.getvalue())


@frappe.whitelist()
def download_payroll_excel_pdf(name: str | None = None) -> None:
	payload = get_payroll_excel_data(name)
	from frappe.utils.pdf import get_pdf

	from hrms.branding import staff_pro_logo_url

	html = frappe.render_template(
		"hrms/payroll/doctype/payroll_entry/payroll_excel_export.html",
		{
			"title": _("Payroll Entry"),
			"logo": staff_pro_logo_url(),
			"generated_on": formatdate(getdate()),
			"meta": payload.get("meta") or {},
			"columns": payload.get("columns") or [],
			"rows": _payroll_pdf_rows(payload),
		},
	)
	_respond_payroll_file(_payroll_export_filename(payload, "pdf"), get_pdf(html))


def _employee_name_parts_by_id(employees: list[str]) -> dict[str, tuple[str, str]]:
	names = {name for name in employees if name}
	if not names:
		return {}

	rows = frappe.get_all(
		"Employee",
		filters={"name": ("in", list(names))},
		fields=["name", "first_name", "last_name", "employee_name"],
	)
	out = {}
	for row in rows:
		first = (row.first_name or "").strip()
		last = (row.last_name or "").strip()
		if not first or not last:
			split_first, split_last = _split_full_name(row.employee_name or "")
			first = first or split_first
			last = last or split_last
		out[row.name] = (first, last)
	return out


def _split_full_name(full_name: str) -> tuple[str, str]:
	parts = [part for part in (full_name or "").strip().split() if part]
	if not parts:
		return "", ""
	if len(parts) == 1:
		return parts[0], ""
	return " ".join(parts[:-1]), parts[-1]


def _payroll_export_table(payload: dict) -> list[list]:
	columns = payload.get("columns") or []
	rows = [ [col.get("name") or col.get("id") for col in columns] ]
	for row in payload.get("rows") or []:
		rows.append([row.get(col["id"], "") for col in columns])
	return rows


def _payroll_pdf_rows(payload: dict) -> list[dict]:
	meta = payload.get("meta") or {}
	currency = meta.get("currency")
	formatted = []
	for row in payload.get("rows") or []:
		out = {}
		for col in payload.get("columns") or []:
			value = row.get(col["id"], "")
			if col["id"] in PAYROLL_EXCEL_MONEY_KEYS:
				value = fmt_money(flt(value), currency=currency) if value not in (None, "") else ""
			elif col["id"] in ("regular_hours", "overtime_hours") and value not in (None, ""):
				value = f"{flt(value):.2f}"
			out[col["id"]] = value
		formatted.append(out)
	return formatted


PAYROLL_EXCEL_MONEY_KEYS = {
	"holiday_pay",
	"hourly_rate",
	"bonus",
	"gross_pay",
	"income_tax_wh",
	"weekly_insurable_earnings",
	"employee_social_security",
	"employer_social_security",
	"pay_period_ee_social",
	"pay_period_er_social",
	"net_pay",
}


def _payroll_export_filename(payload: dict, extension: str) -> str:
	period = (payload.get("meta") or {}).get("pay_period") or "Payroll"
	safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(period))
	return f"Payroll_Entry_{safe}.{extension}"


def _respond_payroll_file(filename: str, content) -> None:
	frappe.response["filename"] = filename
	frappe.response["filecontent"] = content
	frappe.response["type"] = "binary"


def _format_pay_period(start_date, end_date) -> str:
	if not start_date:
		return ""
	start = frappe.format(start_date, {"fieldtype": "Date"})
	if not end_date:
		return start
	return f"{start} – {frappe.format(end_date, {'fieldtype': 'Date'})}"


def _get_excel_salary_slips(entry) -> list:
	fields = [
		"name",
		"employee",
		"employee_name",
		"start_date",
		"end_date",
		"total_working_hours",
		"hour_rate",
		"gross_pay",
		"net_pay",
		"salary_structure",
		"total_deduction",
		"company",
		"ss_wage_band",
		"ss_insurable_earnings",
		"ss_employee_amount",
		"ss_employer_amount",
		"current_month_income_tax",
		"total_income_tax",
	]
	# Loan totals are custom fields added only when the Lending app is installed.
	if frappe.db.has_column("Salary Slip", "total_loan_repayment"):
		fields.append("total_loan_repayment")
	return frappe.get_all(
		"Salary Slip",
		filters={"payroll_entry": entry.name, "docstatus": ("<", 2)},
		fields=fields,
		order_by="employee_name asc, employee asc",
	)


def _slip_income_tax(slip) -> float:
	return flt(slip.current_month_income_tax) or flt(slip.total_income_tax)


def _slip_social_amounts(slip) -> tuple[float, float]:
	return flt(slip.ss_employee_amount), flt(slip.ss_employer_amount)


def _ytd_social_by_employee(entry) -> dict[str, tuple[float, float]]:
	"""Social security totals per agent from the start of the fiscal year up to this period."""
	employees = [row.employee for row in (entry.employees or []) if row.employee]
	if not employees or not entry.end_date:
		return {}

	try:
		year_start = get_fiscal_year(entry.end_date, company=entry.company)[1]
	except Exception:
		year_start = datetime.date(getdate(entry.end_date).year, 1, 1)

	slips = frappe.get_all(
		"Salary Slip",
		filters={
			"employee": ("in", employees),
			"docstatus": 1,
			"start_date": (">=", year_start),
			"end_date": ("<=", entry.end_date),
		},
		fields=["employee", "ss_employee_amount", "ss_employer_amount"],
	)

	totals: dict[str, tuple[float, float]] = {}
	for slip in slips:
		employee_amount, employer_amount = totals.get(slip.employee, (0.0, 0.0))
		totals[slip.employee] = (
			employee_amount + flt(slip.ss_employee_amount),
			employer_amount + flt(slip.ss_employer_amount),
		)
	return totals


def _excel_hours_for_employee(
	employee: str,
	slip_total_hours,
	working_by_employee: dict[str, float],
	overtime_by_employee: dict[str, float],
	prefer_attendance: bool = False,
) -> tuple[float, float]:
	"""Return (overtime_hours, regular_hours) for the spreadsheet row."""
	overtime_hours = flt(overtime_by_employee.get(employee))
	attendance_hours = flt(working_by_employee.get(employee))
	if prefer_attendance:
		total_hours = attendance_hours or flt(slip_total_hours)
	else:
		total_hours = flt(slip_total_hours) or attendance_hours
	regular_hours = max(total_hours - overtime_hours, 0.0) if total_hours else 0.0
	return overtime_hours, regular_hours


def _excel_hourly_rate(slip, agent_rate) -> float:
	"""Prefer the agent's CTC over the structure default copied onto the slip."""
	slip_rate = flt(getattr(slip, "hour_rate", 0) if slip else 0)
	agent_rate = flt(agent_rate)
	structure_rate = 0.0
	structure = getattr(slip, "salary_structure", None) if slip else None
	if structure:
		structure_rate = flt(frappe.db.get_value("Salary Structure", structure, "hour_rate"))
	if slip_rate and (not structure_rate or abs(slip_rate - structure_rate) > 0.0001):
		return slip_rate
	return agent_rate or slip_rate


def _hourly_rate_by_employee(entry, slips) -> dict[str, float]:
	from hrms.payroll.daily_pay import get_hour_rate

	on_date = entry.end_date or entry.start_date
	rates: dict[str, float] = {}
	employees = {slip.employee for slip in slips}
	for emp in entry.employees or []:
		if emp.employee:
			employees.add(emp.employee)
	for employee in employees:
		rates[employee] = flt(get_hour_rate(employee, on_date))
	return rates


def _excel_gross_pay(
	slip,
	regular_hours,
	overtime_hours,
	hourly_rate,
	holiday_pay,
	bonus,
	employee: str | None = None,
	holiday_hours: float = 0,
) -> float:
	from hrms.payroll.hourly_gross import (
		compute_hourly_gross_pay,
		slip_uses_hourly_wages,
		structure_uses_hourly_wages,
	)

	structure = getattr(slip, "salary_structure", None) if slip else None
	if not structure and employee:
		structure = frappe.db.get_value(
			"Salary Structure Assignment",
			{"employee": employee, "docstatus": 1},
			"salary_structure",
			order_by="from_date desc",
		)
	hourly = bool(hourly_rate) and (
		(slip and slip_uses_hourly_wages(slip)) or structure_uses_hourly_wages(structure)
	)
	if hourly:
		# Holiday hours are already in regular hours; only add holiday premium / unworked statutory pay.
		holiday_extra = flt(holiday_pay) - flt(holiday_hours) * flt(hourly_rate)
		return compute_hourly_gross_pay(
			regular_hours=regular_hours,
			overtime_hours=overtime_hours,
			hourly_rate=hourly_rate,
			holiday_pay=max(holiday_extra, 0),
			bonus=bonus,
		)
	return flt(getattr(slip, "gross_pay", 0) if slip else 0)


def _excel_net_pay(slip, gross_pay) -> float:
	if not slip:
		return flt(gross_pay)
	deductions = flt(getattr(slip, "total_deduction", 0))
	if not deductions and flt(slip.gross_pay):
		deductions = flt(slip.gross_pay) - flt(slip.net_pay)
	return flt(flt(gross_pay) - deductions, 2)


def _holiday_hours_by_employee(entry) -> dict[str, float]:
	from hrms.payroll.daily_pay import ensure_working_hours_from_times, get_public_holiday_pay_context

	hours: dict[str, float] = {}
	fields = ["employee", "attendance_date", "working_hours", "status"]
	if frappe.db.has_column("Attendance", "in_time"):
		fields += ["in_time", "out_time"]
	for row in _period_attendance(entry, fields, include_draft=True):
		if (row.get("status") or "") == "Absent":
			continue
		if not get_public_holiday_pay_context(row.employee, row.attendance_date):
			continue
		worked = flt(row.working_hours) or flt(ensure_working_hours_from_times(row))
		hours[row.employee] = hours.get(row.employee, 0) + worked
	return hours


def _working_hours_by_employee(entry) -> dict[str, float]:
	"""Attendance hours per agent for the pay period (draft or submitted)."""
	from hrms.payroll.daily_pay import ensure_working_hours_from_times

	hours: dict[str, float] = {}
	fields = ["employee", "working_hours", "status"]
	if frappe.db.has_column("Attendance", "in_time"):
		fields += ["in_time", "out_time"]
	for row in _period_attendance(entry, fields, include_draft=True):
		if (row.get("status") or "") == "Absent":
			continue
		worked = flt(row.working_hours) or flt(ensure_working_hours_from_times(row))
		hours[row.employee] = hours.get(row.employee, 0) + worked
	return hours


def _overtime_hours_by_employee(entry) -> dict[str, float]:
	"""Overtime hours per agent, preferring Overtime Slip detail rows over attendance."""
	hours: dict[str, float] = {}
	slips = frappe.get_all(
		"Overtime Slip",
		filters={"payroll_entry": entry.name, "docstatus": ("<", 2)},
		fields=["name", "employee", "total_overtime_duration"],
	)

	if slips:
		employee_by_slip = {row.name: row.employee for row in slips}
		details = frappe.get_all(
			"Overtime Details",
			filters={"parent": ("in", list(employee_by_slip))},
			fields=["parent", "overtime_duration"],
		)
		if details:
			for detail in details:
				employee = employee_by_slip.get(detail.parent)
				if employee:
					hours[employee] = hours.get(employee, 0) + flt(detail.overtime_duration)
			return hours

		for slip in slips:
			hours[slip.employee] = hours.get(slip.employee, 0) + flt(slip.total_overtime_duration)
		return hours

	ot_field = (
		["employee", "actual_overtime_duration"]
		if frappe.db.has_column("Attendance", "actual_overtime_duration")
		else ["employee"]
	)
	for row in _period_attendance(entry, ot_field, include_draft=True):
		hours[row.employee] = hours.get(row.employee, 0) + flt(row.get("actual_overtime_duration"))
	return hours


def _holiday_pay_by_employee(entry) -> dict[str, float]:
	"""Total pay booked on public holidays, which already includes any statutory premium."""
	from hrms.payroll.daily_pay import get_public_holiday_pay_context

	holiday_pay: dict[str, float] = {}
	is_holiday: dict[tuple[str, str], bool] = {}
	for row in _period_attendance(entry, ["employee", "attendance_date", "daily_pay"]):
		key = (row.employee, str(row.attendance_date))
		if key not in is_holiday:
			is_holiday[key] = bool(get_public_holiday_pay_context(row.employee, row.attendance_date))
		if is_holiday[key]:
			holiday_pay[row.employee] = holiday_pay.get(row.employee, 0) + flt(row.daily_pay)
	return holiday_pay


def _period_attendance(entry, fields: list[str], include_draft: bool = False) -> list[dict]:
	if not entry.start_date or not entry.end_date:
		return []

	filters = {
		"docstatus": ("<", 2) if include_draft else 1,
		"attendance_date": ("between", [entry.start_date, entry.end_date]),
	}
	employees = [row.employee for row in (entry.employees or []) if row.employee]
	if employees:
		filters["employee"] = ("in", employees)
	elif entry.company:
		filters["company"] = entry.company

	return frappe.get_all("Attendance", filters=filters, fields=fields)


def _bonus_by_salary_slip(slip_names: list[str]) -> dict[str, float]:
	if not slip_names:
		return {}

	SalaryDetail = frappe.qb.DocType("Salary Detail")
	SalaryComponent = frappe.qb.DocType("Salary Component")
	rows = (
		frappe.qb.from_(SalaryDetail)
		.inner_join(SalaryComponent)
		.on(SalaryDetail.salary_component == SalaryComponent.name)
		.select(SalaryDetail.parent, SalaryDetail.amount)
		.where(
			(SalaryDetail.parent.isin(slip_names))
			& (SalaryDetail.parentfield == "earnings")
			& (SalaryComponent.earning_category == "Bonus")
		)
	).run(as_dict=True)

	totals: dict[str, float] = {}
	for row in rows:
		totals[row.parent] = totals.get(row.parent, 0) + flt(row.amount)
	return totals


def _as_payroll_entry_names(names: str | list | tuple | None) -> list[str]:
	if isinstance(names, str):
		names = frappe.parse_json(names)
	if not isinstance(names, (list, tuple)):
		frappe.throw(_("No Payroll Entries selected"))
	return [name for name in names if name]


def _is_cancelled_payroll_entry(doc) -> bool:
	return cint(doc.docstatus) == 2 or doc.status == "Cancelled"


@frappe.whitelist()
def bulk_cancel_payroll_entries(names: str | list) -> dict:
	"""Cancel submitted payroll runs and discard drafts so they can be deleted next."""
	cancelled = []
	skipped = []
	errors = []

	for name in _as_payroll_entry_names(names):
		try:
			doc = frappe.get_doc("Payroll Entry", name)
			if _is_cancelled_payroll_entry(doc):
				skipped.append(name)
				continue
			if cint(doc.docstatus) == 1:
				doc.check_permission("cancel")
				doc.detach_standalone_links()
				doc.cancel()
			elif cint(doc.docstatus) == 0:
				doc.check_permission("write")
				if not hasattr(doc, "discard"):
					frappe.throw(_("Cannot cancel a draft Payroll Entry."))
				doc.detach_standalone_links()
				doc.discard()
			else:
				skipped.append(name)
				continue
			cancelled.append(name)
			if not frappe.in_test:
				frappe.db.commit()
		except Exception as e:
			if not frappe.in_test:
				frappe.db.rollback()
			errors.append({"name": name, "error": frappe.utils.cstr(e)})

	return {"cancelled": cancelled, "skipped": skipped, "errors": errors}


@frappe.whitelist()
def bulk_delete_payroll_entries(names: str | list) -> dict:
	"""Permanently delete cancelled payroll runs."""
	deleted = []
	errors = []

	for name in _as_payroll_entry_names(names):
		try:
			doc = frappe.get_doc("Payroll Entry", name)
			doc.check_permission("delete")
			if not _is_cancelled_payroll_entry(doc):
				frappe.throw(_("Cancel this Payroll Entry before deleting it."))
			doc.detach_standalone_links()
			frappe.delete_doc("Payroll Entry", name)
			deleted.append(name)
			if not frappe.in_test:
				frappe.db.commit()
		except Exception as e:
			if not frappe.in_test:
				frappe.db.rollback()
			errors.append({"name": name, "error": frappe.utils.cstr(e)})

	return {"deleted": deleted, "errors": errors}
