# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from dateutil.relativedelta import relativedelta

import frappe
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import add_days, add_months, cstr, date_diff, flt, get_first_day, get_last_day

import erpnext
from erpnext.accounts.utils import get_fiscal_year, getdate, nowdate
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.employee_advance.employee_advance import (
	create_return_through_additional_salary,
)
from hrms.payroll.doctype.payroll_entry.payroll_entry import (
	ALL_CLIENTS,
	PayrollEntry,
	bulk_cancel_payroll_entries,
	bulk_delete_payroll_entries,
	get_end_date,
	get_start_end_dates,
	payroll_client_query,
)
from hrms.payroll.doctype.salary_component.test_salary_component import create_salary_component
from hrms.payroll.doctype.salary_slip.salary_slip_loan_utils import if_lending_app_installed
from hrms.payroll.doctype.salary_slip.test_salary_slip import (
	create_account,
	make_deduction_salary_component,
	make_earning_salary_component,
	mark_attendance,
	set_salary_component_account,
)
from hrms.payroll.doctype.salary_structure.test_salary_structure import (
	create_salary_structure_assignment,
	make_salary_structure,
)
from hrms.tests.test_utils import create_department
from hrms.tests.utils import HRMSTestSuite
from hrms.utils import get_date_range


class TestPayrollEntry(HRMSTestSuite):
	def setUp(self):
		make_earning_salary_component(setup=True, company_list=["_Test Company"])
		make_deduction_salary_component(setup=True, test_tax=False, company_list=["_Test Company"])

		frappe.db.set_value("Company", "_Test Company", "default_holiday_list", "_Test Holiday List")
		frappe.db.set_single_value("Payroll Settings", "email_salary_slip_to_employee", 0)
		frappe.db.set_value("Account", "Employee Advances - _TC", "account_type", "Receivable")
		# set default payable account
		default_account = frappe.db.get_value("Company", "_Test Company", "default_payroll_payable_account")
		if not default_account or default_account != "_Test Payroll Payable - _TC":
			create_account(
				account_name="_Test Payroll Payable",
				company="_Test Company",
				parent_account="Current Liabilities - _TC",
				account_type="Payable",
			)
			frappe.db.set_value(
				"Company", "_Test Company", "default_payroll_payable_account", "_Test Payroll Payable - _TC"
			)

		payroll_account = frappe.get_doc("Account", "_Test Payroll Payable - _TC")
		if payroll_account and payroll_account.account_type != "Payable":
			frappe.db.set_value("Account", "_Test Payroll Payable - _TC", "account_type", "Payable")

		if "lending" in frappe.get_installed_apps():
			frappe.db.set_value("Company", "_Test Company", "loan_accrual_frequency", "Monthly")

	def test_payroll_entry(self):
		company = frappe.get_doc("Company", "_Test Company")
		employee = frappe.db.get_value("Employee", {"company": "_Test Company"})
		setup_salary_structure(employee, company)

		dates = get_start_end_dates("Monthly", nowdate())
		make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company.default_payroll_payable_account,
			currency=company.default_currency,
			company=company.name,
			cost_center="Main - _TC",
		)

	def test_multi_currency_payroll_entry(self):
		company = frappe.get_doc("Company", "_Test Company")
		create_department("Accounts")
		employee = make_employee(
			"test_muti_currency_employee@payroll.com", company=company.name, department="Accounts - _TC"
		)
		salary_structure = "_Test Multi Currency Salary Structure"
		setup_salary_structure(employee, company, "USD", salary_structure)

		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company.default_payroll_payable_account,
			currency="USD",
			exchange_rate=70,
			company=company.name,
			cost_center="Main - _TC",
			payment_account="Cash - _TC",
		)

		salary_slip = frappe.db.get_value("Salary Slip", {"payroll_entry": payroll_entry.name}, "name")
		salary_slip = frappe.get_doc("Salary Slip", salary_slip)

		payroll_entry.reload()
		payroll_je = salary_slip.journal_entry
		if payroll_je:
			payroll_je_doc = frappe.get_doc("Journal Entry", payroll_je)
			self.assertEqual(salary_slip.base_gross_pay, payroll_je_doc.total_debit)
			self.assertEqual(salary_slip.base_gross_pay, payroll_je_doc.total_credit)

		je = frappe.qb.DocType("Journal Entry")
		jea = frappe.qb.DocType("Journal Entry Account")
		payment_entry = (
			frappe.qb.from_(je)
			.from_(jea)
			.select(
				Coalesce(Sum(je.total_debit), 0).as_("total_debit"),
				Coalesce(Sum(je.total_credit), 0).as_("total_credit"),
			)
			.where(je.name == jea.parent)
			.where((je.voucher_type == "Bank Entry") | (je.voucher_type == "Cash Entry"))
			.where(jea.reference_name == payroll_entry.name)
		).run(as_dict=1)
		# Direct payment JE totals equal gross (earnings vs deductions + Bank/Cash)
		self.assertEqual(salary_slip.base_gross_pay, payment_entry[0].total_debit)
		self.assertEqual(salary_slip.base_gross_pay, payment_entry[0].total_credit)

	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 0}
	)
	def test_payroll_entry_with_employee_cost_center(self):
		department = create_department("Cost Center Test")

		employee1 = make_employee(
			"test_emp1@example.com",
			payroll_cost_center="_Test Cost Center - _TC",
			department=department,
			company="_Test Company",
		)
		employee2 = make_employee("test_emp2@example.com", department=department, company="_Test Company")

		create_assignments_with_cost_centers(employee1, employee2)

		dates = get_start_end_dates("Monthly", nowdate())
		pe = make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account="_Test Payroll Payable - _TC",
			currency="INR",
			department=department,
			company="_Test Company",
			payment_account="Cash - _TC",
			cost_center="Main - _TC",
		)
		je = frappe.db.get_value("Salary Slip", {"payroll_entry": pe.name}, "journal_entry")
		jea = frappe.qb.DocType("Journal Entry Account")
		je_entries = (
			frappe.qb.from_(jea)
			.select(jea.account, jea.cost_center, jea.debit, jea.credit)
			.where(jea.parent == je)
			.orderby(jea.account)
			.orderby(jea.cost_center)
		).run()
		expected_je = (
			("Cash - _TC", "Main - _TC", 0.0, 155600.0),
			("Salary - _TC", "_Test Cost Center - _TC", 124800.0, 0.0),
			("Salary - _TC", "_Test Cost Center 2 - _TC", 31200.0, 0.0),
			("Salary Deductions - _TC", "_Test Cost Center - _TC", 0.0, 320.0),
			("Salary Deductions - _TC", "_Test Cost Center 2 - _TC", 0.0, 80.0),
		)

		self.assertEqual(je_entries, expected_je)

	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 0}
	)
	def test_employee_cost_center_breakup(self):
		"""Test only the latest salary structure assignment is considered for cost center breakup"""
		COMPANY = "_Test Company"
		COST_CENTERS = {"_Test Cost Center - _TC": 60, "_Test Cost Center 2 - _TC": 40}
		department = create_department("Cost Center Test")
		employee = make_employee("test_emp1@example.com", department=department, company=COMPANY)
		salary_structure = make_salary_structure(
			"_Test Salary Structure 2",
			"Monthly",
			employee,
			company=COMPANY,
		)

		# update cost centers in salary structure assignment for employee
		new_assignment = frappe.db.get_value(
			"Salary Structure Assignment",
			{"employee": employee, "salary_structure": salary_structure.name, "docstatus": 1},
			"name",
		)
		new_assignment = frappe.get_doc("Salary Structure Assignment", new_assignment)
		new_assignment.payroll_cost_centers = []
		for cost_center, percentage in COST_CENTERS.items():
			new_assignment.append(
				"payroll_cost_centers", {"cost_center": cost_center, "percentage": percentage}
			)
		new_assignment.save()

		# make an old salary structure assignment to test and ensure old cost center mapping is excluded
		old_assignment = frappe.copy_doc(new_assignment)
		old_assignment.from_date = add_months(new_assignment.from_date, -1)
		old_assignment.payroll_cost_centers = []
		old_assignment.append("payroll_cost_centers", {"cost_center": "Main - _TC", "percentage": 100})
		old_assignment.submit()

		dates = get_start_end_dates("Monthly", nowdate())
		pe = make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account="_Test Payroll Payable - _TC",
			currency="INR",
			department=department,
			company="_Test Company",
			payment_account="Cash - _TC",
			cost_center="Main - _TC",
		)

		# only new cost center breakup is considered
		cost_centers = pe.get_payroll_cost_centers_for_employee(employee, "_Test Salary Structure 2")
		self.assertEqual(cost_centers, COST_CENTERS)

	def test_get_end_date(self):
		self.assertEqual(get_end_date("2017-01-01", "monthly"), {"end_date": "2017-01-31"})
		self.assertEqual(get_end_date("2017-02-01", "monthly"), {"end_date": "2017-02-28"})
		self.assertEqual(get_end_date("2017-02-01", "fortnightly"), {"end_date": "2017-02-14"})
		self.assertEqual(get_end_date("2017-02-01", "bimonthly"), {"end_date": ""})
		self.assertEqual(get_end_date("2017-01-01", "bimonthly"), {"end_date": ""})
		self.assertEqual(get_end_date("2020-02-15", "bimonthly"), {"end_date": ""})
		self.assertEqual(get_end_date("2017-02-15", "monthly"), {"end_date": "2017-03-14"})
		self.assertEqual(get_end_date("2017-02-15", "daily"), {"end_date": "2017-02-15"})

	def test_get_payroll_entries_for_jv_filters_docstatus(self):
		from hrms.payroll.doctype.payroll_entry.payroll_entry import get_payroll_entries_for_jv

		draft_pe = frappe.new_doc("Payroll Entry")
		draft_pe.company = "_Test Company"
		draft_pe.currency = "INR"
		draft_pe.payroll_frequency = "Monthly"
		draft_pe.start_date = "2026-07-06"
		draft_pe.end_date = "2026-07-31"
		draft_pe.flags.ignore_mandatory = True
		draft_pe.insert(ignore_permissions=True)

		res = get_payroll_entries_for_jv("Payroll Entry", "%", "name", 0, 100, {})
		entry_names = [d[0] for d in res]
		self.assertNotIn(draft_pe.name, entry_names)

	@if_lending_app_installed
	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 1}
	)
	def test_loan_with_settings_enabled(self):
		from lending.loan_management.doctype.loan.test_loan import make_loan_disbursement_entry

		frappe.db.delete("Loan")

		[applicant, branch, currency, payroll_payable_account] = setup_lending()
		loan = create_loan_for_employee(applicant)
		dates = frappe._dict({"start_date": add_months(getdate(), -1), "end_date": getdate()})

		make_loan_disbursement_entry(
			loan.name,
			loan.loan_amount,
			disbursement_date=dates.start_date,
			repayment_start_date=dates.end_date,
		)
		make_payroll_entry(
			company="_Test Company",
			start_date=dates.start_date,
			payable_account=payroll_payable_account,
			currency=currency,
			end_date=dates.end_date,
			branch=branch,
			cost_center="Main - _TC",
			payment_account="Cash - _TC",
		)

		name = frappe.db.get_value(
			"Salary Slip", {"posting_date": dates.end_date, "employee": applicant}, "name"
		)

		salary_slip = frappe.get_doc("Salary Slip", name)
		for row in salary_slip.loans:
			if row.loan == loan.name:
				interest_amount = flt(
					(280000) * 8.4 / 100 * (date_diff(dates.end_date, dates.start_date)) / 365, 2
				)
				self.assertEqual(row.interest_amount, interest_amount)
				self.assertEqual(row.total_payment, interest_amount + row.principal_amount)

		[party_type, party] = get_repayment_party_type(loan.name)

		self.assertEqual(party_type, "Employee")
		self.assertEqual(party, applicant)

	@if_lending_app_installed
	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 0}
	)
	def test_loan_with_settings_disabled(self):
		from lending.loan_management.doctype.loan.test_loan import make_loan_disbursement_entry

		frappe.db.delete("Loan")

		[applicant, branch, currency, payroll_payable_account] = setup_lending()
		loan = create_loan_for_employee(applicant)
		dates = frappe._dict({"start_date": add_months(getdate(), -1), "end_date": getdate()})

		make_loan_disbursement_entry(
			loan.name,
			loan.loan_amount,
			disbursement_date=dates.start_date,
			repayment_start_date=dates.end_date,
		)
		make_payroll_entry(
			company="_Test Company",
			start_date=dates.start_date,
			payable_account=payroll_payable_account,
			currency=currency,
			end_date=dates.end_date,
			branch=branch,
			cost_center="Main - _TC",
			payment_account="Cash - _TC",
		)

		[party_type, party] = get_repayment_party_type(loan.name)

		self.assertEqual(cstr(party_type), "")
		self.assertEqual(cstr(party), "")

	def test_salary_slip_operation_queueing(self):
		company = "_Test Company"
		company_doc = frappe.get_doc("Company", company)
		employee = make_employee("test_employee@payroll.com", company=company)
		setup_salary_structure(employee, company_doc)

		# enqueue salary slip creation via payroll entry
		# Payroll Entry status should change to Queued
		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = get_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company_doc.default_payroll_payable_account,
			currency=company_doc.default_currency,
			company=company_doc.name,
			cost_center="Main - _TC",
		)
		frappe.flags.enqueue_payroll_entry = True
		payroll_entry.submit()
		payroll_entry.reload()

		self.assertEqual(payroll_entry.status, "Queued")
		frappe.flags.enqueue_payroll_entry = False

	def test_salary_slip_operation_failure(self):
		company = "_Test Company"
		company_doc = frappe.get_doc("Company", company)
		employee = make_employee("test_employee@payroll.com", company=company)

		salary_structure = make_salary_structure(
			"_Test Salary Structure",
			"Monthly",
			employee,
			company=company,
			currency=company_doc.default_currency,
		)

		# reset account in component to test submission failure
		component = frappe.get_doc("Salary Component", salary_structure.earnings[0].salary_component)
		component.accounts = []
		component.save()

		# salary slip submission via payroll entry
		# Payroll Entry status should change to Failed because of the missing account setup
		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = get_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company_doc.default_payroll_payable_account,
			currency=company_doc.default_currency,
			company=company_doc.name,
			cost_center="Main - _TC",
		)

		# set employee as Inactive to check creation failure
		frappe.db.set_value("Employee", employee, "status", "Inactive")
		payroll_entry.submit()
		payroll_entry.reload()
		self.assertEqual(payroll_entry.status, "Failed")
		self.assertIsNotNone(payroll_entry.error_message)

		frappe.db.set_value("Employee", employee, "status", "Active")

		payroll_entry.create_salary_slips()
		payroll_entry.submit()
		payroll_entry.submit_salary_slips()
		payroll_entry.reload()
		self.assertEqual(payroll_entry.status, "Failed")
		self.assertIsNotNone(payroll_entry.error_message)

		# set accounts
		for data in frappe.get_all("Salary Component", pluck="name"):
			set_salary_component_account(data, company_list=[company])

		# Payroll Entry successful, status should change to Submitted

		payroll_entry.create_salary_slips()
		payroll_entry.submit()
		payroll_entry.submit_salary_slips()
		payroll_entry.reload()

		self.assertEqual(payroll_entry.status, "Submitted")
		self.assertEqual(payroll_entry.error_message, "")

	def test_payroll_entry_cancellation(self):
		company_doc = frappe.get_doc("Company", "_Test Company")
		employee = make_employee("test_employee@payroll.com", company=company_doc.name)

		setup_salary_structure(employee, company_doc)
		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company_doc.default_payroll_payable_account,
			currency=company_doc.default_currency,
			company=company_doc.name,
			cost_center="Main - _TC",
			payment_account="Cash - _TC",
		)
		# Direct payment JE is already submitted with the salary slips
		journal_entries = get_linked_journal_entries(payroll_entry.name, docstatus=1)
		self.assertEqual(len(journal_entries), 1)

		salary_slip = frappe.db.get_value("Salary Slip", {"payroll_entry": payroll_entry.name}, "name")
		self.assertIsNotNone(salary_slip)

		frappe.flags.enqueue_payroll_entry = True
		payroll_entry.cancel()
		frappe.flags.enqueue_payroll_entry = False
		self.assertEqual(payroll_entry.status, "Cancelled")

		salary_slip = frappe.db.get_value("Salary Slip", {"payroll_entry": payroll_entry.name}, "name")
		self.assertIsNone(salary_slip)

		# 1 cancelled JV
		journal_entries = get_linked_journal_entries(payroll_entry.name, docstatus=2)
		self.assertEqual(len(journal_entries), 1)

	def test_payroll_entry_cancellation_with_hr_manager(self):
		company_doc = frappe.get_doc("Company", "_Test Company")
		employee = make_employee("test_hr_manager_employee@payroll.com", company=company_doc.name)

		setup_salary_structure(employee, company_doc)
		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company_doc.default_payroll_payable_account,
			currency=company_doc.default_currency,
			company=company_doc.name,
			cost_center="Main - _TC",
			payment_account="Cash - _TC",
		)

		hr_user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "test_hr_manager@payroll.com",
				"first_name": "Test HR Manager",
				"enabled": 1,
			}
		).insert(ignore_if_duplicate=True)
		hr_user.add_roles("HR Manager")
		frappe.set_user(hr_user.name)

		payroll_entry.submit()
		self.assertEqual(payroll_entry.status, "Submitted")

		payroll_entry.cancel()
		self.assertEqual(payroll_entry.status, "Cancelled")

		frappe.set_user("Administrator")

	def test_payroll_entry_status(self):
		company_doc = frappe.get_doc("Company", "_Test Company")
		employee = make_employee("test_employee@payroll.com", company=company_doc.name)

		setup_salary_structure(employee, company_doc)
		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = get_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company_doc.default_payroll_payable_account,
			currency=company_doc.default_currency,
			company=company_doc.name,
			cost_center="Main - _TC",
		)
		payroll_entry.submit()
		self.assertEqual(payroll_entry.status, "Submitted")

		payroll_entry.cancel()
		self.assertEqual(payroll_entry.status, "Cancelled")

	def test_payroll_entry_cancellation_against_cancelled_journal_entry(self):
		company_doc = frappe.get_doc("Company", "_Test Company")
		employee = make_employee("test_pe_cancellation@payroll.com", company=company_doc.name)

		setup_salary_structure(employee, company_doc)
		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company_doc.default_payroll_payable_account,
			currency=company_doc.default_currency,
			company=company_doc.name,
			cost_center="Main - _TC",
			payment_account="Cash - _TC",
		)

		# cancel the salary slip
		salary_slip = frappe.db.get_value("Salary Slip", {"payroll_entry": payroll_entry.name}, "name")
		salary_slip = frappe.get_doc("Salary Slip", salary_slip)
		salary_slip.cancel()

		# cancel the journal entries
		jvs = get_linked_journal_entries(payroll_entry.name)

		for jv in jvs:
			jv_doc = frappe.get_doc("Journal Entry", jv.parent)
			self.assertEqual(jv_doc.accounts[0].cost_center, payroll_entry.cost_center)
			jv_doc.cancel()

		payroll_entry.cancel()
		self.assertEqual(payroll_entry.status, "Cancelled")

	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 1}
	)
	def test_payroll_accrual_journal_entry_with_employee_tagging(self):
		company_doc = frappe.get_doc("Company", "_Test Company")
		employee = make_employee(
			"test_payroll_accrual_journal_entry_with_employee_tagging@payroll.com", company=company_doc.name
		)

		setup_salary_structure(employee, company_doc)

		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company_doc.default_payroll_payable_account,
			currency=company_doc.default_currency,
			company=company_doc.name,
			cost_center="Main - _TC",
			payment_account="Cash - _TC",
		)

		salary_slip = frappe.db.get_value("Salary Slip", {"payroll_entry": payroll_entry.name}, "name")
		salary_slip = frappe.get_doc("Salary Slip", salary_slip)
		payroll_entry.reload()
		payroll_je = salary_slip.journal_entry

		if payroll_je:
			payroll_je_doc = frappe.get_doc("Journal Entry", payroll_je)
			cash_lines = [account for account in payroll_je_doc.accounts if account.account == "Cash - _TC"]
			self.assertTrue(cash_lines, "Expected Cash credit for direct payroll payment")
			self.assertTrue(any(flt(line.credit) > 0 for line in cash_lines))

	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 0}
	)
	def test_payroll_accrual_journal_entry_without_employee_tagging(self):
		company_doc = frappe.get_doc("Company", "_Test Company")
		employee = make_employee(
			"test_payroll_accrual_journal_entry_without_employee_tagging@payroll.com",
			company=company_doc.name,
		)

		setup_salary_structure(employee, company_doc)

		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company_doc.default_payroll_payable_account,
			currency=company_doc.default_currency,
			company=company_doc.name,
			cost_center="Main - _TC",
			payment_account="Cash - _TC",
		)

		salary_slip = frappe.db.get_value("Salary Slip", {"payroll_entry": payroll_entry.name}, "name")
		salary_slip = frappe.get_doc("Salary Slip", salary_slip)
		payroll_entry.reload()
		payroll_je = salary_slip.journal_entry

		if payroll_je:
			payroll_je_doc = frappe.get_doc("Journal Entry", payroll_je)
			for account in payroll_je_doc.accounts:
				if account.account == "Cash - _TC":
					self.assertEqual(account.party_type, None)
					self.assertEqual(account.party, None)

	def test_advance_deduction_in_accrual_journal_entry(self):
		from hrms.hr.doctype.employee_advance.test_employee_advance import (
			make_employee_advance,
			make_payment_entry,
		)

		company_doc = frappe.get_doc("Company", "_Test Company")
		employee = make_employee("test_employee@payroll.com", company=company_doc.name)

		setup_salary_structure(employee, company_doc)

		# create employee advance
		advance = make_employee_advance(employee, {"repay_unclaimed_amount_from_salary": 1})
		make_payment_entry(advance)
		advance.reload()

		# return advance through additional salary (deduction)
		component = create_salary_component("Advance Salary - Deduction", **{"type": "Deduction"})
		component.append(
			"accounts",
			{"company": company_doc.name, "account": "Employee Advances - _TC"},
		)
		component.save()

		additional_salary = create_return_through_additional_salary(advance)
		additional_salary.salary_component = component.name
		additional_salary.payroll_date = nowdate()
		additional_salary.amount = advance.paid_amount
		additional_salary.submit()

		# payroll entry
		dates = get_start_end_dates("Monthly", nowdate())
		make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company_doc.default_payroll_payable_account,
			currency=company_doc.default_currency,
			company=company_doc.name,
			cost_center="Main - _TC",
			payment_account="Cash - _TC",
		)
		deduction_entry = frappe.get_all(
			"Journal Entry Account",
			fields=["account", "party", "debit", "credit"],
			filters={
				"reference_type": "Employee Advance",
				"reference_name": advance.name,
				"is_advance": "Yes",
			},
		)[0]

		expected_entry = {
			"account": "Employee Advances - _TC",
			"party": employee,
			"debit": 0.0,
			"credit": advance.paid_amount,
		}

		self.assertEqual(deduction_entry, expected_entry)

	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 1}
	)
	def test_employee_wise_bank_entry_with_cost_centers(self):
		"""Direct Bank/Cash payment is booked on slip submit; no separate payable bank entry."""
		department = create_department("Cost Center Test")
		employee1 = make_employee(
			"test_emp1@example.com",
			payroll_cost_center="_Test Cost Center - _TC",
			department=department,
			company="_Test Company",
		)
		employee2 = make_employee("test_emp2@example.com", department=department, company="_Test Company")

		create_assignments_with_cost_centers(employee1, employee2)

		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account="_Test Payroll Payable - _TC",
			currency="INR",
			department=department,
			company="_Test Company",
			payment_account="Cash - _TC",
			cost_center="Main - _TC",
		)
		payroll_entry.reload()

		je_name = frappe.db.get_value("Salary Slip", {"payroll_entry": payroll_entry.name}, "journal_entry")
		self.assertTrue(je_name)

		cash_credit = frappe.db.get_value(
			"Journal Entry Account",
			{"parent": je_name, "account": "Cash - _TC"},
			"credit",
		)
		self.assertEqual(flt(cash_credit), 155600.0)
		self.assertFalse(
			frappe.db.exists(
				"Journal Entry Account",
				{"parent": je_name, "account": "_Test Payroll Payable - _TC"},
			)
		)

	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 0}
	)
	def test_direct_payment_splits_bank_and_cash(self):
		"""Bank Transfer and Cash employees credit the matching Company payment accounts."""
		company = frappe.get_doc("Company", "_Test Company")
		department = create_department("Pay Mode Split")

		bank_account = frappe.db.get_value(
			"Account", {"account_type": "Bank", "company": company.name, "is_group": 0}, "name"
		)
		cash_account = "Cash - _TC"
		if not bank_account:
			parent = frappe.db.get_value(
				"Account", {"is_group": 1, "company": company.name, "root_type": "Asset"}, "name"
			)
			doc = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "_Test Payroll Bank",
					"parent_account": parent,
					"company": company.name,
					"account_type": "Bank",
					"is_group": 0,
				}
			).insert(ignore_permissions=True)
			bank_account = doc.name

		frappe.db.set_value("Company", company.name, "default_bank_account", bank_account)
		frappe.db.set_value("Company", company.name, "default_cash_account", cash_account)

		employee_bank = make_employee(
			"test_bank_pay@example.com",
			department=department,
			company=company.name,
			salary_mode="Bank",
		)
		employee_cash = make_employee(
			"test_cash_pay@example.com",
			department=department,
			company=company.name,
			salary_mode="Cash",
		)
		setup_salary_structure(employee_bank, company)
		setup_salary_structure(employee_cash, company, salary_structure="_Test Salary Structure Cash Mode")

		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			currency=company.default_currency,
			department=department,
			company=company.name,
			cost_center="Main - _TC",
			payment_account=cash_account,
		)

		je_name = frappe.db.get_value("Salary Slip", {"payroll_entry": payroll_entry.name}, "journal_entry")
		accounts = frappe.get_all(
			"Journal Entry Account",
			filters={"parent": je_name, "credit": (">", 0)},
			fields=["account", "credit"],
		)
		credited = {row.account for row in accounts}
		self.assertIn(bank_account, credited)
		self.assertIn(cash_account, credited)
		self.assertNotIn("_Test Payroll Payable - _TC", credited)

	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 0}
	)
	def test_direct_payment_uses_selected_bpo_bank(self):
		"""Selecting Heritage Bank wires agent pay from that BPO source account."""
		company = frappe.get_doc("Company", "_Test Company")
		department = create_department("Heritage Wire")
		default_bank = frappe.db.get_value("Company", company.name, "default_bank_account")
		heritage_gl = _ensure_bank_gl(company.name, "_Test Heritage Wire")
		self.assertNotEqual(heritage_gl, default_bank)

		source = _ensure_company_bank_account(company.name, "Heritage Bank", heritage_gl)
		employee = make_employee(
			"test_heritage_wire@example.com",
			department=department,
			company=company.name,
			salary_mode="Bank",
		)
		if frappe.get_meta("Employee").has_field("bank_name"):
			frappe.db.set_value(
				"Employee",
				employee,
				{"bank_name": "Belize Bank", "bank_ac_no": "123456789"},
			)
		setup_salary_structure(employee, company)

		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			currency=company.default_currency,
			department=department,
			company=company.name,
			cost_center="Main - _TC",
			bank_account=source,
		)
		self.assertEqual(payroll_entry.payment_account, heritage_gl)

		je_name = frappe.db.get_value("Salary Slip", {"payroll_entry": payroll_entry.name}, "journal_entry")
		credited = frappe.get_all(
			"Journal Entry Account",
			filters={"parent": je_name, "credit": (">", 0)},
			fields=["account", "bank_account"],
		)
		self.assertIn(heritage_gl, {row.account for row in credited})
		self.assertIn(source, {row.bank_account for row in credited})
		if default_bank:
			self.assertNotIn(default_bank, {row.account for row in credited})

		slip = frappe.get_doc("Salary Slip", {"payroll_entry": payroll_entry.name, "employee": employee})
		if frappe.get_meta("Salary Slip").has_field("payment_status"):
			self.assertEqual(slip.payment_status, "Paid")
			self.assertEqual(slip.paid_from_bank_account, source)
			self.assertEqual(slip.paid_from_bank, "Heritage Bank")
			self.assertEqual(slip.bank_name, "Belize Bank")
			self.assertEqual(slip.bank_account_no, "123456789")

	def test_payroll_source_banks_include_belize_banks(self):
		from hrms.hr.belize_banks import BELIZE_BANKS, get_company_payment_banks

		banks = get_company_payment_banks("_Test Company")
		names = {row["bank"] for row in banks}
		for bank in BELIZE_BANKS:
			self.assertIn(bank, names)

	def test_default_payroll_bank_account_prefills_a_company_bank(self):
		from hrms.hr.belize_banks import get_company_payment_banks, get_default_payroll_bank_account

		banks = get_company_payment_banks("_Test Company")
		self.assertTrue(banks)
		default = get_default_payroll_bank_account("_Test Company")
		self.assertIn(default, {row["name"] for row in banks})

	def test_payroll_source_banks_include_connected_accounts_without_company_flag(self):
		from hrms.hr.belize_banks import get_company_payment_banks, payroll_bank_account_query

		company = "_Test Company"
		if not frappe.db.exists("Bank", "Heritage Bank"):
			frappe.get_doc({"doctype": "Bank", "bank_name": "Heritage Bank"}).insert(ignore_permissions=True)

		account_name = "Heritage Payroll Test"
		existing = frappe.db.get_value("Bank Account", {"account_name": account_name}, "name")
		if existing:
			frappe.delete_doc("Bank Account", existing, force=True, ignore_permissions=True)

		doc = {
			"doctype": "Bank Account",
			"account_name": account_name,
			"bank": "Heritage Bank",
			"company": company,
			"is_company_account": 0,
			"bank_account_no": "23344432223",
		}
		meta = frappe.get_meta("Bank Account")
		if meta.has_field("account_type"):
			doc["account_type"] = "Bank"
		bank_account = frappe.get_doc(doc).insert(ignore_permissions=True)

		banks = get_company_payment_banks(company)
		self.assertIn(bank_account.name, {row["name"] for row in banks})

		results = payroll_bank_account_query(
			"Bank Account", "Heritage Payroll", "name", 0, 20, {"company": company}
		)
		self.assertTrue(any(row[0] == bank_account.name for row in results))

	def test_validate_attendance(self):
		company = frappe.get_doc("Company", "_Test Company")
		employee = frappe.db.get_value("Employee", {"company": "_Test Company"})
		setup_salary_structure(employee, company)

		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = get_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company.default_payroll_payable_account,
			currency=company.default_currency,
			company=company.name,
			cost_center="Main - _TC",
		)

		# case 1: validate unmarked attendance
		payroll_entry.validate_attendance = True
		employees = payroll_entry.get_employees_with_unmarked_attendance()
		self.assertEqual(employees[0]["employee"], employee)

		# case 2: employee should not be flagged for remaining payroll days for a mid-month relieving date
		relieving_date = add_days(payroll_entry.start_date, 15)
		frappe.db.set_value("Employee", employee, "relieving_date", relieving_date)

		for date in get_date_range(payroll_entry.start_date, relieving_date):
			mark_attendance(employee, date, "Present", ignore_validate=True)

		employees = payroll_entry.get_employees_with_unmarked_attendance()
		self.assertFalse(employees)

		# case 3: employee should not flagged for remaining payroll days
		frappe.db.set_value("Employee", employee, "relieving_date", None)

		for date in get_date_range(add_days(relieving_date, 1), payroll_entry.end_date):
			mark_attendance(employee, date, "Present", ignore_validate=True)

		employees = payroll_entry.get_employees_with_unmarked_attendance()
		self.assertFalse(employees)

	@HRMSTestSuite.change_settings(
		"Payroll Settings",
		{
			"payroll_based_on": "Attendance",
			"consider_unmarked_attendance_as": "Absent",
			"include_holidays_in_total_working_days": 1,
			"consider_marked_attendance_on_holidays": 1,
			"process_payroll_accounting_entry_based_on_employee": 1,
		},
	)
	def test_skip_bank_entry_for_employees_with_zero_amount(self):
		company_doc = frappe.get_doc("Company", "_Test Company")
		employee1 = make_employee("test_employee11@payroll.com", company=company_doc.name)
		employee2 = make_employee("test_employee12@payroll.com", company=company_doc.name)

		setup_salary_structure(employee1, company_doc)
		setup_salary_structure(employee2, company_doc)

		dates = get_start_end_dates("Monthly", nowdate())
		for date in get_date_range(dates.start_date, dates.end_date):
			mark_attendance(employee1, date, "Present", ignore_validate=True)

		payroll_entry = get_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company_doc.default_payroll_payable_account,
			currency=company_doc.default_currency,
			company=company_doc.name,
			cost_center="Main - _TC",
		)
		payroll_entry.submit()
		payroll_entry.submit_salary_slips()
		journal_entry = get_linked_journal_entries(payroll_entry.name, docstatus=1)

		self.assertTrue(journal_entry)

	@if_lending_app_installed
	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 0}
	)
	def test_loan_repayment_from_salary(self):
		self.run_test_for_loan_repayment_from_salary()

	@if_lending_app_installed
	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 1}
	)
	def test_loan_repayment_from_salary_with_employee_tagging(self):
		self.run_test_for_loan_repayment_from_salary()

	def run_test_for_loan_repayment_from_salary(self):
		from lending.loan_management.doctype.loan.test_loan import make_loan_disbursement_entry

		frappe.db.delete("Loan")
		applicant, branch, currency, payroll_payable_account = setup_lending()

		loan = create_loan_for_employee(applicant)
		loan_doc = frappe.get_doc("Loan", loan.name)
		loan_doc.repay_from_salary = 1
		loan_doc.save()

		dates = frappe._dict({"start_date": add_months(getdate(), -1), "end_date": getdate()})
		make_loan_disbursement_entry(
			loan.name,
			loan.loan_amount,
			disbursement_date=dates.start_date,
			repayment_start_date=dates.end_date,
		)

		payroll_entry = make_payroll_entry(
			company="_Test Company",
			start_date=dates.start_date,
			payable_account=payroll_payable_account,
			currency=currency,
			end_date=dates.end_date,
			branch=branch,
			cost_center="Main - _TC",
			payment_account="Cash - _TC",
		)

		salary_slip_name = frappe.db.get_value("Salary Slip", {"payroll_entry": payroll_entry.name}, "name")
		salary_slip = frappe.get_doc("Salary Slip", salary_slip_name)
		payroll_entry.reload()

		self.assertTrue(flt(salary_slip.total_loan_repayment) > 0)
		self.assertTrue(salary_slip.journal_entry)

		je = frappe.qb.DocType("Journal Entry")
		jea = frappe.qb.DocType("Journal Entry Account")
		bank_entry = (
			frappe.qb.from_(je)
			.inner_join(jea)
			.on(je.name == jea.parent)
			.select(je.total_debit, je.total_credit)
			.where((je.voucher_type == "Bank Entry") | (je.voucher_type == "Cash Entry"))
			.where(jea.reference_type == "Payroll Entry")
			.where(jea.reference_name == payroll_entry.name)
			.limit(1)
		).run(as_dict=True)

		self.assertTrue(bank_entry)
		self.assertEqual(bank_entry[0].get("total_debit"), bank_entry[0].get("total_credit"))
		self.assertNotIn(
			"_Test Payroll Payable - _TC",
			frappe.get_all(
				"Journal Entry Account",
				filters={"parent": salary_slip.journal_entry},
				pluck="account",
			),
		)

	@if_lending_app_installed
	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 0}
	)
	def test_loan_repayment_value_date_for_future_payroll(self):
		from lending.loan_management.doctype.loan.test_loan import make_loan_disbursement_entry
		from lending.tests.test_utils import create_loan

		frappe.db.delete("Loan")
		applicant, branch, currency, payroll_payable_account = setup_lending()

		today = getdate()
		payroll_start_date = get_first_day(today)
		payroll_end_date = get_last_day(today)
		loan_posting_date = get_first_day(add_months(today, -1))
		repayment_start_date = add_days(payroll_start_date, 4)

		loan = create_loan(
			applicant,
			"Car Loan",
			280000,
			"Repay Over Number of Periods",
			20,
			applicant_type="Employee",
			posting_date=loan_posting_date,
			repayment_start_date=repayment_start_date,
		)
		loan.repay_from_salary = 1
		loan.submit()

		make_loan_disbursement_entry(
			loan.name,
			loan.loan_amount,
			disbursement_date=loan_posting_date,
			repayment_start_date=repayment_start_date,
		)

		payroll_entry = make_payroll_entry(
			company="_Test Company",
			start_date=payroll_start_date,
			end_date=payroll_end_date,
			payable_account=payroll_payable_account,
			currency=currency,
			branch=branch,
			cost_center="Main - _TC",
			payment_account="Cash - _TC",
		)

		salary_slip_name = frappe.db.get_value(
			"Salary Slip", {"payroll_entry": payroll_entry.name, "employee": applicant}, "name"
		)
		loan_repayment_name = frappe.db.get_value(
			"Salary Slip Loan", {"parent": salary_slip_name}, "loan_repayment_entry"
		)

		lr_value_date, lr_interest_payable = frappe.db.get_value(
			"Loan Repayment", loan_repayment_name, ["value_date", "interest_payable"]
		)

		self.assertEqual(getdate(lr_value_date), payroll_end_date)
		self.assertGreater(flt(lr_interest_payable), 0)

	@HRMSTestSuite.change_settings(
		"Payroll Settings", {"process_payroll_accounting_entry_based_on_employee": 0}
	)
	def test_component_exclusion_from_accounting_entries(self):
		company = frappe.get_doc("Company", "_Test Company")
		employee = make_employee("exclude_component_test@payroll.com", company=company.name)

		# Create Salary Components
		basic = create_salary_component("Basic", **{"type": "Earning"})
		basic.append("accounts", {"company": company.name, "account": "Salary - _TC"})
		basic.save()

		esi = create_salary_component(
			"ESI", **{"type": "Deduction", "do_not_include_in_total": 1, "do_not_include_in_accounts": 1}
		)
		esi.append("accounts", {"company": company.name, "account": "Salary - _TC"})
		esi.save()

		# Create Salary structure with both components
		make_salary_structure(
			"Test Salary Structure",
			"Monthly",
			employee,
			company=company.name,
			other_details={
				"earnings": [{"salary_component": basic.name, "amount": 20000}],
				"deductions": [
					{
						"salary_component": esi.name,
						"amount": 200,
						"do_not_include_in_total": 1,
						"do_not_include_in_accounts": 1,
					}
				],
			},
		)

		# Create Payroll entry
		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = make_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company.default_payroll_payable_account,
			currency=company.default_currency,
			company=company.name,
			cost_center="Main - _TC",
		)

		# Get and verify salary slip & jv
		salary_slip = frappe.get_doc("Salary Slip", {"payroll_entry": payroll_entry.name})

		self.assertAlmostEqual(salary_slip.gross_pay, 20000.0, places=2)

		# Deductions table should include ESI
		self.assertTrue(any(row.salary_component == esi.name for row in salary_slip.deductions))

		# verify jv & accounts
		journal_entry = frappe.get_doc("Journal Entry", salary_slip.journal_entry)
		self.assertTrue(journal_entry, "Journal Entry not created")
		self.assertEqual(salary_slip.gross_pay, journal_entry.total_debit)

		accounts = [d.account for d in journal_entry.accounts]
		self.assertIn("Salary - _TC", accounts)
		self.assertIn("Cash - _TC", accounts)
		self.assertNotIn(company.default_payroll_payable_account, accounts)
		self.assertNotIn("ESIC Payable - _TC", accounts, "ESIC component wrongly included in JE")

	def test_employee_benefits_accruals_in_salary_slip(self):
		"""Test to verify
		- employee flexible benefits of accrual payout methods are fetched into salary slip
		- employee benefit ledger entries are created for each component
		- accrual earning components are excluded from earnings and added to accrued_benefts instead
		- additional salary for accrual component is included in totals and benefit ledger entries are created
		- unclaimed benefits and benefit type of "Accrue and Payout at end of Payroll Perod" are paid out in final month of payroll period
		"""
		from hrms.payroll.doctype.salary_slip.test_salary_slip import (
			create_salary_slips_for_payroll_period,
			make_payroll_period,
		)

		frappe.db.set_value("Company", "_Test Company", "default_holiday_list", "_Test Holiday List")

		make_payroll_period(company="_Test Company")
		emp = make_employee(
			"test_employee_benefits@salary.com",
			company="_Test Company",
			date_of_joining="2021-01-01",
		)
		payroll_period = frappe.get_last_doc("Payroll Period", filters={"company": "_Test Company"})

		make_salary_structure(
			"Test Benefit Accrual",
			"Monthly",
			company="_Test Company",
			employee=emp,
			payroll_period=payroll_period,
			base=65000,
			include_flexi_benefits=True,
			test_accrual_component=True,
			test_tax=True,
		)

		# Create and submit payroll entry for first month of payroll period
		first_month_start = payroll_period.start_date
		first_month_end = add_months(first_month_start, 1)
		company_doc = frappe.get_doc("Company", "_Test Company")

		payroll_entry = make_payroll_entry(
			start_date=first_month_start,
			end_date=first_month_end,
			payable_account=company_doc.default_payroll_payable_account,
			currency=company_doc.default_currency,
			company="_Test Company",
			cost_center="Main - _TC",
		)
		salary_slip = frappe.get_doc("Salary Slip", {"payroll_entry": payroll_entry.name})

		# Check if employee benefits have been fetched to accrued benefits table
		self.assertTrue(salary_slip.accrued_benefits)
		accrual_payout_methods = [
			"Accrue and payout at end of payroll period",
			"Accrue per cycle, pay only on claim",
		]
		for benefit in salary_slip.accrued_benefits:
			if benefit.salary_component != "Accrued Earnings":
				payout_method = frappe.db.get_value(
					"Salary Component", benefit.salary_component, "payout_method"
				)
				self.assertIn(payout_method, accrual_payout_methods)
			else:
				self.assertEqual(benefit.amount, 1000)

		# Check if employee benefit ledger entries have been created for each component
		for benefit_row in salary_slip.accrued_benefits:
			self.assertTrue(
				frappe.db.exists(
					"Employee Benefit Ledger",
					{"salary_slip": salary_slip.name, "salary_component": benefit_row.salary_component},
				)
			)

		earnings_list = [earning.salary_component for earning in salary_slip.earnings]
		self.assertNotIn(
			"Accrued Earnings", earnings_list
		)  # "Accrued Earnings component should not be in earnings table but in accrued benefits")

		# Check if Employee Benefit Ledger exists for Accrued Earnings Component
		self.assertTrue(
			frappe.db.exists(
				"Employee Benefit Ledger",
				{"salary_slip": salary_slip.name, "salary_component": "Accrued Earnings"},
			)
		)

		# Create additional salary for accrual component for second month of payroll period
		second_month_start = add_months(first_month_start, 1)
		second_month_end = add_months(first_month_start, 2)

		additional_salary = frappe.get_doc(
			{
				"doctype": "Additional Salary",
				"employee": emp,
				"salary_component": "Accrued Earnings",
				"amount": 1000,
				"payroll_date": second_month_end,
				"company": "_Test Company",
				"overwrite_salary_structure_amount": 0,
			}
		)
		additional_salary.insert()
		additional_salary.submit()

		next_month_payroll_entry = make_payroll_entry(
			start_date=second_month_start,
			end_date=second_month_end,
			payable_account=company_doc.default_payroll_payable_account,
			currency=company_doc.default_currency,
			company="_Test Company",
			cost_center="Main - _TC",
		)
		next_salary_slip = frappe.get_doc("Salary Slip", {"payroll_entry": next_month_payroll_entry.name})

		# Payout against accrual component as additional salary is recorded in Employee Benefit Ledger
		self.assertTrue(
			frappe.db.exists(
				"Employee Benefit Ledger",
				{
					"salary_slip": next_salary_slip.name,
					"salary_component": "Accrued Earnings",
					"transaction_type": "Payout",
				},
			)
		)

		frappe.db.delete("Salary Slip", {"employee": emp})
		frappe.db.delete("Employee Benefit Ledger")

		# check if unclaimed benefits and benefit type of "Accrue and Payout at end of Payroll Perod" are paid out in final month of payroll period
		create_salary_slips_for_payroll_period(emp, "Test Benefit Accrual", payroll_period)

		salary_slip = frappe.get_all(
			"Salary Slip", filters={"employee": emp}, order_by="posting_date desc", limit=1, pluck="name"
		)
		salary_slip = frappe.get_doc("Salary Slip", salary_slip[0])
		earnings_components = {earning.salary_component: earning.amount for earning in salary_slip.earnings}

		self.assertEqual(
			earnings_components.get("Internet Reimbursement"),
			12000,
		)
		self.assertEqual(
			earnings_components.get("Mediclaim Allowance"),
			24000,
		)

	def test_status_on_discard(self):
		company = frappe.get_doc("Company", "_Test Company")
		employee = frappe.db.get_value("Employee", {"company": "_Test Company"})
		setup_salary_structure(employee, company)

		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = get_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company.default_payroll_payable_account,
			currency=company.default_currency,
			company=company.name,
			cost_center="Main - _TC",
		)
		payroll_entry.discard()
		payroll_entry.reload()
		self.assertEqual(payroll_entry.status, "Cancelled")

	def test_bulk_cancel_then_delete_draft_payroll_entries(self):
		company = frappe.get_doc("Company", "_Test Company")
		employee = frappe.db.get_value("Employee", {"company": "_Test Company"})
		setup_salary_structure(employee, company)

		dates = get_start_end_dates("Monthly", nowdate())
		first = get_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company.default_payroll_payable_account,
			currency=company.default_currency,
			company=company.name,
			cost_center="Main - _TC",
		)
		second = get_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			payable_account=company.default_payroll_payable_account,
			currency=company.default_currency,
			company=company.name,
			cost_center="Main - _TC",
		)

		blocked = bulk_delete_payroll_entries([first.name])
		self.assertEqual(blocked.get("deleted"), [])
		self.assertTrue(blocked.get("errors"))
		self.assertTrue(frappe.db.exists("Payroll Entry", first.name))

		result = bulk_cancel_payroll_entries([first.name, second.name])
		self.assertEqual(sorted(result.get("cancelled") or []), sorted([first.name, second.name]))
		self.assertEqual(result.get("errors"), [])

		first.reload()
		second.reload()
		self.assertEqual(first.status, "Cancelled")
		self.assertEqual(second.status, "Cancelled")

		deleted = bulk_delete_payroll_entries([first.name, second.name])
		self.assertEqual(sorted(deleted.get("deleted") or []), sorted([first.name, second.name]))
		self.assertEqual(deleted.get("errors"), [])
		self.assertFalse(frappe.db.exists("Payroll Entry", first.name))
		self.assertFalse(frappe.db.exists("Payroll Entry", second.name))

	def test_fill_employees_by_customer_without_filters(self):
		"""Selecting a client pulls billed agents; branch/department filters are optional."""
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		from hrms.setup import get_custom_fields

		create_custom_fields(get_custom_fields(), ignore_validate=True)
		if not frappe.get_meta("Employee").has_field("bill_to_customer"):
			return
		if not frappe.get_meta("Payroll Entry").has_field("customer"):
			return

		company = frappe.get_doc("Company", "_Test Company")
		customer_a = _ensure_customer("_Test Payroll Client A")
		customer_b = _ensure_customer("_Test Payroll Client B")

		emp_a = make_employee("payroll.client.a@example.com", company=company.name)
		emp_b = make_employee("payroll.client.b@example.com", company=company.name)
		frappe.db.set_value("Employee", emp_a, "bill_to_customer", customer_a)
		frappe.db.set_value("Employee", emp_b, "bill_to_customer", customer_b)
		setup_salary_structure(emp_a, company)
		setup_salary_structure(emp_b, company)

		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = frappe.new_doc("Payroll Entry")
		payroll_entry.company = company.name
		payroll_entry.customer = customer_a
		payroll_entry.start_date = dates.start_date
		payroll_entry.end_date = dates.end_date
		payroll_entry.payroll_frequency = "Monthly"
		payroll_entry.currency = company.default_currency
		payroll_entry.exchange_rate = 1
		payroll_entry.fill_employee_details()

		employees = {row.employee for row in payroll_entry.employees}
		self.assertIn(emp_a, employees)
		self.assertNotIn(emp_b, employees)

		payroll_entry.fill_employee_details(raise_if_empty=0)
		self.assertIn(emp_a, {row.employee for row in payroll_entry.employees})

	def test_fill_employees_customer_is_unassigned(self):
		"""Calling fill_employee_details with `customer_is_unassigned` filters to agents without bill_to_customer."""
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		from hrms.setup import get_custom_fields

		create_custom_fields(get_custom_fields(), ignore_validate=True)
		if not frappe.get_meta("Employee").has_field("bill_to_customer"):
			return
		if not frappe.get_meta("Payroll Entry").has_field("customer"):
			return

		company = frappe.get_doc("Company", "_Test Company")
		customer_a = _ensure_customer("_Test Payroll Client A")

		emp_unassigned = make_employee("payroll.agent.unassigned@example.com", company=company.name)
		emp_a = make_employee("payroll.client.a@example.com", company=company.name)
		emp_b = make_employee("payroll.client.b@example.com", company=company.name)

		frappe.db.set_value("Employee", emp_unassigned, "bill_to_customer", None)
		frappe.db.set_value("Employee", emp_a, "bill_to_customer", customer_a)

		setup_salary_structure(emp_unassigned, company)
		setup_salary_structure(emp_a, company)
		setup_salary_structure(emp_b, company)

		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = frappe.new_doc("Payroll Entry")
		payroll_entry.company = company.name
		payroll_entry.start_date = dates.start_date
		payroll_entry.end_date = dates.end_date
		payroll_entry.payroll_frequency = "Monthly"
		payroll_entry.currency = company.default_currency
		payroll_entry.exchange_rate = 1

		# Ensure unassigned bucket contains only employees without bill_to_customer.
		payroll_entry.fill_employee_details(customer_is_unassigned=1)
		employees = {row.employee for row in payroll_entry.employees}
		self.assertIn(emp_unassigned, employees)
		self.assertNotIn(emp_a, employees)
		self.assertNotIn(emp_b, employees)

		# Default behavior (customer not set) includes all agents.
		payroll_entry.fill_employee_details(raise_if_empty=0)
		employees_all = {row.employee for row in payroll_entry.employees}
		self.assertIn(emp_unassigned, employees_all)
		self.assertIn(emp_a, employees_all)
		self.assertIn(emp_b, employees_all)

	def test_fill_employees_all_clients(self):
		"""Selecting All Clients includes agents from every client and unassigned agents."""
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		from hrms.setup import get_custom_fields

		create_custom_fields(get_custom_fields(), ignore_validate=True)
		if not frappe.get_meta("Employee").has_field("bill_to_customer"):
			return
		if not frappe.get_meta("Payroll Entry").has_field("customer"):
			return

		company = frappe.get_doc("Company", "_Test Company")
		customer_a = _ensure_customer("_Test Payroll Client A")
		customer_b = _ensure_customer("_Test Payroll Client B")

		emp_unassigned = make_employee("payroll.all.clients.unassigned@example.com", company=company.name)
		emp_a = make_employee("payroll.all.clients.a@example.com", company=company.name)
		emp_b = make_employee("payroll.all.clients.b@example.com", company=company.name)

		frappe.db.set_value("Employee", emp_unassigned, "bill_to_customer", None)
		frappe.db.set_value("Employee", emp_a, "bill_to_customer", customer_a)
		frappe.db.set_value("Employee", emp_b, "bill_to_customer", customer_b)

		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = frappe.new_doc("Payroll Entry")
		payroll_entry.company = company.name
		payroll_entry.customer = ALL_CLIENTS
		payroll_entry.start_date = dates.start_date
		payroll_entry.end_date = dates.end_date
		payroll_entry.payroll_frequency = "Monthly"
		payroll_entry.currency = company.default_currency
		payroll_entry.exchange_rate = 1
		payroll_entry.fill_employee_details()

		employees = {row.employee for row in payroll_entry.employees}
		self.assertIn(emp_unassigned, employees)
		self.assertIn(emp_a, employees)
		self.assertIn(emp_b, employees)

	def test_payroll_client_query_includes_all_clients(self):
		rows = payroll_client_query(
			doctype="Customer",
			txt="",
			searchfield="name",
			start="0",
			page_len="20",
			filters="{}",
		)
		self.assertTrue(rows)
		self.assertEqual(rows[0][0], ALL_CLIENTS)

	def test_all_clients_is_not_an_invalid_link(self):
		payroll_entry = frappe.new_doc("Payroll Entry")
		payroll_entry.customer = ALL_CLIENTS
		invalid_links, _cancelled = payroll_entry.get_invalid_links()
		self.assertFalse(
			any(
				(row[0] == "customer" if isinstance(row, (list, tuple)) else row.get("fieldname") == "customer")
				for row in (invalid_links or [])
			)
		)

	def test_fill_employees_by_customer_ignores_currency_and_dates(self):
		"""Client roster is independent of payroll currency, pay period, and salary structures."""
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		from hrms.setup import get_custom_fields

		create_custom_fields(get_custom_fields(), ignore_validate=True)
		if not frappe.get_meta("Employee").has_field("bill_to_customer"):
			return
		if not frappe.get_meta("Payroll Entry").has_field("customer"):
			return

		company = frappe.get_doc("Company", "_Test Company")
		customer = _ensure_customer("_Test Payroll Client Currency")
		employee = make_employee("payroll.client.currency@example.com", company=company.name)
		frappe.db.set_value("Employee", employee, "bill_to_customer", customer)

		payroll_entry = frappe.new_doc("Payroll Entry")
		payroll_entry.company = company.name
		payroll_entry.customer = customer
		payroll_entry.start_date = "2010-01-01"
		payroll_entry.end_date = "2010-01-14"
		payroll_entry.payroll_frequency = "Fortnightly"
		payroll_entry.currency = "USD" if company.default_currency != "USD" else "BZD"
		payroll_entry.exchange_rate = 1
		payroll_entry.fill_employee_details()

		self.assertIn(employee, {row.employee for row in payroll_entry.employees})

	def test_fill_employees_includes_agent_bank(self):
		company = frappe.get_doc("Company", "_Test Company")
		employee = make_employee("payroll.agent.bank@example.com", company=company.name)
		if frappe.get_meta("Employee").has_field("bank_name"):
			frappe.db.set_value("Employee", employee, {"bank_name": "Atlantic Bank", "bank_ac_no": "998877"})
		setup_salary_structure(employee, company)

		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = frappe.new_doc("Payroll Entry")
		payroll_entry.company = company.name
		payroll_entry.start_date = dates.start_date
		payroll_entry.end_date = dates.end_date
		payroll_entry.payroll_frequency = "Monthly"
		payroll_entry.currency = company.default_currency
		payroll_entry.exchange_rate = 1
		payroll_entry.fill_employee_details()

		row = next(r for r in payroll_entry.employees if r.employee == employee)
		if frappe.get_meta("Payroll Employee Detail").has_field("bank_name"):
			self.assertEqual(row.bank_name, "Atlantic Bank")
			self.assertEqual(row.bank_ac_no, "998877")

	def test_get_payroll_excel_data_columns_and_agent_row(self):
		from hrms.payroll.doctype.payroll_entry.payroll_entry import get_payroll_excel_data

		company = frappe.get_doc("Company", "_Test Company")
		employee = make_employee("payroll.excel.view@example.com", company=company.name)
		setup_salary_structure(employee, company)
		dates = get_start_end_dates("Monthly", nowdate())
		payroll_entry = get_payroll_entry(
			start_date=dates.start_date,
			end_date=dates.end_date,
			currency=company.default_currency,
			company=company.name,
			cost_center="Main - _TC",
		)
		payload = get_payroll_excel_data(payroll_entry.name)
		column_ids = [col["id"] for col in payload["columns"]]
		self.assertIn("last_name", column_ids)
		self.assertIn("first_name", column_ids)
		self.assertNotIn("employee_name", column_ids)
		self.assertIn("regular_hours", column_ids)
		self.assertIn("holiday_pay", column_ids)
		self.assertIn("pay_period_ee_social", column_ids)
		self.assertIn("net_pay", column_ids)
		self.assertTrue(any(row["employee"] == employee for row in payload["rows"]))
		agent_row = next(row for row in payload["rows"] if row["employee"] == employee)
		self.assertTrue(agent_row["first_name"] or agent_row["last_name"])

	def test_split_full_name_into_first_and_last(self):
		from hrms.payroll.doctype.payroll_entry.payroll_entry import _split_full_name

		self.assertEqual(_split_full_name("Ana Cruz"), ("Ana", "Cruz"))
		self.assertEqual(_split_full_name("Mary Ann Cruz"), ("Mary Ann", "Cruz"))
		self.assertEqual(_split_full_name("Ana"), ("Ana", ""))


