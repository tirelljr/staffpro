import frappe


def execute():
	co = frappe.db.get_value(
		"Company",
		"Staff Pro BPO",
		["social_security_registration_no", "social_security_schedule"],
		as_dict=True,
	)
	print("Company:", co)
	emps = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "employee_name", "social_security_number"],
		order_by="name",
		limit=10,
	)
	for e in emps:
		print(e.name, e.employee_name, e.social_security_number)
	slips = frappe.get_all(
		"Salary Slip",
		filters={"docstatus": 1, "ss_scheme": ("is", "set")},
		fields=[
			"name",
			"employee",
			"ss_employee_contribution",
			"ss_employer_contribution",
			"ss_wage_band",
			"gross_pay",
			"net_pay",
		],
		limit=10,
	)
	print("SS Slips:", len(slips))
	for s in slips:
		print(
			s.name,
			s.employee,
			"gross",
			s.gross_pay,
			"SS",
			s.ss_employee_contribution,
			"+",
			s.ss_employer_contribution,
			s.ss_wage_band,
			"net",
			s.net_pay,
		)
	from hrms.payroll.report.social_security_contributions.social_security_contributions import (
		execute as run_report,
	)

	_cols, data = run_report({"company": "Staff Pro BPO"})
	print("Report rows:", len(data))
