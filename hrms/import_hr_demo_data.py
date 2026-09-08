"""Import HR portal demo data for Staff Pro BPO."""

import frappe
from frappe.utils import (
	add_days,
	add_months,
	cint,
	flt,
	get_first_day,
	get_first_day_of_week,
	get_last_day,
	getdate,
	nowdate,
)

DEMO_HOUR_RATE = 12.5
COMPANY = "Staff Pro BPO"

DEPARTMENTS = [
	"Human Resources",
	"Operations",
	"Customer Support",
	"Quality Assurance",
	"Training",
	"Finance",
	"IT",
]

DESIGNATIONS = [
	"HR Manager",
	"Operations Manager",
	"Team Lead",
	"Customer Service Representative",
	"Quality Analyst",
	"Trainer",
	"Accountant",
	"IT Support Specialist",
	"Supervisor",
]

EMPLOYEES = [
	{"first_name": "Maria", "last_name": "Santos", "email": "maria.santos@staffpro.local", "gender": "Female", "department": "Human Resources", "designation": "HR Manager", "date_of_birth": "1985-03-12", "date_of_joining": "2018-01-15", "reports_to": None},
	{"first_name": "James", "last_name": "Rivera", "email": "james.rivera@staffpro.local", "gender": "Male", "department": "Operations", "designation": "Operations Manager", "date_of_birth": "1988-08-22", "date_of_joining": "2019-06-03", "reports_to": "maria.santos@staffpro.local"},
	{"first_name": "Ana", "last_name": "Cruz", "email": "ana.cruz@staffpro.local", "gender": "Female", "department": "Customer Support", "designation": "Team Lead", "date_of_birth": "1992-11-04", "date_of_joining": "2021-08-21", "reports_to": "james.rivera@staffpro.local"},
	{"first_name": "Carlos", "last_name": "Mendoza", "email": "carlos.mendoza@staffpro.local", "gender": "Male", "department": "Customer Support", "designation": "Customer Service Representative", "date_of_birth": "1994-08-25", "date_of_joining": "2023-02-14", "reports_to": "ana.cruz@staffpro.local"},
	{"first_name": "Sofia", "last_name": "Reyes", "email": "sofia.reyes@staffpro.local", "gender": "Female", "department": "Customer Support", "designation": "Customer Service Representative", "date_of_birth": "1991-09-08", "date_of_joining": "2022-09-01", "reports_to": "ana.cruz@staffpro.local"},
	{"first_name": "Miguel", "last_name": "Torres", "email": "miguel.torres@staffpro.local", "gender": "Male", "department": "Customer Support", "designation": "Customer Service Representative", "date_of_birth": "1993-01-20", "date_of_joining": "2024-01-08", "reports_to": "ana.cruz@staffpro.local"},
	{"first_name": "Elena", "last_name": "Garcia", "email": "elena.garcia@staffpro.local", "gender": "Female", "department": "Quality Assurance", "designation": "Quality Analyst", "date_of_birth": "1989-05-17", "date_of_joining": "2020-05-11", "reports_to": "james.rivera@staffpro.local"},
	{"first_name": "Diego", "last_name": "Lopez", "email": "diego.lopez@staffpro.local", "gender": "Male", "department": "Training", "designation": "Trainer", "date_of_birth": "1987-12-03", "date_of_joining": "2019-12-02", "reports_to": "maria.santos@staffpro.local"},
	{"first_name": "Laura", "last_name": "Fernandez", "email": "laura.fernandez@staffpro.local", "gender": "Female", "department": "Finance", "designation": "Accountant", "date_of_birth": "1990-07-29", "date_of_joining": "2021-04-19", "reports_to": "maria.santos@staffpro.local"},
	{"first_name": "Pedro", "last_name": "Ramirez", "email": "pedro.ramirez@staffpro.local", "gender": "Male", "department": "IT", "designation": "IT Support Specialist", "date_of_birth": "1995-10-14", "date_of_joining": "2023-10-16", "reports_to": "james.rivera@staffpro.local"},
	{"first_name": "Isabella", "last_name": "Morales", "email": "isabella.morales@staffpro.local", "gender": "Female", "department": "Customer Support", "designation": "Customer Service Representative", "date_of_birth": "1996-08-20", "date_of_joining": "2024-08-20", "reports_to": "ana.cruz@staffpro.local"},
	{"first_name": "Luis", "last_name": "Herrera", "email": "luis.herrera@staffpro.local", "gender": "Male", "department": "Operations", "designation": "Supervisor", "date_of_birth": "1986-02-28", "date_of_joining": "2017-03-06", "reports_to": "james.rivera@staffpro.local"},
]

LEAVE_TYPES = ["Casual Leave", "Sick Leave", "Privilege Leave"]
JOB_OPENINGS = [
	{"job_title": "Customer Service Representative", "department": "Customer Support", "designation": "Customer Service Representative"},
	{"job_title": "Quality Analyst", "department": "Quality Assurance", "designation": "Quality Analyst"},
	{"job_title": "Team Lead - Operations", "department": "Operations", "designation": "Team Lead"},
]

JOB_APPLICANTS = [
	{"applicant_name": "Roberto Silva", "email": "roberto.silva@example.com", "status": "Open"},
	{"applicant_name": "Camila Vargas", "email": "camila.vargas@example.com", "status": "Replied"},
	{"applicant_name": "Fernando Castro", "email": "fernando.castro@example.com", "status": "Hold"},
]

SHIFT_NAME = "Day Shift"
SALARY_STRUCTURE = "Staff Pro Weekly"
BASIC_COMPONENT = "Basic Hourly"
LEAVE_OPEN_PAY_PERIODS = 1

HOUR_RATES = {
	"HR Manager": 24.0,
	"Operations Manager": 22.0,
	"Team Lead": 16.0,
	"Customer Service Representative": 12.5,
	"Quality Analyst": 15.0,
	"Trainer": 14.5,
	"Accountant": 17.0,
	"IT Support Specialist": 16.0,
	"Supervisor": 18.0,
}

BILLING_RATES = {
	"HR Manager": 36.0,
	"Operations Manager": 32.0,
	"Team Lead": 26.0,
	"Customer Service Representative": 22.0,
	"Quality Analyst": 24.0,
	"Trainer": 23.0,
	"Accountant": 28.0,
	"IT Support Specialist": 26.0,
	"Supervisor": 28.0,
}

CLIENTS = [
	{
		"customer_name": "Horizon Health",
		"service_type": "Inbound",
		"default_billing_rate": 22,
		"campaign_name": "Member Services",
		"contracted_seats": 8,
	},
	{
		"customer_name": "Pacific Telecom",
		"service_type": "Technical Support",
		"default_billing_rate": 28,
		"campaign_name": "Tech Support L1",
		"contracted_seats": 6,
	},
	{
		"customer_name": "Caribbean Collections",
		"service_type": "Collections",
		"default_billing_rate": 20,
		"campaign_name": "Card Recovery",
		"contracted_seats": 4,
	},
]

CLIENT_ASSIGNMENTS = {
	"maria.santos@staffpro.local": "Horizon Health",
	"james.rivera@staffpro.local": "Pacific Telecom",
	"ana.cruz@staffpro.local": "Horizon Health",
	"carlos.mendoza@staffpro.local": "Horizon Health",
	"sofia.reyes@staffpro.local": "Horizon Health",
	"miguel.torres@staffpro.local": "Pacific Telecom",
	"elena.garcia@staffpro.local": "Horizon Health",
	"diego.lopez@staffpro.local": "Pacific Telecom",
	"laura.fernandez@staffpro.local": "Caribbean Collections",
	"pedro.ramirez@staffpro.local": "Pacific Telecom",
	"isabella.morales@staffpro.local": "Caribbean Collections",
	"luis.herrera@staffpro.local": "Caribbean Collections",
}

