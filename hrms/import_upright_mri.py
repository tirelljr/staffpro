# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Import the Upright MRI client and linked agents from the campaign PDF."""

from __future__ import annotations

from datetime import timedelta

import frappe
from frappe.utils import add_days, flt, get_weekday, getdate, nowdate

from hrms.hr.doctype.shift_assignment_tool.shift_assignment_tool import create_shift_assignment
from hrms.hr.doctype.shift_schedule.shift_schedule import get_or_insert_shift_schedule

CLIENT_NAME = "Upright MRI"
CAMPAIGN_NAME = "Upright MRI"
COMPANY_FALLBACK = "Staff Pro BPO"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
SATURDAY_WEEKS = 26
LUNCH_NOTE = (
	"All agents have a 1 hour unpaid lunch. "
	"All work Monday to Friday. "
	"Saturdays rotate: only one agent works each Saturday."
)

AGENTS = (
	{
		"first_name": "Audrey",
		"last_name": "Tun",
		"gender": "Female",
		"ctc": 8.0,
		"date_of_birth": "2000-10-24",
		"date_of_joining": "2026-07-14",
		"social_security_number": "000402361",
		"start_time": "07:00:00",
		"end_time": "16:00:00",
		"shift_label": "Upright MRI 7:00 AM – 4:00 PM",
	},
	{
		"first_name": "Aurora",
		"last_name": "Rodriguez",
		"gender": "Female",
		"ctc": 10.0,
		"date_of_birth": "1989-01-14",
		"date_of_joining": "2023-06-01",
		"social_security_number": "000322125",
		"start_time": "09:00:00",
		"end_time": "18:00:00",
		"shift_label": "Upright MRI 9:00 AM – 6:00 PM",
	},
	{
		"first_name": "Emogene",
		"last_name": "Walton",
		"gender": "Female",
		"ctc": 8.0,
		"date_of_birth": "2001-10-01",
		"date_of_joining": "2026-03-12",
		"social_security_number": "000485212",
		"start_time": "07:30:00",
		"end_time": "16:30:00",
		"shift_label": "Upright MRI 7:30 AM – 4:30 PM",
	},
	{
		"first_name": "Gianie",
		"last_name": "Salazar",
		"gender": "Female",
		"ctc": 9.0,
		"date_of_birth": "2001-10-19",
		"date_of_joining": "2025-06-25",
		"social_security_number": "000405462",
		"start_time": "06:30:00",
		"end_time": "15:30:00",
		"shift_label": "Upright MRI 6:30 AM – 3:30 PM",
	},
	{
		"first_name": "Mildre",
		"last_name": "Gonzalez",
		"gender": "Female",
		"ctc": 9.0,
		"date_of_birth": "1992-11-24",
		"date_of_joining": "2026-09-14",
		"social_security_number": "000215200",
		"start_time": "07:00:00",
		"end_time": "16:00:00",
		"shift_label": "Upright MRI 7:00 AM – 4:00 PM",
	},
)


def run():
	frappe.set_user("Administrator")
	company = _company()
	client = _ensure_client(company)
	campaign = _ensure_campaign()
	department = _ensure_link("Department", "Operations", company)
	designation = _ensure_designation()
	holiday_list = _holiday_list(company)
	shifts = {}
	weekday_schedules = {}
	for agent in AGENTS:
		shifts[agent["shift_label"]] = _ensure_shift_type(
			agent["shift_label"], agent["start_time"], agent["end_time"], holiday_list
		)
	for label, shift_type in shifts.items():
		weekday_schedules[label] = get_or_insert_shift_schedule(shift_type, "Every Week", WEEKDAYS)

	created = []
	updated = []
	for agent in AGENTS:
		name, was_new = _ensure_agent(
			agent,
			company=company,
			client=client,
			campaign=campaign,
			department=department,
			designation=designation,
			holiday_list=holiday_list,
			shift_type=shifts[agent["shift_label"]],
		)
		_ensure_weekday_assignment(name, company, weekday_schedules[agent["shift_label"]], agent)
		(created if was_new else updated).append(name)

	saturdays = _assign_saturday_rotation(company, shifts)
	structure = _assign_salary_structures(company, created + updated)
	_comment_client(client)
	frappe.db.commit()
	return {
		"client": client,
		"campaign": campaign,
		"company": company,
		"created": created,
		"updated": updated,
		"saturday_assignments": saturdays,
		"salary_structure": structure,
	}


