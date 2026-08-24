# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.payroll.doctype.salary_slip.salary_slip import pay_agents


class TestPayAgents(FrappeTestCase):
	def test_pay_agents_requires_selection(self):
		self.assertRaises(frappe.ValidationError, pay_agents, [])
		self.assertRaises(frappe.ValidationError, pay_agents, None)

	def test_get_pay_preview_requires_selection(self):
		from hrms.payroll.doctype.salary_slip.salary_slip import get_pay_preview

		self.assertRaises(frappe.ValidationError, get_pay_preview, [])
		self.assertRaises(frappe.ValidationError, get_pay_preview, None)

	def test_pay_preview_query_includes_docstatus(self):
		from hrms.payroll.doctype.salary_slip.salary_slip import _salary_slip_query_fields

		self.assertIn("docstatus", _salary_slip_query_fields())
		self.assertIn("payment_status", _salary_slip_query_fields())
		self.assertIn("company", _salary_slip_query_fields())

	def test_can_pay_requires_submitted_unpaid(self):
		from hrms.payroll.doctype.salary_slip.salary_slip import _can_pay_salary_slip

		self.assertFalse(_can_pay_salary_slip(frappe._dict(docstatus=0, payment_status="Not Paid")))
		self.assertFalse(_can_pay_salary_slip(frappe._dict(docstatus=2, payment_status="Not Paid")))
		self.assertFalse(_can_pay_salary_slip(frappe._dict(docstatus=1, payment_status="Paid")))
		self.assertFalse(
			_can_pay_salary_slip(
				frappe._dict(docstatus=1, payment_status="Not Paid", salary_withholding="WH-1")
			)
		)
		self.assertTrue(_can_pay_salary_slip(frappe._dict(docstatus=1, payment_status="Not Paid")))

	def test_paid_from_label_uses_stored_bank(self):
		from hrms.payroll.doctype.salary_slip.salary_slip import _paid_from_label

		self.assertEqual(_paid_from_label(frappe._dict(paid_from_bank="Heritage Bank")), "Heritage Bank")

	def test_paid_from_falls_back_to_default_company_bank(self):
		from hrms.hr.belize_banks import bank_label_for_account, get_default_payroll_bank_account
		from hrms.payroll.doctype.salary_slip.salary_slip import _paid_from_account, _paid_from_label

		if not frappe.db.exists("Company", "_Test Company"):
			return
		default = get_default_payroll_bank_account("_Test Company")
		if not default:
			return
		row = frappe._dict(company="_Test Company")
		self.assertEqual(_paid_from_account(row), default)
		self.assertEqual(_paid_from_label(row), bank_label_for_account(default) or default)

	def test_payment_stamp_sets_date_and_time_when_paid(self):
		from hrms.payroll.doctype.salary_slip.salary_slip import get_payment_stamp

		if not frappe.get_meta("Salary Slip").has_field("payment_date"):
			return
		stamp = get_payment_stamp(True)
		self.assertTrue(stamp.get("payment_date"))
		self.assertTrue(stamp.get("payment_time"))
		kept = get_payment_stamp(True, keep_date="2026-07-31", keep_time="09:15:00")
		self.assertEqual(kept.get("payment_date"), "2026-07-31")
		self.assertEqual(kept.get("payment_time"), "09:15:00")

	def test_payment_stamp_clears_when_unpaid(self):
		from hrms.payroll.doctype.salary_slip.salary_slip import get_payment_stamp

		if not frappe.get_meta("Salary Slip").has_field("payment_date"):
			return
		stamp = get_payment_stamp(False)
		self.assertIsNone(stamp.get("payment_date"))
		self.assertIsNone(stamp.get("payment_time"))