# Paid-to bank on each demo employee (Belize banks + unique account numbers).
DEMO_BANK_ACCOUNTS = {
	"maria.santos@staffpro.local": {"bank": "Heritage Bank", "account_no": "1500284739", "account_type": "Checking"},
	"james.rivera@staffpro.local": {"bank": "Belize Bank", "account_no": "2201847562", "account_type": "Checking"},
	"ana.cruz@staffpro.local": {"bank": "Atlantic Bank", "account_no": "3109472158", "account_type": "Checking"},
	"carlos.mendoza@staffpro.local": {"bank": "National Bank of Belize", "account_no": "4001839462", "account_type": "Savings"},
	"sofia.reyes@staffpro.local": {"bank": "Heritage Bank", "account_no": "1501938472", "account_type": "Savings"},
	"miguel.torres@staffpro.local": {"bank": "Belize Bank", "account_no": "2203948571", "account_type": "Checking"},
	"elena.garcia@staffpro.local": {"bank": "Atlantic Bank", "account_no": "3102847561", "account_type": "Checking"},
	"diego.lopez@staffpro.local": {"bank": "National Bank of Belize", "account_no": "4009182736", "account_type": "Checking"},
	"laura.fernandez@staffpro.local": {"bank": "Heritage Bank", "account_no": "1508473629", "account_type": "Savings"},
	"pedro.ramirez@staffpro.local": {"bank": "Belize Bank", "account_no": "2205748193", "account_type": "Checking"},
	"isabella.morales@staffpro.local": {"bank": "Atlantic Bank", "account_no": "3106582947", "account_type": "Savings"},
	"luis.herrera@staffpro.local": {"bank": "National Bank of Belize", "account_no": "4003728194", "account_type": "Savings"},
}


def _ensure_demo_masters():
	"""Create HR master records needed before demo employees can be inserted."""
	for gender in ("Male", "Female"):
		if not frappe.db.exists("Gender", gender):
			frappe.get_doc({"doctype": "Gender", "gender": gender}).insert(ignore_permissions=True)
	for employment_type in ("Full-time", "Part-time"):
		if not frappe.db.exists("Employment Type", employment_type):
			frappe.get_doc(
				{"doctype": "Employment Type", "employee_type_name": employment_type}
			).insert(ignore_permissions=True)
	for leave_type in LEAVE_TYPES + ["Leave Without Pay"]:
		if not frappe.db.exists("Leave Type", leave_type):
			frappe.get_doc({"doctype": "Leave Type", "leave_type_name": leave_type}).insert(
				ignore_permissions=True
			)


def run(company=None):
	company = company or _get_company()
	if not company:
		print("No company found. Complete setup wizard first.")
		return

	print(f"Creating HR demo data for {company}...")
	frappe.flags.in_import = True

	try:
		_ensure_demo_masters()
		if not _has_hr_demo_data(company):
			departments = _create_departments(company)
			designations = _create_designations()
			holiday_list = _ensure_holiday_list(company)
			_create_leave_period(company)
			employee_map = _create_employees(company, departments, designations, holiday_list)
			seed_demo_profile_images()
			_create_leave_allocations(company, employee_map)
			_create_leave_applications(company, employee_map)
			_create_job_openings(company, departments, designations)
			_create_job_applicants(designations)
			_set_default_company(company)
		seed_connected_bpo_demo(company)
		frappe.db.commit()
		status(company)
		print(f"HR demo data import complete for {company}.")
	finally:
		frappe.flags.in_import = False


def clear(company=None):
	company = company or _get_company()
	frappe.only_for("System Manager")

	for doctype in (
		"Employee Checkin",
		"Attendance",
		"Leave Application",
		"Leave Allocation",
		"Job Applicant",
		"Job Opening",
		"Employee",
	):
		names = frappe.get_all(doctype, pluck="name")
		if frappe.get_meta(doctype).has_field("company"):
			names = frappe.get_all(doctype, filters={"company": company}, pluck="name")
		for name in names:
			if doctype == "Employee" and frappe.db.get_value("Employee", name, "company_email") not in {
				e["email"] for e in EMPLOYEES
			}:
				continue
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)

	for email in [e["email"] for e in EMPLOYEES]:
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)

	frappe.db.commit()
	print(f"Cleared HR demo data for {company}.")


PAYROLL_RUN_DOCTYPES = (
	"Client Invoice",
	"Salary Slip",
	"Additional Salary",
	"Overtime Slip",
	"Payroll Correction",
	"Arrear",
	"Employee Incentive",
	"Retention Bonus",
	"Salary Withholding",
	"Payroll Entry",
)


def clear_payroll(company=None):
	"""Remove payroll run documents so a fresh payroll can be tested."""
	company = company or _get_company()
	frappe.only_for("System Manager")

	deleted = {}
	for doctype in PAYROLL_RUN_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		filters = {"company": company} if frappe.get_meta(doctype).has_field("company") else {}
		names = frappe.get_all(doctype, filters=filters, pluck="name")
		count = 0
		for name in names:
			_force_delete_doc(doctype, name)
			count += 1
		deleted[doctype] = count

	_clear_payroll_accounting(company)
	_reset_payroll_series()
	if not frappe.flags.in_test:
		frappe.db.commit()
	print(f"Cleared demo payroll data for {company}: {deleted}")
	status(company)


def _force_delete_doc(doctype, name):
	try:
		doc = frappe.get_doc(doctype, name)
		if cint(doc.docstatus) == 1:
			doc.flags.ignore_permissions = True
			doc.flags.ignore_links = True
			try:
				doc.cancel()
			except Exception:
				frappe.db.set_value(doctype, name, "docstatus", 2, update_modified=False)
		frappe.delete_doc(
			doctype,
			name,
			force=True,
			ignore_permissions=True,
			ignore_on_trash=True,
			delete_permanently=True,
		)
	except Exception:
		frappe.db.delete(doctype, {"name": name})


def _clear_payroll_accounting(company):
	if frappe.db.exists("DocType", "Journal Entry"):
		for name in frappe.get_all(
			"Journal Entry",
			filters={"company": company, "voucher_type": "Journal Entry", "user_remark": ("like", "%Salary%")},
			pluck="name",
		):
			_force_delete_doc("Journal Entry", name)
		for name in frappe.get_all(
			"Journal Entry",
			or_filters={"cheque_no": ("like", "HR-PRUN%"), "bill_no": ("like", "Sal Slip%")},
			pluck="name",
		):
			_force_delete_doc("Journal Entry", name)
	if frappe.db.exists("DocType", "GL Entry"):
		frappe.db.delete("GL Entry", {"voucher_type": "Salary Slip", "company": company})
		frappe.db.delete("GL Entry", {"voucher_type": "Payroll Entry", "company": company})


def _reset_payroll_series():
	year = getdate().year
	frappe.db.sql(
		"update `tabSeries` set current=0 where name in (%s, %s)",
		(f"HR-PRUN-{year}-", f"CI-{year}-"),
	)


def status(company=None):
	company = company or _get_company()
	for doctype in (
		"Department",
		"Employee",
		"Leave Allocation",
		"Leave Application",
		"Attendance",
		"Employee Checkin",
		"Salary Structure",
		"Salary Structure Assignment",
		"Salary Slip",
		"Payroll Entry",
		"Customer",
		"Client Invoice",
		"Job Opening",
		"Job Applicant",
	):
		if not frappe.db.exists("DocType", doctype):
			continue
		if frappe.get_meta(doctype).has_field("company"):
			count = frappe.db.count(doctype, {"company": company})
		else:
			count = frappe.db.count(doctype)
		print(f"{doctype}: {count}")
	_print_connected_status(company)


def _print_connected_status(company):
	from frappe.utils import get_first_day

	today = getdate()
	week_start = get_first_day_of_week(today)
	month_start = get_first_day(today)
	present_today = frappe.db.count(
		"Attendance",
		{"company": company, "docstatus": 1, "status": ["in", ["Present", "Half Day", "Work From Home"]], "attendance_date": today},
	)
	hours = frappe.db.sql(
		"""
		select coalesce(sum(working_hours), 0) from `tabAttendance`
		where company=%s and docstatus=1 and attendance_date between %s and %s
		and status in ('Present','Half Day','Work From Home')
		""",
		(company, week_start, today),
	)[0][0]
	ss_slips = frappe.db.count(
		"Salary Slip",
		{"company": company, "docstatus": 1, "ss_category": ["!=", ""]},
	)
	invoices = frappe.db.count("Client Invoice", {"company": company, "docstatus": 1}) if frappe.db.exists("DocType", "Client Invoice") else 0
	print(f"Agents present today: {present_today}")
	print(f"Hours this week: {hours}")
	print(f"Submitted SS slips: {ss_slips}")
	print(f"Submitted client invoices: {invoices}")
	for entry in frappe.get_all(
		"Payroll Entry",
		filters={"company": company},
		fields=["name", "start_date", "end_date", "docstatus", "payroll_frequency"],
		order_by="end_date desc",
		limit=5,
	):
		print(f"Payroll Entry {entry.name}: {entry.start_date} to {entry.end_date} status={entry.docstatus}")
	slip = frappe.get_all(
		"Salary Slip",
		filters={"company": company, "docstatus": 1},
		fields=["name", "employee_name", "start_date", "end_date", "ss_category", "ss_employee_amount", "gross_pay"],
		order_by="end_date desc",
		limit=3,
	)
	for row in slip:
		print(
			f"Slip {row.name} {row.employee_name} {row.start_date}–{row.end_date} "
			f"gross={row.gross_pay} SS={row.ss_employee_amount} {row.ss_category}"
		)