def _ensure_customer(name: str) -> str:
	if frappe.db.exists("Customer", name):
		return name
	customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"
	territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
	frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": name,
			"customer_type": "Company",
			"customer_group": customer_group,
			"territory": territory,
		}
	).insert(ignore_permissions=True)
	return name


def get_payroll_entry(**args):
	args = frappe._dict(args)

	payroll_entry: PayrollEntry = frappe.new_doc("Payroll Entry")
	payroll_entry.company = args.company or "_Test Company"
	payroll_entry.customer = args.customer
	payroll_entry.start_date = args.start_date or "2016-11-01"
	payroll_entry.end_date = args.end_date or "2016-11-30"
	payroll_entry.payment_account = get_payment_account()
	payroll_entry.posting_date = nowdate()
	payroll_entry.payroll_frequency = "Monthly"
	payroll_entry.branch = args.branch or None
	payroll_entry.department = args.department or None
	payroll_entry.payroll_payable_account = args.payable_account
	payroll_entry.currency = args.currency
	payroll_entry.exchange_rate = args.exchange_rate or 1

	if args.cost_center:
		payroll_entry.cost_center = args.cost_center

	if args.payment_account:
		payroll_entry.payment_account = args.payment_account

	if args.bank_account:
		payroll_entry.bank_account = args.bank_account

	payroll_entry.fill_employee_details()
	payroll_entry.insert()

	return payroll_entry