def _company() -> str:
	return (
		frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {"company_name": COMPANY_FALLBACK}, "name")
		or frappe.db.get_value("Company", {}, "name")
	)


def _ensure_client(company: str) -> str:
	from hrms.payroll.bpo_client_accounts import setup_usd_client_billing

	existing = frappe.db.exists("Customer", CLIENT_NAME) or frappe.db.get_value(
		"Customer", {"customer_name": CLIENT_NAME}, "name"
	)
	values = {
		"customer_name": CLIENT_NAME,
		"customer_type": "Company",
		"customer_group": _customer_group(),
		"territory": _territory(),
	}
	meta = frappe.get_meta("Customer")
	if meta.has_field("campaign_name"):
		values["campaign_name"] = CAMPAIGN_NAME
	if meta.has_field("service_type"):
		values["service_type"] = "Back Office"
	if meta.has_field("contracted_seats"):
		values["contracted_seats"] = len(AGENTS)
	if meta.has_field("billing_currency"):
		values["billing_currency"] = "USD"
	if existing:
		frappe.db.set_value("Customer", existing, values, update_modified=False)
		name = existing
	else:
		doc = frappe.get_doc({"doctype": "Customer", **values})
		doc.flags.ignore_permissions = True
		doc.insert()
		name = doc.name
	try:
		setup_usd_client_billing()
	except Exception:
		frappe.log_error(title="Upright MRI USD billing setup failed")
	return name