def _get_company():
	if frappe.db.exists("Company", COMPANY):
		return COMPANY
	return (
		frappe.db.get_single_value("Global Defaults", "default_company")
		or (frappe.get_all("Company", pluck="name", filters={"company_name": ("not like", "%(Demo)%")}, limit=1) or [None])[0]
	)


def _has_hr_demo_data(company):
	return frappe.db.exists("Employee", {"company": company, "company_email": EMPLOYEES[0]["email"]})


def _create_departments(company):
	departments = {}
	for name in DEPARTMENTS:
		dept_name = f"{name} - {frappe.db.get_value('Company', company, 'abbr')}"
		if not frappe.db.exists("Department", dept_name):
			frappe.get_doc({"doctype": "Department", "department_name": name, "company": company}).insert(
				ignore_permissions=True
			)
		departments[name] = dept_name
	return departments


def _create_designations():
	designations = {}
	for name in DESIGNATIONS:
		if not frappe.db.exists("Designation", name):
			frappe.get_doc({"doctype": "Designation", "designation_name": name}).insert(ignore_permissions=True)
		designations[name] = name
	return designations


def _ensure_holiday_list(company):
	from hrms.hr.staff_pro_holiday_list import DEFAULT_HOLIDAY_LIST, ensure_staff_pro_holiday_list

	return ensure_staff_pro_holiday_list(company) or DEFAULT_HOLIDAY_LIST


def _create_leave_period(company):
	today = getdate()
	from_date = get_first_day(today.replace(month=1, day=1))
	to_date = get_last_day(today.replace(month=12, day=31))

	if frappe.db.exists("Leave Period", {"company": company, "from_date": from_date}):
		return

	frappe.get_doc(
		{
			"doctype": "Leave Period",
			"company": company,
			"from_date": from_date,
			"to_date": to_date,
			"is_active": 1,
		}
	).insert(ignore_permissions=True)


def _demo_avatar_url(emp):
	slug = f"{emp['first_name']}-{emp['last_name']}".lower()
	return f"/assets/hrms/images/demo/{slug}.jpg"


def seed_demo_profile_images():
	"""Attach bundled headshots to demo employees and their login users."""
	for emp in EMPLOYEES:
		image = _demo_avatar_url(emp)
		employee_name = frappe.db.get_value("Employee", {"company_email": emp["email"]})
		if employee_name:
			frappe.db.set_value("Employee", employee_name, "image", image, update_modified=False)
		if frappe.db.exists("User", emp["email"]):
			frappe.db.set_value(
				"User",
				emp["email"],
				{"user_image": image, "last_name": emp["last_name"]},
				update_modified=False,
			)
	frappe.clear_cache()
	if not frappe.flags.in_import:
		frappe.db.commit()


def _ensure_user(email, first_name, last_name=None, image=None):
	if frappe.db.exists("User", email):
		values = {}
		if last_name:
			values["last_name"] = last_name
		if image:
			values["user_image"] = image
		if values:
			frappe.db.set_value("User", email, values, update_modified=False)
		return email

	frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"user_image": image,
			"new_password": "StaffPro@2026!Demo",
			"send_welcome_email": 0,
			"roles": [{"doctype": "Has Role", "role": "Employee"}],
		}
	).insert(ignore_permissions=True)
	return email


def seed_demo_employee_dates():
	"""Write each demo employee's real date of birth and date of joining."""
	updated = 0
	for emp in EMPLOYEES:
		employee_name = frappe.db.get_value("Employee", {"company_email": emp["email"]})
		if not employee_name:
			continue
		values = {
			"date_of_birth": emp["date_of_birth"],
			"date_of_joining": emp["date_of_joining"],
		}
		current = frappe.db.get_value("Employee", employee_name, ["date_of_birth", "date_of_joining"], as_dict=True) or {}
		same_birth = current.get("date_of_birth") and getdate(current.date_of_birth) == getdate(values["date_of_birth"])
		same_join = current.get("date_of_joining") and getdate(current.date_of_joining) == getdate(
			values["date_of_joining"]
		)
		if same_birth and same_join:
			continue
		frappe.db.set_value("Employee", employee_name, values, update_modified=False)
		updated += 1
	if updated and not frappe.flags.in_import:
		frappe.db.commit()
	return updated


def seed_demo_employee_banks(company=None, employee_map=None):
	"""Give each demo employee a Belize bank and unique account number."""
	from hrms.hr.belize_banks import ensure_belize_banks

	company = company or _get_company()
	if not company:
		return 0

	ensure_belize_banks()
	employee_map = employee_map or _demo_employee_map(company)
	if not employee_map:
		return 0

	updated = _apply_employee_bank_fields(employee_map)
	_backfill_demo_payroll_banks(employee_map)
	if updated and not frappe.flags.in_import and not frappe.flags.in_test:
		frappe.db.commit()
	return updated


def _apply_employee_bank_fields(employee_map):
	if not frappe.db.exists("DocType", "Employee"):
		return 0

	meta = frappe.get_meta("Employee")
	updated = 0
	for email, employee in employee_map.items():
		bank = DEMO_BANK_ACCOUNTS.get(email)
		if not bank:
			continue
		values = {}
		if meta.has_field("salary_mode"):
			values["salary_mode"] = "Bank"
		if meta.has_field("bank_name"):
			values["bank_name"] = bank["bank"]
		if meta.has_field("bank_ac_no"):
			values["bank_ac_no"] = bank["account_no"]
		if meta.has_field("bank_account_type"):
			values["bank_account_type"] = bank.get("account_type") or "Checking"
		if not values:
			continue
		frappe.db.set_value("Employee", employee, values, update_modified=False)
		updated += 1
	return updated


def _backfill_demo_payroll_banks(employee_map):
	slip_meta = frappe.get_meta("Salary Slip") if frappe.db.exists("DocType", "Salary Slip") else None
	detail_meta = (
		frappe.get_meta("Payroll Employee Detail")
		if frappe.db.exists("DocType", "Payroll Employee Detail")
		else None
	)
	for email, employee in employee_map.items():
		bank = DEMO_BANK_ACCOUNTS.get(email)
		if not bank:
			continue
		if slip_meta:
			slip_values = {}
			if slip_meta.has_field("bank_name"):
				slip_values["bank_name"] = bank["bank"]
			if slip_meta.has_field("bank_account_no"):
				slip_values["bank_account_no"] = bank["account_no"]
			if slip_values:
				for name in frappe.get_all("Salary Slip", filters={"employee": employee}, pluck="name"):
					frappe.db.set_value("Salary Slip", name, slip_values, update_modified=False)
		if detail_meta:
			detail_values = {}
			if detail_meta.has_field("bank_name"):
				detail_values["bank_name"] = bank["bank"]
			if detail_meta.has_field("bank_ac_no"):
				detail_values["bank_ac_no"] = bank["account_no"]
			if detail_values:
				for name in frappe.get_all(
					"Payroll Employee Detail", filters={"employee": employee}, pluck="name"
				):
					frappe.db.set_value("Payroll Employee Detail", name, detail_values, update_modified=False)