def make_payroll_entry(**args):
	payroll_entry = get_payroll_entry(**args)
	payroll_entry.submit()
	payroll_entry.submit_salary_slips()
	# Payment Journal Entry (Bank/Cash) is created on slip submit; no separate bank entry.

	return payroll_entry


def get_payment_account():
	return frappe.get_value(
		"Account",
		{"account_type": "Cash", "company": "_Test Company" or "_Test Company", "is_group": 0},
		"name",
	)


def setup_salary_structure(employee, company_doc, currency=None, salary_structure=None):
	for data in frappe.get_all("Salary Component", pluck="name"):
		if not frappe.db.get_value(
			"Salary Component Account", {"parent": data, "company": company_doc.name}, "name"
		):
			set_salary_component_account(data)

	return make_salary_structure(
		salary_structure or "_Test Salary Structure",
		"Monthly",
		employee,
		company=company_doc.name,
		currency=(currency or company_doc.default_currency),
	)


def create_assignments_with_cost_centers(employee1, employee2):
	company = frappe.get_doc("Company", "_Test Company")
	setup_salary_structure(employee1, company)
	ss = setup_salary_structure(employee2, company, salary_structure="_Test Salary Structure 2")

	# update cost centers in salary structure assignment for employee2
	ssa = frappe.db.get_value(
		"Salary Structure Assignment",
		{"employee": employee2, "salary_structure": ss.name, "docstatus": 1},
		"name",
	)

	ssa_doc = frappe.get_doc("Salary Structure Assignment", ssa)
	ssa_doc.payroll_cost_centers = []
	ssa_doc.append("payroll_cost_centers", {"cost_center": "_Test Cost Center - _TC", "percentage": 60})
	ssa_doc.append("payroll_cost_centers", {"cost_center": "_Test Cost Center 2 - _TC", "percentage": 40})
	ssa_doc.save()


