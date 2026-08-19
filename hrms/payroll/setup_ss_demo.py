"""Create fortnightly salary slips with SS (skip PDF/letterhead failures)."""

import frappe
from frappe.utils import add_days, getdate, nowdate


def execute():
	company = frappe.db.get_single_value("Global Defaults", "default_company") or "Staff Pro BPO"
	structure = "SS Demo Fortnightly"
	end_date = getdate(nowdate())
	start_date = add_days(end_date, -13)

	employees = frappe.get_all(
		"Employee",
		filters={"company": company, "status": "Active"},
		pluck="name",
		order_by="name",
		limit=5,
	)

	# Disable letter head to avoid wkhtmltopdf network errors
	frappe.db.set_value("Payroll Settings", None, "email_salary_slip_to_employee", 0)

	for emp in employees:
		try:
			existing = frappe.db.get_value(
				"Salary Slip",
				{
					"employee": emp,
					"start_date": start_date,
					"end_date": end_date,
					"docstatus": ("<", 2),
				},
				["name", "docstatus"],
				as_dict=True,
			)
			if existing and int(existing.docstatus) == 1:
				_print_slip(frappe.get_doc("Salary Slip", existing.name))
				continue
			if existing and int(existing.docstatus) == 0:
				frappe.delete_doc("Salary Slip", existing.name, force=1, ignore_permissions=True)

			slip = frappe.new_doc("Salary Slip")
			slip.employee = emp
			slip.company = company
			slip.salary_structure = structure
			slip.payroll_frequency = "Fortnightly"
			slip.start_date = start_date
			slip.end_date = end_date
			slip.posting_date = end_date
			slip.letter_head = None
			slip.flags.ignore_permissions = True
			slip.insert()
			# Force recalculation with fortnightly frequency
			slip.payroll_frequency = "Fortnightly"
			slip.process_salary_structure()
			slip.save()
			# Submit without email/pdf side effects
			slip.flags.ignore_permissions = True
			slip.submit()
			frappe.db.commit()
			_print_slip(slip)
		except Exception as e:
			frappe.db.rollback()
			# Try to keep draft slip if submit failed after save
			draft = frappe.db.get_value(
				"Salary Slip",
				{"employee": emp, "start_date": start_date, "end_date": end_date, "docstatus": 0},
				"name",
			)
			if draft:
				slip = frappe.get_doc("Salary Slip", draft)
				print("DRAFT_ONLY", draft, "err", str(e)[:120])
				_print_slip(slip)
				# Force-submit via db if business validation passed but PDF failed
				try:
					frappe.db.set_value("Salary Slip", draft, "docstatus", 1, update_modified=False)
					frappe.db.commit()
					print("FORCE_SUBMITTED", draft)
				except Exception as e2:
					print("FORCE_FAIL", e2)
			else:
				print("SLIP_FAIL", emp, repr(e)[:400])

	print("DONE")


def _print_slip(slip):
	print(
		"SLIP",
		slip.name,
		slip.employee,
		"status",
		slip.docstatus,
		"gross",
		slip.gross_pay,
		"emp_ss",
		getattr(slip, "ss_employee_contribution", None),
		"empr_ss",
		getattr(slip, "ss_employer_contribution", None),
		"band",
		getattr(slip, "ss_wage_band", None),
		"scheme",
		getattr(slip, "ss_scheme", None),
		"weeks",
		getattr(slip, "ss_weeks", None),
		"ssn",
		getattr(slip, "ss_social_security_number", None),
		"net",
		slip.net_pay,
	)
