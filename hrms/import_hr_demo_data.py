"""Import HR portal demo data for Staff Pro BPO."""

import frappe
from frappe.utils import add_days, flt, get_first_day, get_last_day, getdate, nowdate

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
		seed_demo_profile_images()
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

	from hrms.hr.belize_holidays import add_belize_holidays_to_list

	add_belize_holidays_to_list(list_name, year=from_date.year)

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


def _create_employees(company, departments, designations, holiday_list):
	employee_map = {}

	for emp in EMPLOYEES:
		if frappe.db.exists("Employee", {"company_email": emp["email"]}):
			employee_map[emp["email"]] = frappe.db.get_value("Employee", {"company_email": emp["email"]})
			continue

		user_id = _ensure_user(emp["email"], emp["first_name"], emp["last_name"], _demo_avatar_url(emp))
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"naming_series": "EMP-",
				"first_name": emp["first_name"],
				"last_name": emp["last_name"],
				"company": company,
				"user_id": user_id,
				"image": _demo_avatar_url(emp),
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
	backfill_salary_slip_ss(company)
	if not frappe.flags.in_test:
		frappe.db.commit()
	print(f"Seeded demo hours: {created} days created, {skipped} skipped.")
	return {"created": created, "skipped": skipped, "refreshed_today": refreshed, "week_start": str(week_start), "employees": employee_ids}


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
	return [("09:00:00", "IN"), ("12:00:00", "OUT"), ("13:00:00", "IN"), ("17:00:00", "OUT")]


def _refresh_today_demo_clocks(employee_ids) -> int:
	"""Rebuild today's demo-device punches so Who Is In matches the current clock."""
	today = getdate()
	if today.weekday() >= 5:
		return 0
	refreshed = 0
	for index, employee in enumerate(employee_ids):
		if _replace_day_demo_punches(employee, today, _demo_punches_for(index, today)):
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
		["name", "status", "working_hours"],
		as_dict=True,
	)
	if existing and existing.status == "On Leave":
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