def setup_lending():
	from lending.loan_management.doctype.loan.test_loan import (
		create_loan_accounts,
		create_loan_product,
		set_loan_settings_in_company,
	)
	from lending.tests.test_utils import create_demand_offset_order

	create_demand_offset_order(
		"Test EMI Based Standard Loan Demand Offset Order",
		["EMI (Principal + Interest)", "Penalty", "Charges"],
	)

	company = "_Test Company"
	branch = "Test Employee Branch"

	if not frappe.db.exists("Branch", branch):
		frappe.get_doc({"doctype": "Branch", "branch": branch}).insert()

	set_loan_settings_in_company(company)
	applicant = make_employee("test_employee@loan.com", company="_Test Company", branch=branch)
	company_doc = frappe.get_doc("Company", company)

	make_salary_structure(
		"Test Salary Structure for Loan",
		"Monthly",
		employee=applicant,
		from_date=add_months(getdate(), -1),
		company="_Test Company",
		currency=company_doc.default_currency,
	)

	if not frappe.db.exists("Loan Product", "Car Loan"):
		create_loan_accounts()
		create_loan_product(
			"Car Loan",
			"Car Loan",
			500000,
			8.4,
			is_term_loan=1,
			disbursement_account="Disbursement Account - _TC",
			payment_account="Payment Account - _TC",
			loan_account="Loan Account - _TC",
			interest_income_account="Interest Income Account - _TC",
			penalty_income_account="Penalty Income Account - _TC",
			repayment_schedule_type="Monthly as per repayment start date",
			collection_offset_sequence_for_standard_asset="Test EMI Based Standard Loan Demand Offset Order",
			collection_offset_sequence_for_sub_standard_asset="Test EMI Based Standard Loan Demand Offset Order",
		)

	return (
		applicant,
		branch,
		company_doc.default_currency,
		company_doc.default_payroll_payable_account,
	)