def _ensure_campaign() -> str | None:
	if not frappe.db.exists("DocType", "Employee Grade"):
		return None
	if frappe.db.exists("Employee Grade", CAMPAIGN_NAME):
		return CAMPAIGN_NAME
	doc = frappe.get_doc({"doctype": "Employee Grade", "name": CAMPAIGN_NAME, "grade_name": CAMPAIGN_NAME})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def _ensure_designation() -> str | None:
	for name in ("Agent", "Customer Service Representative"):
		if frappe.db.exists("Designation", name):
			return name
	doc = frappe.get_doc({"doctype": "Designation", "designation_name": "Agent"})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def _ensure_link(doctype: str, name: str, company: str | None = None) -> str | None:
	if frappe.db.exists(doctype, name):
		return name
	if doctype == "Department" and company:
		abbr = frappe.db.get_value("Company", company, "abbr")
		full = f"{name} - {abbr}" if abbr else name
		if frappe.db.exists(doctype, full):
			return full
		parent = frappe.db.get_value("Department", {"is_group": 1, "company": company}, "name")
		doc = frappe.get_doc(
			{
				"doctype": "Department",
				"department_name": name,
				"company": company,
				"parent_department": parent,
				"is_group": 0,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		return doc.name
	found = frappe.db.get_value(doctype, {}, "name")
	return found


def _holiday_list(company: str) -> str | None:
	for name in (
		frappe.db.get_value("Company", company, "default_holiday_list"),
		"Staff Pro Holiday List",
		frappe.db.get_value("Holiday List", {}, "name"),
	):
		if name and frappe.db.exists("Holiday List", name):
			return name
	return None


def _ensure_shift_type(label: str, start_time: str, end_time: str, holiday_list: str | None) -> str:
	if frappe.db.exists("Shift Type", label):
		frappe.db.set_value(
			"Shift Type",
			label,
			{"start_time": start_time, "end_time": end_time, "holiday_list": holiday_list},
			update_modified=False,
		)
		return label
	doc = frappe.get_doc(
		{
			"doctype": "Shift Type",
			"name": label,
			"start_time": start_time,
			"end_time": end_time,
			"holiday_list": holiday_list,
			"enable_late_entry_marking": 1,
			"late_entry_grace_period": 10,
			"enable_early_exit_marking": 1,
			"early_exit_grace_period": 10,
			"working_hours_calculation_based_on": "Every Valid Check-in and Check-out",
			"determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def _email(agent: dict) -> str:
	return f"{agent['first_name'].lower()}.{agent['last_name'].lower()}@staffpro.local"


def _username(agent: dict) -> str:
	return f"{agent['first_name'][:1]}{agent['last_name']}".replace(" ", "")


def _ensure_agent(
	agent: dict,
	*,
	company: str,
	client: str,
	campaign: str | None,
	department: str | None,
	designation: str | None,
	holiday_list: str | None,
	shift_type: str,
) -> tuple[str, bool]:
	email = _email(agent)
	existing = (
		frappe.db.get_value("Employee", {"company_email": email}, "name")
		or frappe.db.get_value("Employee", {"employee_name": f"{agent['first_name']} {agent['last_name']}"}, "name")
		or frappe.db.get_value("Employee", {"social_security_number": agent["social_security_number"]}, "name")
	)
	values = {
		"first_name": agent["first_name"],
		"last_name": agent["last_name"],
		"gender": agent["gender"],
		"date_of_birth": agent["date_of_birth"],
		"date_of_joining": agent["date_of_joining"],
		"company": company,
		"company_email": email,
		"prefered_contact_email": "Company Email",
		"prefered_email": email,
		"status": "Active",
		"employment_type": "Full-time" if frappe.db.exists("Employment Type", "Full-time") else None,
		"department": department,
		"designation": designation,
		"ctc": agent["ctc"],
		"social_security_number": agent["social_security_number"],
		"bill_to_customer": client,
		"default_shift": shift_type,
		"holiday_list": holiday_list,
		"overtime_threshold_hours": 90,
	}
	meta = frappe.get_meta("Employee")
	if campaign and meta.has_field("grade"):
		values["grade"] = campaign
	if meta.has_field("salary_currency"):
		values["salary_currency"] = "BZD"
	if meta.has_field("billing_currency"):
		values["billing_currency"] = "USD"
	values = {key: value for key, value in values.items() if value not in (None, "") and (meta.has_field(key) or key in {"first_name", "last_name"})}

	if existing:
		frappe.db.set_value("Employee", existing, values, update_modified=False)
		_ensure_username_on_employee(existing, agent, email)
		return existing, False

	user_id = _ensure_user(email, agent["first_name"], agent["last_name"], _username(agent))
	payload = {
		"doctype": "Employee",
		"naming_series": "HR-EMP-" if meta.has_field("naming_series") else None,
		"user_id": user_id,
		**values,
	}
	payload = {key: value for key, value in payload.items() if value not in (None, "")}
	doc = frappe.get_doc(payload)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name, True


def _ensure_user(email: str, first_name: str, last_name: str, username: str) -> str:
	existing = frappe.db.exists("User", email) or frappe.db.get_value("User", {"username": username}, "name")
	if existing:
		if not frappe.db.get_value("User", existing, "username"):
			frappe.db.set_value("User", existing, "username", username, update_modified=False)
		return existing
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"username": username,
			"send_welcome_email": 0,
			"enabled": 1,
		}
	)
	user.flags.ignore_permissions = True
	user.flags.ignore_password_policy = True
	user.user_type = "Website User"
	user.insert()
	roles = ["Employee"]
	if frappe.db.exists("Role", "Employee Self Service"):
		roles.append("Employee Self Service")
	user.add_roles(*roles)
	frappe.db.set_value("User", user.name, "user_type", "Website User", update_modified=False)
	return user.name


def _ensure_username_on_employee(employee: str, agent: dict, email: str) -> None:
	if not frappe.db.get_value("Employee", employee, "user_id"):
		user_id = _ensure_user(email, agent["first_name"], agent["last_name"], _username(agent))
		frappe.db.set_value("Employee", employee, "user_id", user_id, update_modified=False)


def _ensure_weekday_assignment(employee: str, company: str, shift_schedule: str, agent: dict) -> str | None:
	existing = frappe.db.get_value(
		"Shift Schedule Assignment",
		{"employee": employee, "shift_schedule": shift_schedule},
		"name",
	)
	if existing:
		doc = frappe.get_doc("Shift Schedule Assignment", existing)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Shift Schedule Assignment",
				"employee": employee,
				"company": company,
				"shift_schedule": shift_schedule,
				"shift_status": "Active",
				"enabled": 1,
				"create_shifts_after": agent["date_of_joining"],
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
	start = max(getdate(agent["date_of_joining"]), getdate(nowdate()))
	end = getdate(add_days(start, 90))
	if not frappe.db.exists(
		"Shift Assignment",
		{"employee": employee, "shift_schedule_assignment": doc.name, "docstatus": 1},
	):
		doc.create_shifts(start, end)
	return doc.name


def _next_saturday():
	today = getdate(nowdate())
	offset = (5 - today.weekday()) % 7
	if offset == 0 and today.weekday() != 5:
		offset = 6
	if today.weekday() == 5:
		return today
	return today + timedelta(days=offset)


def _assign_saturday_rotation(company: str, shifts: dict[str, str]) -> int:
	start = _next_saturday()
	created = 0
	employees = []
	for agent in AGENTS:
		name = (
			frappe.db.get_value("Employee", {"company_email": _email(agent)}, "name")
			or frappe.db.get_value("Employee", {"employee_name": f"{agent['first_name']} {agent['last_name']}"}, "name")
		)
		employees.append((name, shifts[agent["shift_label"]]))

	for week in range(SATURDAY_WEEKS):
		day = start + timedelta(days=7 * week)
		employee, shift_type = employees[week % len(employees)]
		if not employee:
			continue
		if getdate(day) < getdate(frappe.db.get_value("Employee", employee, "date_of_joining")):
			continue
		if frappe.db.exists(
			"Shift Assignment",
			{
				"employee": employee,
				"shift_type": shift_type,
				"start_date": day,
				"end_date": day,
				"docstatus": 1,
			},
		):
			continue
		create_shift_assignment(employee, company, shift_type, day, day, "Active")
		created += 1
	return created


def _assign_salary_structures(company: str, employees: list[str]) -> str | None:
	structure = (
		frappe.db.get_value(
			"Salary Structure",
			{"company": company, "docstatus": 1, "is_active": "Yes"},
			"name",
		)
		or frappe.db.get_value("Salary Structure", {"docstatus": 1, "is_active": "Yes"}, "name")
	)
	if not structure:
		return None
	currency = frappe.db.get_value("Company", company, "default_currency") or "BZD"
	for employee in employees:
		if frappe.db.exists(
			"Salary Structure Assignment",
			{"employee": employee, "docstatus": 1, "salary_structure": structure},
		):
			continue
		hour_rate = flt(frappe.db.get_value("Employee", employee, "ctc"))
		joining = frappe.db.get_value("Employee", employee, "date_of_joining") or nowdate()
		assignment = frappe.new_doc("Salary Structure Assignment")
		assignment.employee = employee
		assignment.salary_structure = structure
		assignment.company = company
		assignment.currency = currency
		assignment.from_date = joining
		if assignment.meta.has_field("base"):
			assignment.base = flt(hour_rate * 10 * 8, 2)
		assignment.flags.ignore_permissions = True
		assignment.insert()
		assignment.submit()
	return structure


def _comment_client(client: str) -> None:
	if frappe.db.exists(
		"Comment",
		{"reference_doctype": "Customer", "reference_name": client, "content": ["like", "%Saturdays rotate%"]},
	):
		return
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Customer",
			"reference_name": client,
			"content": LUNCH_NOTE,
		}
	).insert(ignore_permissions=True)


def _customer_group() -> str:
	for name in ("Commercial", "All Customer Groups", "Individual"):
		if frappe.db.exists("Customer Group", name):
			return name
	return frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "All Customer Groups"


def _territory() -> str:
	for name in ("All Territories", "Belize", "Rest Of The World"):
		if frappe.db.exists("Territory", name):
			return name
	return frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