def _create_employees(company, departments, designations, holiday_list):
	employee_map = {}

	for idx, emp in enumerate(EMPLOYEES, start=1):
		if frappe.db.exists("Employee", {"company_email": emp["email"]}):
			employee_map[emp["email"]] = frappe.db.get_value("Employee", {"company_email": emp["email"]})
			continue

		user_id = _ensure_user(emp["email"], emp["first_name"], emp["last_name"])
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"naming_series": "EMP-",
				"employee_number": emp.get("employee_number") or f"EMP-{idx:05d}",
				"first_name": emp["first_name"],
				"last_name": emp["last_name"],
				"company": company,
				"user_id": user_id,
				"date_of_birth": emp["date_of_birth"],
				"date_of_joining": emp["date_of_joining"],
				"department": departments[emp["department"]],
				"designation": designations[emp["designation"]],
				"gender": emp["gender"],
				"company_email": emp["email"],
				"prefered_contact_email": "Company Email",
				"prefered_email": emp["email"],
				"status": "Active",
				"employment_type": "Full-time",
				"holiday_list": holiday_list,
				"cell_number": f"+63 917{abs(hash(emp['email'])) % 10000000:07d}",
			}
		).insert(ignore_permissions=True)
		employee_map[emp["email"]] = employee.name

	for emp in EMPLOYEES:
		if emp["reports_to"]:
			frappe.db.set_value(
				"Employee",
				employee_map[emp["email"]],
				"reports_to",
				employee_map[emp["reports_to"]],
			)

	seed_demo_employee_dates()
	_apply_employee_bpo_fields(company, employee_map)
	seed_demo_employee_banks(company, employee_map)
	return employee_map


def _create_leave_allocations(company, employee_map):
	today = getdate()
	from_date = get_first_day(today.replace(month=1, day=1))
	to_date = get_last_day(today.replace(month=12, day=31))

	for employee in employee_map.values():
		for leave_type in LEAVE_TYPES:
			if frappe.db.exists(
				"Leave Allocation",
				{"employee": employee, "leave_type": leave_type, "from_date": from_date},
			):
				continue

			allocation = frappe.get_doc(
				{
					"doctype": "Leave Allocation",
					"employee": employee,
					"leave_type": leave_type,
					"from_date": from_date,
					"to_date": to_date,
					"new_leaves_allocated": 12 if leave_type != "Sick Leave" else 6,
					"company": company,
				}
			)
			allocation.insert(ignore_permissions=True)
			allocation.submit()


def _create_leave_applications(company, employee_map):
	emails = list(employee_map.keys())
	approver_user = frappe.db.get_value("Employee", employee_map[emails[0]], "user_id")

	leave_requests = [
		(emails[3], "Casual Leave", -14, -12, "Family event"),
		(emails[4], "Sick Leave", -7, -6, "Medical appointment"),
		(emails[5], "Casual Leave", 5, 6, "Personal day"),
	]

	for email, leave_type, from_offset, to_offset, description in leave_requests:
		from_date = add_days(nowdate(), from_offset)
		to_date = add_days(nowdate(), to_offset)

		app = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee_map[email],
				"leave_type": leave_type,
				"from_date": from_date,
				"to_date": to_date,
				"posting_date": nowdate(),
				"company": company,
				"description": description,
				"leave_approver": approver_user,
				"status": "Approved" if from_offset < 0 else "Open",
			}
		)
		app.insert(ignore_permissions=True)
		if from_offset < 0:
			app.submit()


def _create_attendance(employee_map):
	seed_week_hours(employees=list(employee_map.values()))


def seed_week_hours(company=None, week_start=None, employees=None):
	"""Create a Mon–Fri week of IN / lunch / OUT punches so Hours, pay, and SS can be demoed."""
	from frappe.utils import get_first_day_of_week

	from hrms.payroll.daily_pay import allocate_week_deductions
	from hrms.payroll.social_security import seed_belize_ssb_2022_table

	company = company or _get_company()
	if not company:
		print("No company found. Cannot seed hours.")
		return {"created": 0, "skipped": 0}

	seed_belize_ssb_2022_table()
	week_start = getdate(week_start or get_first_day_of_week(nowdate()))
	# Walk the calendar week and keep Mon–Fri so Hours has a full work week.
	days = [add_days(week_start, offset) for offset in range(7)]
	employee_ids = employees or _demo_employee_ids(company)
	if not employee_ids:
		print("No employees found. Cannot seed hours.")
		return {"created": 0, "skipped": 0}

	created = 0
	skipped = 0
	for index, employee in enumerate(employee_ids):
		for day in days:
			if getdate(day).weekday() >= 5:
				continue
			punches = _demo_punches_for(index, day)
			if _seed_day_hours(employee, day, punches):
				created += 1
			else:
				skipped += 1
		allocate_week_deductions(employee, week_start)

	refreshed = _refresh_today_demo_clocks(employee_ids)
	_backfill_attendance_pay(company, week_start, days[-1])
	submitted = _submit_open_attendance(company, week_start, days[-1])
	backfill_salary_slip_ss(company)
	if not frappe.flags.in_test:
		frappe.db.commit()
	print(f"Seeded demo hours: {created} days created, {skipped} skipped.")
	return {
		"created": created,
		"skipped": skipped,
		"refreshed_today": refreshed,
		"submitted": submitted,
		"week_start": str(week_start),
		"employees": employee_ids,
	}


def _demo_employee_ids(company):
	ids = []
	for emp in EMPLOYEES:
		name = frappe.db.get_value("Employee", {"company_email": emp["email"], "company": company})
		if name:
			ids.append(name)
	if ids:
		return ids
	return frappe.get_all(
		"Employee",
		filters={"company": company, "status": "Active"},
		pluck="name",
		order_by="name",
		limit=8,
	)


def _demo_punches_for(employee_index: int, day) -> list[tuple[str, str]]:
	"""Standard 8h with lunch; mix start times so Who Is In reflects a live floor."""
	weekday = getdate(day).weekday()
	if employee_index == 1 and weekday == 2:
		# James on Wednesday: 8–12, 1–6 (10h with lunch)
		return [("08:00:00", "IN"), ("12:00:00", "OUT"), ("13:00:00", "IN"), ("18:00:00", "OUT")]
	if employee_index == 3 and weekday == 4:
		# Carlos on Friday: single 9–5 block, no lunch row
		return [("09:00:00", "IN"), ("17:00:00", "OUT")]
	if employee_index == 4:
		# Sofia: late start
		return [("09:22:00", "IN"), ("12:30:00", "OUT"), ("13:00:00", "IN"), ("17:00:00", "OUT")]
	if employee_index == 5:
		# Miguel: later shift
		return [("10:00:00", "IN"), ("13:00:00", "OUT"), ("13:45:00", "IN"), ("18:00:00", "OUT")]
	if employee_index == 7:
		# Diego: early in, longer lunch
		return [("08:15:00", "IN"), ("12:00:00", "OUT"), ("13:30:00", "IN"), ("17:00:00", "OUT")]
	if employee_index == 10:
		# Isabella: no lunch break
		return [("08:45:00", "IN"), ("17:15:00", "OUT")]
	if employee_index == 2 and weekday == 3:
		# Ana on Thursday: early exit
		return [("09:00:00", "IN"), ("12:00:00", "OUT"), ("13:00:00", "IN"), ("15:40:00", "OUT")]
	if employee_index == 9 and weekday == 1:
		# Pedro on Tuesday: early exit
		return [("09:00:00", "IN"), ("12:00:00", "OUT"), ("13:00:00", "IN"), ("16:05:00", "OUT")]
	return [("09:00:00", "IN"), ("12:00:00", "OUT"), ("13:00:00", "IN"), ("17:00:00", "OUT")]


def _refresh_today_demo_clocks(employee_ids) -> int:
	"""Rebuild today's demo-device punches so Who Is In matches the current clock."""
	today = getdate()
	if today.weekday() >= 5:
		return 0
	refreshed = 0
	for index, employee in enumerate(employee_ids):
		punches = _punches_until_now(_demo_punches_for(index, today))
		if _replace_day_demo_punches(employee, today, punches) or _seed_day_hours(employee, today, punches):
			refreshed += 1
	return refreshed