def create_loan_for_employee(applicant):
	from lending.tests.test_utils import create_loan

	dates = frappe._dict({"start_date": add_months(getdate(), -1), "end_date": getdate()})

	loan = create_loan(
		applicant,
		"Car Loan",
		280000,
		"Repay Over Number of Periods",
		20,
		applicant_type="Employee",
		posting_date=dates.start_date,
		repayment_start_date=dates.end_date,
	)
	loan.repay_from_salary = 1
	loan.submit()

	return loan


def get_repayment_party_type(loan):
	loan_repayment = frappe.db.get_value(
		"Loan Repayment", {"against_loan": loan}, ["name", "payroll_payable_account"], as_dict=True
	)
	if not loan_repayment:
		return "", ""

	return frappe.db.get_value(
		"GL Entry",
		{
			"voucher_no": loan_repayment.name,
			"account": loan_repayment.payroll_payable_account,
			"is_cancelled": 0,
		},
		["party_type", "party"],
	) or ("", "")


def submit_bank_entry(payroll_entry_id):
	# submit the bank entry journal voucher
	jv = get_linked_journal_entries(payroll_entry_id, docstatus=0)[0].parent

	jv_doc = frappe.get_doc("Journal Entry", jv)
	jv_doc.cheque_no = "123456"
	jv_doc.cheque_date = nowdate()
	jv_doc.submit()


