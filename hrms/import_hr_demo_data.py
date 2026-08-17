"""Import HR portal demo data for Staff Pro BPO."""

import frappe
from frappe.utils import add_days, get_first_day, get_last_day, getdate, nowdate, now_datetime

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
	{"first_name": "Maria", "last_name": "Santos", "email": "maria.santos@staffpro.local", "gender": "Female", "department": "Human Resources", "designation": "HR Manager", "reports_to": None},
	{"first_name": "James", "last_name": "Rivera", "email": "james.rivera@staffpro.local", "gender": "Male", "department": "Operations", "designation": "Operations Manager", "reports_to": "maria.santos@staffpro.local"},
	{"first_name": "Ana", "last_name": "Cruz", "email": "ana.cruz@staffpro.local", "gender": "Female", "department": "Customer Support", "designation": "Team Lead", "reports_to": "james.rivera@staffpro.local"},
	{"first_name": "Carlos", "last_name": "Mendoza", "email": "carlos.mendoza@staffpro.local", "gender": "Male", "department": "Customer Support", "designation": "Customer Service Representative", "reports_to": "ana.cruz@staffpro.local"},
	{"first_name": "Sofia", "last_name": "Reyes", "email": "sofia.reyes@staffpro.local", "gender": "Female", "department": "Customer Support", "designation": "Customer Service Representative", "reports_to": "ana.cruz@staffpro.local"},
	{"first_name": "Miguel", "last_name": "Torres", "email": "miguel.torres@staffpro.local", "gender": "Male", "department": "Customer Support", "designation": "Customer Service Representative", "reports_to": "ana.cruz@staffpro.local"},
	{"first_name": "Elena", "last_name": "Garcia", "email": "elena.garcia@staffpro.local", "gender": "Female", "department": "Quality Assurance", "designation": "Quality Analyst", "reports_to": "james.rivera@staffpro.local"},
	{"first_name": "Diego", "last_name": "Lopez", "email": "diego.lopez@staffpro.local", "gender": "Male", "department": "Training", "designation": "Trainer", "reports_to": "maria.santos@staffpro.local"},
	{"first_name": "Laura", "last_name": "Fernandez", "email": "laura.fernandez@staffpro.local", "gender": "Female", "department": "Finance", "designation": "Accountant", "reports_to": "maria.santos@staffpro.local"},
	{"first_name": "Pedro", "last_name": "Ramirez", "email": "pedro.ramirez@staffpro.local", "gender": "Male", "department": "IT", "designation": "IT Support Specialist", "reports_to": "james.rivera@staffpro.local"},
	{"first_name": "Isabella", "last_name": "Morales", "email": "isabella.morales@staffpro.local", "gender": "Female", "department": "Customer Support", "designation": "Customer Service Representative", "reports_to": "ana.cruz@staffpro.local"},
	{"first_name": "Luis", "last_name": "Herrera", "email": "luis.herrera@staffpro.local", "gender": "Male", "department": "Operations", "designation": "Supervisor", "reports_to": "james.rivera@staffpro.local"},
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


def run(company=None):
	company = company or _get_company()
	if not company:
		print("No company found. Complete setup wizard first.")
		return

	if _has_hr_demo_data(company):
		print(f"HR demo data already exists for {company}. Run clear() first to reset.")
		return

	print(f"Creating HR demo data for {company}...")
	frappe.flags.in_import = True

	try:
		departments = _create_departments(company)
		designations = _create_designations()
		holiday_list = _ensure_holiday_list(company)
		_create_leave_period(company)
		employee_map = _create_employees(company, departments, designations, holiday_list)
		_create_leave_allocations(company, employee_map)
		_create_leave_applications(company, employee_map)
		_create_attendance(employee_map)
		_create_job_openings(company, departments, designations)
		_create_job_applicants(designations)
		_set_default_company(company)
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


def status(company=None):
	company = company or _get_company()
	for doctype in (
		"Department",
		"Employee",
		"Leave Allocation",
		"Leave Application",
		"Attendance",
		"Job Opening",
		"Job Applicant",
	):
		if frappe.get_meta(doctype).has_field("company"):
			count = frappe.db.count(doctype, {"company": company})
		else:
			count = frappe.db.count(doctype)
		print(f"{doctype}: {count}")


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
	list_name = "Staff Pro Holiday List"
	today = getdate()
	from_date = get_first_day(today.replace(month=1, day=1))
	to_date = get_last_day(today.replace(month=12, day=31))

	if not frappe.db.exists("Holiday List", list_name):
		holiday_list = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": list_name,
				"from_date": from_date,
				"to_date": to_date,
				"weekly_off": "Sunday",
			}
		).insert(ignore_permissions=True)
		holiday_list.get_weekly_off_dates()
		holiday_list.save(ignore_permissions=True)

	if not frappe.db.get_value("Company", company, "default_holiday_list"):
		frappe.db.set_value("Company", company, "default_holiday_list", list_name)

	if not frappe.db.exists(
		"Holiday List Assignment",
		{"applicable_for": "Company", "assigned_to": company, "holiday_list": list_name},
	):
		assignment = frappe.get_doc(
			{
				"doctype": "Holiday List Assignment",
				"applicable_for": "Company",
				"assigned_to": company,
				"holiday_list": list_name,
				"from_date": from_date,
			}
		)
		assignment.insert(ignore_permissions=True)
		assignment.submit()

	return list_name


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


def _ensure_user(email, first_name):
	if frappe.db.exists("User", email):
		return email

	frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"new_password": "StaffPro@2026!Demo",
			"send_welcome_email": 0,
			"roles": [{"doctype": "Has Role", "role": "Employee"}],
		}
	).insert(ignore_permissions=True)
	return email


def _create_employees(company, departments, designations, holiday_list):
	employee_map = {}
	join_date = add_days(getdate(), -180)

	for emp in EMPLOYEES:
		if frappe.db.exists("Employee", {"company_email": emp["email"]}):
			employee_map[emp["email"]] = frappe.db.get_value("Employee", {"company_email": emp["email"]})
			continue

		user_id = _ensure_user(emp["email"], emp["first_name"])
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"naming_series": "EMP-",
				"first_name": emp["first_name"],
				"last_name": emp["last_name"],
				"company": company,
				"user_id": user_id,
				"date_of_birth": "1990-05-08",
				"date_of_joining": join_date,
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
	emails = list(employee_map.keys())[:8]

	for offset in range(-10, 0):
		attendance_date = getdate(add_days(nowdate(), offset))
		if attendance_date.weekday() == 6:
			continue

		for email in emails:
			employee = employee_map[email]
			if frappe.db.exists("Attendance", {"employee": employee, "attendance_date": attendance_date}):
				continue

			status = "Present"
			if offset == -3 and email == emails[2]:
				status = "On Leave"

			doc = frappe.get_doc(
				{
					"doctype": "Attendance",
					"employee": employee,
					"attendance_date": attendance_date,
					"status": status,
					"company": frappe.db.get_value("Employee", employee, "company"),
				}
			)
			doc.insert(ignore_permissions=True)
			doc.submit()

			if status == "Present":
				checkin_time = now_datetime().replace(
					year=attendance_date.year,
					month=attendance_date.month,
					day=attendance_date.day,
					hour=9,
					minute=0,
					second=0,
				)
				checkout_time = checkin_time.replace(hour=18)
				_create_checkin(employee, checkin_time, "IN")
				_create_checkin(employee, checkout_time, "OUT")


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