def _replace_day_demo_punches(employee: str, day, punches: list[tuple[str, str]]) -> bool:
	from datetime import datetime

	from frappe.utils import get_time

	from hrms.payroll.daily_pay import resync_attendance_from_day_logs

	day = getdate(day)
	start = f"{day} 00:00:00"
	end = f"{day} 23:59:59"
	logs = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": ["between", [start, end]]},
		fields=["name", "device_id"],
	)
	if not logs or any((row.device_id or "") != "demo-device" for row in logs):
		return False

	existing = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": day, "docstatus": ("<", 2)},
		["name", "status"],
		as_dict=True,
	)
	if existing and existing.status == "On Leave":
		return False

	for row in logs:
		frappe.delete_doc("Employee Checkin", row.name, force=True, ignore_permissions=True)

	for clock, log_type in punches:
		when = datetime.combine(day, get_time(clock))
		log = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"time": when,
				"log_type": log_type,
				"device_id": "demo-device",
				"skip_auto_attendance": 1,
			}
		)
		log.flags.ignore_geolocation = True
		log.insert(ignore_permissions=True)

	resync_attendance_from_day_logs(employee, day, attendance_name=existing.name if existing else None)
	attendance_name = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": day, "docstatus": ("<", 2)},
	)
	if attendance_name:
		_stamp_missing_attendance_pay(attendance_name)
	return True


def _seed_day_hours(employee: str, day, punches: list[tuple[str, str]]) -> bool:
	from datetime import datetime

	from frappe.utils import get_time

	from hrms.payroll.daily_pay import resync_attendance_from_day_logs

	day = getdate(day)
	existing = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": day, "docstatus": ("<", 2)},
		["name", "status", "working_hours", "docstatus"],
		as_dict=True,
	)
	if existing and existing.status == "On Leave":
		return False
	if existing and cint(existing.get("docstatus")) == 1 and existing.status != "Absent" and flt(existing.get("working_hours")) >= 1:
		return False

	already = frappe.db.count(
		"Employee Checkin",
		{"employee": employee, "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
	)
	if already or (existing and flt(existing.working_hours)):
		return False

	for clock, log_type in punches:
		when = datetime.combine(day, get_time(clock))
		log = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"time": when,
				"log_type": log_type,
				"device_id": "demo-device",
				"skip_auto_attendance": 1,
			}
		)
		log.flags.ignore_geolocation = True
		log.insert(ignore_permissions=True)

	resync_attendance_from_day_logs(employee, day, attendance_name=existing.name if existing else None)
	attendance_name = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": day, "docstatus": ("<", 2)},
	)
	if attendance_name:
		_stamp_missing_attendance_pay(attendance_name)
	return True


def _stamp_missing_attendance_pay(attendance_name: str) -> None:
	"""Write hour rate and daily pay when a clock day was stored without payroll fields."""
	from hrms.payroll.daily_pay import (
		apply_daily_pay_to_doc,
		attendance_has_payroll_fields,
		get_hour_rate,
	)

	if not attendance_name or not attendance_has_payroll_fields():
		return
	doc = frappe.get_doc("Attendance", attendance_name)
	if not flt(doc.working_hours) and (doc.status or "") == "Absent":
		return
	rate = flt(doc.hour_rate) or get_hour_rate(doc.employee, doc.attendance_date) or DEMO_HOUR_RATE
	if not rate:
		return
	cache = frappe.flags.setdefault("hour_rate_cache", {})
	cache[(doc.employee, str(getdate(doc.attendance_date)))] = flt(rate, 6)
	apply_daily_pay_to_doc(doc)
	if not flt(doc.net_daily_pay) and flt(doc.daily_pay):
		doc.net_daily_pay = flt(
			flt(doc.daily_pay) - flt(doc.ss_deduction) - flt(doc.tax_deduction), 2
		)
	values = {
		key: getattr(doc, key)
		for key in ("hour_rate", "daily_pay", "ss_deduction", "tax_deduction", "net_daily_pay")
		if frappe.db.has_column("Attendance", key)
	}
	if values:
		frappe.db.set_value("Attendance", attendance_name, values, update_modified=False)


def _backfill_attendance_pay(company, start_date, end_date):
	"""Recompute hour rate, daily pay, and weekly SS on existing clocks in the demo week."""
	from hrms.payroll.daily_pay import allocate_week_deductions, resync_attendance_from_day_logs

	filters = {
		"attendance_date": ["between", [getdate(start_date), getdate(end_date)]],
		"docstatus": ("<", 2),
		"status": ["in", ["Present", "Work From Home", "Half Day"]],
	}
	if frappe.db.has_column("Attendance", "company"):
		filters["company"] = company

	touched = set()
	for row in frappe.get_all(
		"Attendance",
		filters=filters,
		fields=["name", "employee", "attendance_date", "daily_pay", "hour_rate"],
	):
		if flt(row.get("daily_pay")) and flt(row.get("hour_rate")):
			continue
		resync_attendance_from_day_logs(row.employee, row.attendance_date, attendance_name=row.name)
		_stamp_missing_attendance_pay(row.name)
		touched.add(row.employee)

	for employee in touched:
		allocate_week_deductions(employee, start_date)


def backfill_salary_slip_ss(company=None):
	"""Fill SS band fields on existing slips so Upcoming Payroll can show a contribution."""
	from hrms.payroll.social_security import apply_social_security

	filters = {"docstatus": ("<", 2)}
	if company:
		filters["company"] = company
	for name in frappe.get_all("Salary Slip", filters=filters, pluck="name"):
		slip = frappe.get_doc("Salary Slip", name)
		if flt(slip.get("ss_employee_amount")):
			continue
		apply_social_security(slip)
		if not flt(slip.get("ss_employee_amount")):
			continue
		values = {
			key: value
			for key, value in {
				"ss_weekly_earnings": slip.ss_weekly_earnings,
				"ss_insurable_earnings": slip.ss_insurable_earnings,
				"ss_wage_band": slip.ss_wage_band,
				"ss_category": slip.ss_category,
				"ss_employee_amount": slip.ss_employee_amount,
				"ss_employer_amount": slip.ss_employer_amount,
			}.items()
			if frappe.db.has_column("Salary Slip", key)
		}
		if values:
			frappe.db.set_value("Salary Slip", name, values, update_modified=False)


def _create_checkin(employee, time, log_type):
	frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": employee,
			"time": time,
			"device_id": "demo-device",
			"log_type": log_type,
		}
	).insert(ignore_permissions=True)


def _create_job_openings(company, departments, designations):
	for opening in JOB_OPENINGS:
		if frappe.db.exists("Job Opening", {"job_title": opening["job_title"], "company": company}):
			continue

		frappe.get_doc(
			{
				"doctype": "Job Opening",
				"job_title": opening["job_title"],
				"company": company,
				"department": departments[opening["department"]],
				"designation": designations[opening["designation"]],
				"status": "Open",
				"description": f"We are hiring a {opening['job_title']} to join our growing BPO team.",
				"publish": 1,
			}
		).insert(ignore_permissions=True)


def _create_job_applicants(designations):
	for applicant in JOB_APPLICANTS:
		if frappe.db.exists("Job Applicant", {"email_id": applicant["email"]}):
			continue

		frappe.get_doc(
			{
				"doctype": "Job Applicant",
				"applicant_name": applicant["applicant_name"],
				"email_id": applicant["email"],
				"status": applicant["status"],
				"designation": designations["Customer Service Representative"],
			}
		).insert(ignore_permissions=True)


def _set_default_company(company):
	frappe.db.set_single_value("Global Defaults", "default_company", company)
	frappe.db.set_default("company", company)