def get_linked_journal_entries(payroll_entry_id, docstatus=None):
	filters = {"reference_type": "Payroll Entry", "reference_name": payroll_entry_id}
	if docstatus is not None:
		filters["docstatus"] = docstatus

	return frappe.get_all(
		"Journal Entry Account",
		filters,
		"parent",
		distinct=True,
	)


def _ensure_bank_gl(company: str, account_name: str) -> str:
	existing = frappe.db.get_value(
		"Account", {"account_name": account_name, "company": company, "is_group": 0}, "name"
	)
	if existing:
		return existing

	parent = frappe.db.get_value(
		"Account",
		{"is_group": 1, "company": company, "root_type": "Asset", "account_type": "Bank"},
		"name",
	) or frappe.db.get_value(
		"Account", {"is_group": 1, "company": company, "root_type": "Asset"}, "name"
	)
	doc = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": account_name,
			"parent_account": parent,
			"company": company,
			"account_type": "Bank",
			"is_group": 0,
		}
	).insert(ignore_permissions=True)
	return doc.name


def _ensure_company_bank_account(company: str, bank_name: str, gl_account: str) -> str:
	if not frappe.db.exists("Bank", bank_name):
		frappe.get_doc({"doctype": "Bank", "bank_name": bank_name}).insert(ignore_permissions=True)

	existing = frappe.db.get_value(
		"Bank Account",
		{"company": company, "bank": bank_name, "is_company_account": 1},
		"name",
	)
	if existing:
		frappe.db.set_value("Bank Account", existing, "account", gl_account)
		return existing

	abbr = frappe.db.get_value("Company", company, "abbr") or company
	doc = {
		"doctype": "Bank Account",
		"account_name": f"{bank_name} - {abbr}",
		"bank": bank_name,
		"is_company_account": 1,
		"company": company,
		"account": gl_account,
	}
	meta = frappe.get_meta("Bank Account")
	if meta.has_field("account_type"):
		doc["account_type"] = "Bank"
	return frappe.get_doc(doc).insert(ignore_permissions=True).name
