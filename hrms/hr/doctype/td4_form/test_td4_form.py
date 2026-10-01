# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import today
from frappe.utils.user import add_role

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.document_category.document_category import seed_document_categories
from hrms.hr.doctype.td4_form.td4_form import (
	dismiss_td4_prompt,
	ensure_initial_td4,
	get_td4,
	get_td4_roster,
	request_td4,
	submit_td4,
)
from hrms.tests.utils import HRMSTestSuite

PDF_BYTES = b"%PDF-1.1\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
SIGNATURE = (
	"data:image/png;base64,"
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class TestTD4Form(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		seed_document_categories()
		self.employees = []
		self.previous_tin = None
		if frappe.get_meta("Company").has_field("tax_id"):
			self.previous_tin = frappe.db.get_value("Company", self.company, "tax_id")
			frappe.db.set_value("Company", self.company, "tax_id", "TD4-TEST-TIN", update_modified=False)

	def tearDown(self):
		frappe.set_user("Administrator")
		names = frappe.get_all("TD4 Form", filters={"employee": ["in", self.employees or [""]]}, pluck="name")
		if names:
			for name in frappe.get_all(
				"PWA Notification",
				filters={"reference_document_type": "TD4 Form", "reference_document_name": ["in", names]},
				pluck="name",
			):
				frappe.delete_doc("PWA Notification", name, ignore_permissions=True, force=True)
			for name in frappe.get_all(
				"Agent Document",
				filters={"notes": ["like", "Signed TD4 TD4-%"]},
				pluck="name",
			):
				if any(td4 in (frappe.db.get_value("Agent Document", name, "notes") or "") for td4 in names):
					frappe.delete_doc("Agent Document", name, ignore_permissions=True, force=True)
			for name in names:
				frappe.delete_doc("TD4 Form", name, ignore_permissions=True, force=True)
		if self.previous_tin is not None or frappe.get_meta("Company").has_field("tax_id"):
			frappe.db.set_value("Company", self.company, "tax_id", self.previous_tin, update_modified=False)

	def test_first_login_creates_one_open_form(self):
		agent = self._make_agent("td4.first@example.com")
		frappe.set_user(agent.user_id)
		first = ensure_initial_td4()
		second = ensure_initial_td4()
		self.assertEqual(first["name"], second["name"])
		self.assertEqual(frappe.db.get_value("TD4 Form", first["name"], "status"), "Requested")
		self.assertFalse(
			frappe.db.exists(
				"PWA Notification",
				{"reference_document_type": "TD4 Form", "reference_document_name": first["name"]},
			)
		)

	def test_prefill_locks_employer_and_employee_identity(self):
		agent = self._make_agent("td4.prefill@example.com", tin="TIN-44", ssn="001112223", address="12 Albert Street")
		frappe.set_user(agent.user_id)
		name = ensure_initial_td4()["name"]
		doc = get_td4(name)
		self.assertEqual(doc["employee_name"], agent.employee_name)
		self.assertEqual(doc["employee_address"], "12 Albert Street")
		self.assertEqual(doc["employee_tin"], "TIN-44")
		if frappe.get_meta("Employee").has_field("social_security_number"):
			self.assertEqual(doc["social_security"], "001112223")
		self.assertTrue(doc["employer_name"])
		if frappe.get_meta("Company").has_field("tax_id"):
			self.assertEqual(doc["employer_tin"], "TD4-TEST-TIN")

	def test_agent_cannot_open_another_agents_form(self):
		owner = self._make_agent("td4.owner@example.com")
		other = self._make_agent("td4.other@example.com")
		frappe.set_user(owner.user_id)
		name = ensure_initial_td4()["name"]
		frappe.set_user(other.user_id)
		self.assertRaises(frappe.PermissionError, get_td4, name)

	def test_submit_checks_income_total_and_weeks(self):
		agent = self._make_agent("td4.invalid@example.com", tin="TIN-1", ssn="00999", address="1 Main")
		frappe.set_user(agent.user_id)
		name = ensure_initial_td4()["name"]
		values = self._values(total_income=50, total_taxable_income=40, non_taxable_income=5, commissions=5)
		values["number_of_weeks"] = 60
		self._assert_error(lambda: submit_td4(name, values), "weeks")
		values["number_of_weeks"] = 10
		values["total_income"] = 10
		self._assert_error(lambda: submit_td4(name, values), "total income")

	@patch("hrms.hr.doctype.td4_form.td4_form.get_pdf", return_value=PDF_BYTES)
	def test_submit_signs_and_files_pdf(self, _pdf):
		agent = self._make_agent("td4.submit@example.com", tin="TIN-9", ssn="00888", address="4 Church Street")
		frappe.set_user(agent.user_id)
		name = ensure_initial_td4()["name"]
		submitted = submit_td4(name, self._values())
		self.assertEqual(submitted["status"], "Submitted")
		self.assertEqual(submitted["filled_by"], agent.user_id)
		self.assertTrue(submitted["filled_by_name"])
		self.assertTrue(submitted["filled_on"])
		self.assertTrue(submitted["signed_pdf"])
		self.assertIsNone(ensure_initial_td4()["name"])
		notes = f"Signed TD4 {name}"
		self.assertTrue(frappe.db.exists("Agent Document", {"employee": agent.name, "category": "Tax Forms", "notes": notes}))
		stored = frappe.db.get_value("Agent Document", {"notes": notes}, "file")
		self.assertTrue(stored)

		doc = frappe.get_doc("TD4 Form", name)
		doc.flags.ignore_permissions = True
		doc.total_income = 5
		self._assert_error(doc.save, "cannot be changed")

	def test_admin_request_notifies_and_does_not_duplicate(self):
		agent = self._make_agent("td4.request@example.com", tin="TIN-2", ssn="00777", address="9 Bay")
		frappe.set_user(agent.user_id)
		submit_td4_name = ensure_initial_td4()["name"]
		with patch("hrms.hr.doctype.td4_form.td4_form.get_pdf", return_value=PDF_BYTES):
			submit_td4(submit_td4_name, self._values())

		frappe.set_user("Administrator")
		created = request_td4(agent.name)
		self.assertTrue(created["created"])
		self.assertTrue(
			frappe.db.exists(
				"PWA Notification",
				{
					"reference_document_type": "TD4 Form",
					"reference_document_name": created["name"],
					"to_user": agent.user_id,
				},
			)
		)
		again = request_td4(agent.name)
		self.assertFalse(again["created"])
		self.assertEqual(again["name"], created["name"])

	def test_prompt_locks_after_three_closes(self):
		agent = self._make_agent("td4.dismiss@example.com", tin="TIN-3", ssn="00666", address="2 Oak")
		frappe.set_user(agent.user_id)
		state = ensure_initial_td4()
		self.assertFalse(state["locked"])
		for expected in (1, 2, 3):
			state = dismiss_td4_prompt(state["name"])
			self.assertEqual(state["dismiss_count"], expected)
			self.assertEqual(state["locked"], expected >= 3)
		again = dismiss_td4_prompt(state["name"])
		self.assertEqual(again["dismiss_count"], 3)
		self.assertTrue(ensure_initial_td4()["locked"])

	def test_roster_lists_filled_and_open_agents(self):
		open_agent = self._make_agent("td4.open@example.com", tin="TIN-4", ssn="00555", address="3 Pine")
		filled_agent = self._make_agent("td4.filled@example.com", tin="TIN-5", ssn="00444", address="5 Palm")
		frappe.set_user(open_agent.user_id)
		ensure_initial_td4()
		frappe.set_user(filled_agent.user_id)
		name = ensure_initial_td4()["name"]
		with patch("hrms.hr.doctype.td4_form.td4_form.get_pdf", return_value=PDF_BYTES):
			submit_td4(name, self._values(employee_tin="TIN-5", social_security="00444", employee_address="5 Palm"))
		frappe.set_user("Administrator")
		rows = {row["employee"]: row for row in get_td4_roster()}
		self.assertIn(open_agent.name, rows)
		self.assertIn(filled_agent.name, rows)
		self.assertFalse(rows[open_agent.name]["filled"])
		self.assertTrue(rows[filled_agent.name]["filled"])
		self.assertEqual(rows[filled_agent.name]["filled_by"], filled_agent.user_id)

	def test_new_account_opens_td4_without_notice(self):
		agent = self._make_agent("td4.account@example.com", tin="TIN-6", ssn="00333", address="6 Cedar")
		name = frappe.db.get_value("TD4 Form", {"employee": agent.name, "status": "Requested"}, "name")
		self.assertTrue(name)
		self.assertFalse(
			frappe.db.exists("PWA Notification", {"reference_document_type": "TD4 Form", "reference_document_name": name})
		)

	def _assert_error(self, fn, fragment):
		with self.assertRaises(frappe.ValidationError) as caught:
			fn()
		self.assertIn(fragment.lower(), str(caught.exception).lower())

	def _values(self, **overrides):
		values = {
			"reporting_year": 2026,
			"employee_address": "4 Church Street",
			"social_security": "00888",
			"employee_tin": "TIN-9",
			"number_of_weeks": 12,
			"total_income": 100,
			"total_taxable_income": 80,
			"non_taxable_income": 10,
			"commissions": 10,
			"tax_deducted": 5,
			"date_signed": today(),
			"signature": SIGNATURE,
		}
		values.update(overrides)
		return values

	def _make_agent(self, email, tin="TIN-0", ssn="000000000", address="1 Test Street"):
		employee_name = make_employee(email, company=self.company)
		employee = frappe.get_doc("Employee", employee_name)
		add_role(employee.user_id, "Employee")
		updates = {"pan_number": tin, "current_address": address}
		if frappe.get_meta("Employee").has_field("social_security_number"):
			updates["social_security_number"] = ssn
		frappe.db.set_value("Employee", employee.name, updates, update_modified=False)
		employee.reload()
		self.employees.append(employee.name)
		return employee