def seed_connected_bpo_demo(company=None):
	"""Fill attendance, payroll, SS, clients, invoices, and dashboard metrics."""
	from hrms.payroll.social_security import (
		ensure_employee_ss_fields,
		ensure_ss_salary_components,
		seed_belize_ssb_2022_table,
	)

	company = company or _get_company()
	if not company:
		print("No company found. Cannot seed connected BPO demo.")
		return

	print(f"Seeding connected BPO demo data for {company}...")
	was_importing = frappe.flags.in_import
	frappe.flags.in_import = True
	frappe.flags.skip_payroll_enqueue = True

	try:
		seed_belize_ssb_2022_table()
		ensure_employee_ss_fields()
		ensure_ss_salary_components()
		_ensure_holiday_list(company)
		_create_leave_period(company)
		_ensure_shift_type(company)
		customers = _create_demo_clients(company)
		employee_map = _demo_employee_map(company)
		if not employee_map:
			print("No demo employees found. Run import_hr_demo_data.run() first.")
			return

		_apply_employee_bpo_fields(company, employee_map)
		try:
			_ensure_salary_structure(company, employee_map)
		except Exception:
			frappe.log_error(title="Demo salary structure failed")
		_configure_demo_payroll_settings(company)
		history = seed_floor_history(company, list(employee_map.values()))
		exceptions = _stamp_attendance_exceptions(company, list(employee_map.values()))
		submitted = _submit_open_attendance(company, history["from_date"], history["to_date"])
		try:
			payroll = _seed_demo_payroll(company, list(employee_map.values()))
		except Exception:
			frappe.log_error(title="Demo payroll seed failed")
			payroll = {"slips": 0, "entries": 0}
		seed_demo_employee_banks(company, employee_map)
		try:
			invoices = _seed_demo_invoices(company, customers)
		except Exception:
			frappe.log_error(title="Demo invoice seed failed")
			invoices = 0
		_prepare_run_payroll_window(company)
		if not frappe.flags.in_test:
			frappe.db.commit()
		print(
			"Connected BPO demo: "
			f"{history['created']} clock days, {submitted} attendance submitted, "
			f"{exceptions['absent']} absent, {exceptions['late']} late, {exceptions['early']} early, "
			f"{payroll['slips']} salary slips, {invoices} client invoices."
		)
		return {
			"employees": len(employee_map),
			"clock_days": history["created"],
			"submitted": submitted,
			"absent": exceptions["absent"],
			"late": exceptions["late"],
			"early": exceptions["early"],
			"salary_slips": payroll["slips"],
			"payroll_entries": payroll["entries"],
			"invoices": invoices,
			"customers": customers,
		}
	finally:
		frappe.flags.in_import = was_importing


def _demo_employee_map(company):
	employee_map = {}
	for emp in EMPLOYEES:
		name = frappe.db.get_value("Employee", {"company_email": emp["email"], "company": company})
		if name:
			employee_map[emp["email"]] = name
	return employee_map


def _demo_ss_number(email: str) -> str:
	digits = f"{abs(hash(email)) % 10**9:09d}"
	if digits[0] == "0":
		digits = "1" + digits[1:]
	return digits


def _apply_employee_bpo_fields(company, employee_map):
	emp_by_email = {row["email"]: row for row in EMPLOYEES}
	meta = frappe.get_meta("Employee")
	for email, employee in employee_map.items():
		emp = emp_by_email.get(email) or {}
		designation = emp.get("designation") or frappe.db.get_value("Employee", employee, "designation")
		values = {}
		if meta.has_field("ctc"):
			values["ctc"] = HOUR_RATES.get(designation, DEMO_HOUR_RATE)
		if meta.has_field("social_security_number"):
			current = frappe.db.get_value("Employee", employee, "social_security_number")
			if not current:
				values["social_security_number"] = _demo_ss_number(email)
		if meta.has_field("bill_to_customer"):
			client = CLIENT_ASSIGNMENTS.get(email)
			if client and frappe.db.exists("Customer", client):
				values["bill_to_customer"] = client
		if meta.has_field("billing_rate"):
			values["billing_rate"] = BILLING_RATES.get(designation, 22.0)
		if meta.has_field("billing_currency"):
			values["billing_currency"] = "USD"
		if meta.has_field("default_shift"):
			values["default_shift"] = SHIFT_NAME
		if meta.has_field("holiday_list") and not frappe.db.get_value("Employee", employee, "holiday_list"):
			values["holiday_list"] = "Staff Pro Holiday List"
		if values:
			frappe.db.set_value("Employee", employee, values, update_modified=False)
	_apply_employee_bank_fields(employee_map)


def _ensure_shift_type(company):
	if frappe.db.exists("Shift Type", SHIFT_NAME):
		return SHIFT_NAME
	holiday_list = frappe.db.get_value("Company", company, "default_holiday_list") or "Staff Pro Holiday List"
	doc = frappe.get_doc(
		{
			"doctype": "Shift Type",
			"name": SHIFT_NAME,
			"start_time": "09:00:00",
			"end_time": "17:00:00",
			"holiday_list": holiday_list if frappe.db.exists("Holiday List", holiday_list) else None,
			"enable_late_entry_marking": 1,
			"late_entry_grace_period": 10,
			"enable_early_exit_marking": 1,
			"early_exit_grace_period": 10,
			"working_hours_calculation_based_on": "Every Valid Check-in and Check-out",
			"determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
		}
	)
	doc.insert(ignore_permissions=True)
	return SHIFT_NAME


def _create_demo_clients(company):
	from hrms.payroll.bpo_client_accounts import setup_usd_client_billing

	customer_group = _ensure_customer_group()
	territory = _ensure_territory()
	names = []
	for client in CLIENTS:
		name = client["customer_name"]
		if frappe.db.exists("Customer", name):
			updates = {
				"default_billing_rate": client["default_billing_rate"],
			}
			if frappe.get_meta("Customer").has_field("campaign_name"):
				updates["campaign_name"] = client["campaign_name"]
			if frappe.get_meta("Customer").has_field("service_type"):
				updates["service_type"] = client["service_type"]
			if frappe.get_meta("Customer").has_field("contracted_seats"):
				updates["contracted_seats"] = client["contracted_seats"]
			frappe.db.set_value("Customer", name, updates, update_modified=False)
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": name,
					"customer_type": "Company",
					"customer_group": customer_group,
					"territory": territory,
					"default_billing_rate": client["default_billing_rate"],
					"campaign_name": client["campaign_name"],
					"service_type": client["service_type"],
					"contracted_seats": client["contracted_seats"],
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert()
		names.append(name)
	try:
		setup_usd_client_billing()
	except Exception:
		frappe.log_error(title="Demo USD client billing setup failed")
	return names


def _ensure_customer_group():
	for name in ("Commercial", "All Customer Groups", "Individual"):
		if frappe.db.exists("Customer Group", name):
			return name
	leaf = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
	if leaf:
		return leaf
	parent = frappe.db.get_value("Customer Group", {"is_group": 1}, "name") or "All Customer Groups"
	if not frappe.db.exists("Customer Group", parent):
		frappe.get_doc({"doctype": "Customer Group", "customer_group_name": parent, "is_group": 1}).insert(
			ignore_permissions=True
		)
	doc = frappe.get_doc(
		{"doctype": "Customer Group", "customer_group_name": "Commercial", "parent_customer_group": parent, "is_group": 0}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_territory():
	for name in ("All Territories", "Belize", "Rest Of The World"):
		if frappe.db.exists("Territory", name):
			return name
	leaf = frappe.db.get_value("Territory", {"is_group": 0}, "name")
	if leaf:
		return leaf
	doc = frappe.get_doc({"doctype": "Territory", "territory_name": "All Territories", "is_group": 1})
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_salary_structure(company, employee_map):
	currency = frappe.db.get_value("Company", company, "default_currency") or "BZD"
	_ensure_basic_hourly_component(company)
	structure = _get_or_create_weekly_structure(company, currency)
	for employee in employee_map.values():
		_assign_structure_if_missing(company, employee, structure, currency)
	return structure


def _ensure_basic_hourly_component(company):
	account = _salary_expense_account(company)
	if not frappe.db.exists("Salary Component", BASIC_COMPONENT):
		doc = frappe.get_doc(
			{
				"doctype": "Salary Component",
				"salary_component": BASIC_COMPONENT,
				"salary_component_abbr": "BH",
				"type": "Earning",
				"depends_on_payment_days": 1,
				"is_tax_applicable": 0,
				"amount_based_on_formula": 1,
				"formula": "base",
				"do_not_include_in_accounts": 0,
			}
		)
		if account:
			doc.append("accounts", {"company": company, "account": account})
		doc.insert(ignore_permissions=True)
		return

	if account and not frappe.db.exists(
		"Salary Component Account", {"parent": BASIC_COMPONENT, "company": company}
	):
		component = frappe.get_doc("Salary Component", BASIC_COMPONENT)
		component.append("accounts", {"company": company, "account": account})
		component.save(ignore_permissions=True)


def _salary_expense_account(company):
	return (
		frappe.get_cached_value("Company", company, "default_payroll_payable_account")
		or frappe.get_cached_value("Company", company, "default_expense_account")
		or frappe.db.get_value(
			"Account",
			{"company": company, "root_type": "Expense", "is_group": 0, "disabled": 0},
			"name",
			order_by="creation",
		)
	)


def _get_or_create_weekly_structure(company, currency):
	existing = frappe.db.get_value(
		"Salary Structure",
		{"name": SALARY_STRUCTURE, "docstatus": 1, "company": company},
		"name",
	)
	if existing:
		return existing

	if frappe.db.exists("Salary Structure", SALARY_STRUCTURE):
		doc = frappe.get_doc("Salary Structure", SALARY_STRUCTURE)
		if doc.docstatus == 0:
			if not doc.earnings:
				doc.append(
					"earnings",
					{
						"salary_component": BASIC_COMPONENT,
						"abbr": "BH",
						"amount_based_on_formula": 1,
						"formula": "base",
						"depends_on_payment_days": 1,
					},
				)
			doc.company = company
			doc.currency = currency
			doc.payroll_frequency = "Weekly"
			doc.hour_rate = DEMO_HOUR_RATE
			doc.salary_slip_based_on_timesheet = 0
			doc.is_active = "Yes"
			doc.save(ignore_permissions=True)
			doc.submit()
		return doc.name

	doc = frappe.get_doc(
		{
			"doctype": "Salary Structure",
			"name": SALARY_STRUCTURE,
			"company": company,
			"currency": currency,
			"payroll_frequency": "Weekly",
			"is_active": "Yes",
			"hour_rate": DEMO_HOUR_RATE,
			"salary_slip_based_on_timesheet": 0,
			"earnings": [
				{
					"salary_component": BASIC_COMPONENT,
					"abbr": "BH",
					"amount_based_on_formula": 1,
					"formula": "base",
					"depends_on_payment_days": 1,
				}
			],
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc.name


def _assign_structure_if_missing(company, employee, structure, currency):
	if frappe.db.exists(
		"Salary Structure Assignment",
		{"employee": employee, "docstatus": 1, "salary_structure": structure},
	):
		return
	joining = frappe.db.get_value("Employee", employee, "date_of_joining") or add_months(nowdate(), -6)
	hour_rate = flt(frappe.db.get_value("Employee", employee, "ctc")) or DEMO_HOUR_RATE
	try:
		assignment = frappe.new_doc("Salary Structure Assignment")
		assignment.employee = employee
		assignment.salary_structure = structure
		assignment.company = company
		assignment.currency = currency
		assignment.from_date = joining
		assignment.base = flt(hour_rate * 40, 2)
		assignment.flags.ignore_permissions = True
		assignment.insert()
		assignment.submit()
	except Exception:
		frappe.log_error(title="Demo salary structure assignment failed")


def _configure_demo_payroll_settings(company):
	from hrms.patches.v16_0.add_invoicing_workspace import ensure_bpo_agent_hours_item

	ensure_bpo_agent_hours_item()
	cycle_start = _demo_cycle_start()
	values = {
		"payroll_based_on": "Attendance",
		"consider_unmarked_attendance_as": "Present",
		"email_salary_slip_to_employee": 0,
		"enable_automatic_payroll": 1,
		"automatic_payroll_submit_slips": 1,
		"automatic_payroll_company": company,
		"automatic_payroll_weekly_days": 5,
		"automatic_payroll_fortnightly_days": 0,
		"automatic_payroll_monthly_days": 0,
		"automatic_payroll_frequency": "Weekly",
		"automatic_payroll_cycle_start": cycle_start,
		"enable_automatic_client_invoice": 1,
		"automatic_invoice_weekly_days": 5,
		"automatic_invoice_fortnightly_days": 0,
		"automatic_invoice_monthly_days": 0,
	}
	meta = frappe.get_meta("Payroll Settings")
	values = {key: value for key, value in values.items() if meta.has_field(key)}
	if values:
		frappe.db.set_single_value("Payroll Settings", values, update_modified=False)


def _demo_cycle_start():
	anchor = get_first_day(add_months(nowdate(), -2))
	return add_days(anchor, (7 - getdate(anchor).weekday()) % 7)


def seed_floor_history(company, employees):
	"""Seed Mon–Fri clocks from last month through today so dashboard charts have a series."""
	today = getdate()
	from_date = get_first_day(add_months(today, -1))
	created = 0
	for index, employee in enumerate(employees):
		day = from_date
		while day <= today:
			if day.weekday() < 5 and _seed_history_day(index, employee, day):
				created += 1
			day = add_days(day, 1)
		from hrms.payroll.daily_pay import allocate_week_deductions

		week = get_first_day_of_week(from_date)
		while week <= today:
			allocate_week_deductions(employee, week)
			week = add_days(week, 7)

	_refresh_today_demo_clocks(employees)
	_backfill_attendance_pay(company, from_date, today)
	return {"created": created, "from_date": from_date, "to_date": today}


def _seed_history_day(index, employee, day) -> bool:
	plan = _demo_day_plan(index, day)
	if plan == "leave":
		return False
	existing = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": day, "docstatus": ("<", 2)},
		["name", "status", "working_hours", "docstatus"],
		as_dict=True,
	)
	if existing and existing.status == "On Leave":
		return False
	if (
		existing
		and cint(existing.docstatus) == 1
		and existing.status != "Absent"
		and flt(existing.working_hours) >= 1
		and getdate(day) != getdate()
	):
		return False
	if plan == "absent":
		return _mark_absent(employee, day)
	punches = _demo_punches_for(index, day)
	if getdate(day) == getdate() and day.weekday() < 5:
		punches = _punches_until_now(punches)
	if _replace_day_demo_punches(employee, day, punches):
		return True
	return _seed_day_hours(employee, day, punches)


def _demo_day_plan(index: int, day) -> str:
	weekday = getdate(day).weekday()
	# Keep today present so Agents Present (Today) is populated.
	if getdate(day) == getdate():
		return "present"
	# A few absences so Floor Attendance is not 100% present.
	if (index + weekday + getdate(day).day) % 17 == 0:
		return "absent"
	if (index + weekday + getdate(day).day) % 23 == 0:
		return "absent"
	return "present"


def _mark_absent(employee, day) -> bool:
	existing = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": day, "docstatus": ("<", 2)},
		["name", "status", "docstatus"],
		as_dict=True,
	)
	if existing:
		if existing.status == "On Leave" or cint(existing.docstatus) == 1:
			return False
		frappe.db.set_value("Attendance", existing.name, "status", "Absent", update_modified=False)
		return True
	if frappe.db.count(
		"Employee Checkin",
		{"employee": employee, "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
	):
		return False
	doc = frappe.get_doc(
		{
			"doctype": "Attendance",
			"employee": employee,
			"attendance_date": day,
			"status": "Absent",
			"company": frappe.db.get_value("Employee", employee, "company"),
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return True


def _punches_until_now(punches: list[tuple[str, str]]) -> list[tuple[str, str]]:
	from datetime import datetime

	from frappe.utils import get_time, now_datetime

	now = now_datetime()
	if getdate(now) != getdate():
		return punches
	kept = []
	for clock, log_type in punches:
		when = datetime.combine(getdate(now), get_time(clock))
		if when <= now:
			kept.append((clock, log_type))
	return kept or punches[:1]


def _submit_open_attendance(company, start_date, end_date) -> int:
	filters = {
		"docstatus": 0,
		"attendance_date": ["between", [getdate(start_date), getdate(end_date)]],
	}
	if frappe.db.has_column("Attendance", "company"):
		filters["company"] = company
	submitted = 0
	for name in frappe.get_all("Attendance", filters=filters, pluck="name"):
		try:
			doc = frappe.get_doc("Attendance", name)
			if doc.status in ("Present", "Half Day", "Work From Home") and not flt(doc.working_hours):
				_stamp_missing_attendance_pay(name)
				doc.reload()
			doc.flags.ignore_permissions = True
			doc.submit()
			submitted += 1
		except Exception:
			frappe.log_error(title="Demo attendance submit failed")
	return submitted


def _stamp_attendance_exceptions(company, employees) -> dict:
	"""Mark late entry / early exit on submitted or draft present days from punch times."""
	from datetime import datetime

	from frappe.utils import get_time

	start = get_first_day(nowdate())
	end = getdate()
	late = early = absent = 0
	filters = {
		"attendance_date": ["between", [start, end]],
		"docstatus": ("<", 2),
		"status": ["in", ["Present", "Half Day", "Work From Home"]],
	}
	if frappe.db.has_column("Attendance", "company"):
		filters["company"] = company
	for row in frappe.get_all(
		"Attendance",
		filters=filters,
		fields=["name", "employee", "attendance_date", "in_time", "out_time", "late_entry", "early_exit"],
	):
		values = {}
		in_time = row.in_time
		out_time = row.out_time
		if in_time:
			threshold = datetime.combine(getdate(row.attendance_date), get_time("09:10:00"))
			if getdate(in_time) and in_time > threshold:
				values["late_entry"] = 1
		if out_time:
			threshold = datetime.combine(getdate(row.attendance_date), get_time("16:50:00"))
			if out_time < threshold:
				values["early_exit"] = 1
		if values:
			frappe.db.set_value("Attendance", row.name, values, update_modified=False)
			late += cint(values.get("late_entry"))
			early += cint(values.get("early_exit"))

	absent_filters = {
		"attendance_date": ["between", [start, end]],
		"docstatus": ("<", 2),
		"status": "Absent",
	}
	if frappe.db.has_column("Attendance", "company"):
		absent_filters["company"] = company
	absent = frappe.db.count("Attendance", absent_filters)
	return {"late": late, "early": early, "absent": absent}


def _completed_week_bounds(as_of=None):
	as_of = getdate(as_of or nowdate())
	this_week = getdate(get_first_day_of_week(as_of))
	weeks = []
	start = getdate(_demo_cycle_start())
	while start < this_week:
		end = add_days(start, 4)
		weeks.append((start, end))
		start = add_days(start, 7)
	return weeks


def _seed_demo_payroll(company, employees) -> dict:
	from hrms.payroll.auto_payroll import create_or_submit_payroll_entry, get_payroll_customers

	weeks = _completed_week_bounds()
	if not weeks:
		return {"entries": 0, "slips": 0}

	# Leave the latest completed week for "Run Payroll Now".
	historical = weeks[:-LEAVE_OPEN_PAY_PERIODS] if len(weeks) > LEAVE_OPEN_PAY_PERIODS else weeks[:1]
	settings = frappe.get_single("Payroll Settings")
	settings.automatic_payroll_submit_slips = 0
	customers = get_payroll_customers(company) or [None]
	entries = 0
	for start_date, end_date in historical:
		for customer in customers:
			filters = {
				"company": company,
				"start_date": start_date,
				"end_date": end_date,
				"docstatus": ("<", 2),
			}
			if customer:
				filters["customer"] = customer
			existing = frappe.db.exists("Payroll Entry", filters)
			try:
				if existing:
					entry = frappe.get_doc("Payroll Entry", existing)
					if entry.docstatus == 0:
						create_or_submit_payroll_entry(
							settings,
							company,
							start_date,
							end_date,
							existing=entry,
							frequency="Weekly",
							customer=customer,
						)
				else:
					create_or_submit_payroll_entry(
						settings,
						company,
						start_date,
						end_date,
						frequency="Weekly",
						customer=customer,
					)
				entries += 1
			except Exception:
				frappe.log_error(title="Demo payroll entry failed")
				_create_week_salary_slips(company, employees, start_date, end_date)

	submitted = _submit_demo_salary_slips(company)
	backfill_salary_slip_ss(company)
	return {"entries": entries, "slips": submitted}


def _create_week_salary_slips(company, employees, start_date, end_date):
	for employee in employees:
		if frappe.db.exists(
			"Salary Slip",
			{
				"employee": employee,
				"start_date": start_date,
				"end_date": end_date,
				"docstatus": ("<", 2),
			},
		):
			continue
		try:
			slip = frappe.new_doc("Salary Slip")
			slip.employee = employee
			slip.company = company
			slip.salary_structure = SALARY_STRUCTURE
			slip.payroll_frequency = "Weekly"
			slip.start_date = start_date
			slip.end_date = end_date
			slip.posting_date = end_date
			slip.salary_slip_based_on_timesheet = 0
			slip.letter_head = None
			slip.flags.ignore_permissions = True
			slip.insert()
		except Exception:
			frappe.log_error(title="Demo salary slip create failed")


def _submit_demo_salary_slips(company) -> int:
	submitted = 0
	frappe.flags.via_payroll_entry = True
	try:
		for name in frappe.get_all(
			"Salary Slip",
			filters={"company": company, "docstatus": 0},
			pluck="name",
		):
			try:
				slip = frappe.get_doc("Salary Slip", name)
				if not flt(slip.get("ss_employee_amount")):
					from hrms.payroll.social_security import apply_social_security

					apply_social_security(slip)
					slip.calculate_net_pay()
					slip.save(ignore_permissions=True)
				slip.flags.ignore_permissions = True
				slip.submit()
				submitted += 1
			except Exception:
				frappe.log_error(title="Demo salary slip submit failed")
	finally:
		frappe.flags.via_payroll_entry = False
	return submitted


def _seed_demo_invoices(company, customers) -> int:
	from hrms.payroll.auto_client_invoice import create_or_submit_client_invoice

	if not frappe.db.exists("DocType", "Client Invoice"):
		return 0
	weeks = _completed_week_bounds()
	if not weeks:
		return 0
	historical = weeks[:-LEAVE_OPEN_PAY_PERIODS] if len(weeks) > LEAVE_OPEN_PAY_PERIODS else weeks[:1]
	created = 0
	for customer in customers:
		for start_date, end_date in historical[-4:]:
			existing = frappe.db.get_value(
				"Client Invoice",
				{
					"company": company,
					"customer": customer,
					"from_date": start_date,
					"to_date": end_date,
					"docstatus": ("<", 2),
				},
				"name",
			)
			try:
				invoice = create_or_submit_client_invoice(
					company,
					customer,
					start_date,
					end_date,
					frappe.get_doc("Client Invoice", existing) if existing else None,
					frequency="Weekly",
				)
			except Exception:
				frappe.log_error(title="Demo client invoice failed")
				continue
			if invoice:
				created += 1
	return created


def _prepare_run_payroll_window(company):
	"""Drop blocking drafts and mark the last seeded week paid so Run Payroll Now hits the open week."""
	from hrms.payroll.auto_payroll import build_payroll_entry

	for name in frappe.get_all(
		"Payroll Entry",
		filters={"company": company, "docstatus": 0},
		pluck="name",
	):
		frappe.delete_doc("Payroll Entry", name, force=True, ignore_permissions=True)

	weeks = _completed_week_bounds()
	if len(weeks) <= LEAVE_OPEN_PAY_PERIODS:
		return
	start_date, end_date = weeks[-1 - LEAVE_OPEN_PAY_PERIODS]
	if frappe.db.exists(
		"Payroll Entry",
		{"company": company, "start_date": start_date, "end_date": end_date, "docstatus": 1},
	):
		return

	settings = frappe.get_single("Payroll Settings")
	try:
		entry = build_payroll_entry(settings, company, start_date, end_date, "Weekly")
		entry.flags.ignore_mandatory = True
		entry.flags.ignore_permissions = True
		entry.insert()
		frappe.db.set_value(
			"Payroll Entry",
			entry.name,
			{
				"docstatus": 1,
				"status": "Submitted",
				"salary_slips_created": 1,
				"salary_slips_submitted": 1,
			},
			update_modified=False,
		)
	except Exception:
		frappe.log_error(title="Demo payroll cycle anchor failed")


def repair_payroll_window(company=None):
	company = company or _get_company()
	_prepare_run_payroll_window(company)
	if not frappe.flags.in_test:
		frappe.db.commit()
	status(company)


def verify_ss_report(company=None):
	from hrms.payroll.report.social_security_deductions.social_security_deductions import execute as ss_report

	company = company or _get_company()
	_cols, data = ss_report(
		{
			"company": company,
			"from_date": str(get_first_day(nowdate())),
			"to_date": nowdate(),
		}
	)
	print(f"SS deduction rows this month: {len(data)}")
	if data:
		row = data[0]
		print(
			f"Sample: {row.get('employee_name')} SS# {row.get('ss_number')} "
			f"emp={row.get('ss_employee_amount')} empr={row.get('ss_employer_amount')} band={row.get('ss_wage_band')}"
		)
	if frappe.db.exists("DocType", "Client Invoice"):
		invoice = frappe.get_all(
			"Client Invoice",
			filters={"company": company, "docstatus": 1},
			fields=["name", "customer", "from_date", "to_date", "total_hours", "total_amount"],
			order_by="to_date desc",
			limit=3,
		)
		for row in invoice:
			print(
				f"Invoice {row.name} {row.customer} {row.from_date}–{row.to_date} "
				f"{row.total_hours}h ${row.total_amount}"
			)
	return len(data)
