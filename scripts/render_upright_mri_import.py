"""Import Upright MRI onto the Render Staff Pro site via the Frappe API."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from http.cookiejar import MozillaCookieJar
from pathlib import Path

BASE = "https://staffpro-0rcm.onrender.com"
COOKIE_PATH = Path.home() / "AppData" / "Local" / "Temp" / "sp-cookies.txt"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
SATURDAY_WEEKS = 26

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


def email_for(agent: dict) -> str:
	return f"{agent['first_name'].lower()}.{agent['last_name'].lower()}@staffpro.local"


def username_for(agent: dict) -> str:
	return f"{agent['first_name'][:1]}{agent['last_name']}".replace(" ", "")


class Site:
	def __init__(self):
		self.jar = MozillaCookieJar(str(COOKIE_PATH))
		self.jar.load(ignore_discard=True, ignore_expires=True)
		self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

	def call(self, method: str, **kwargs):
		payload = json.dumps(kwargs).encode()
		req = urllib.request.Request(
			f"{BASE}/api/method/{method}",
			data=payload,
			headers={"Content-Type": "application/json", "Accept": "application/json"},
			method="POST",
		)
		try:
			with self.opener.open(req, timeout=60) as resp:
				body = json.loads(resp.read().decode())
		except urllib.error.HTTPError as exc:
			detail = exc.read().decode(errors="replace")
			raise RuntimeError(f"{method} failed {exc.code}: {detail[:800]}") from exc
		if "exc_type" in body and body.get("exc_type"):
			raise RuntimeError(f"{method} error: {body}")
		return body.get("message", body)

	def get_list(self, doctype: str, filters=None, fields=None, limit=20):
		return (
			self.call(
				"frappe.client.get_list",
				doctype=doctype,
				filters=filters or {},
				fields=fields or ["name"],
				limit_page_length=limit,
			)
			or []
		)

	def get_value(self, doctype: str, filters, fieldname="name"):
		result = self.call("frappe.client.get_value", doctype=doctype, filters=filters, fieldname=fieldname)
		if isinstance(result, dict):
			return result.get(fieldname) or result.get("name")
		return result

	def exists(self, doctype: str, name: str) -> bool:
		return bool(self.call("frappe.client.get_value", doctype=doctype, filters={"name": name}, fieldname="name"))

	def insert(self, doc: dict) -> dict:
		return self.call("frappe.client.insert", doc=doc)

	def set_value(self, doctype: str, name: str, fieldname, value=None):
		if isinstance(fieldname, dict):
			return self.call("frappe.client.set_value", doctype=doctype, name=name, fieldname=fieldname)
		return self.call("frappe.client.set_value", doctype=doctype, name=name, fieldname=fieldname, value=value)

	def submit(self, doc: dict) -> dict:
		return self.call("frappe.client.submit", doc=doc)


def first_name(rows, key="name"):
	return rows[0][key] if rows else None


def next_saturday(today: date) -> date:
	offset = (5 - today.weekday()) % 7
	return today if today.weekday() == 5 else today + timedelta(days=offset)


def monday_of(day: date) -> date:
	return day - timedelta(days=day.weekday())


def _ensure_weekday_blocks(site: Site, employee: str, company: str, shift_type: str, agent: dict) -> int:
	start = max(date.fromisoformat(agent["date_of_joining"]), date.today())
	created = 0
	week_start = monday_of(start)
	for _ in range(13):
		block_start = max(week_start, start)
		block_end = week_start + timedelta(days=4)
		if block_start.weekday() > 4:
			week_start += timedelta(days=7)
			continue
		if site.get_list(
			"Shift Assignment",
			{
				"employee": employee,
				"shift_type": shift_type,
				"start_date": block_start.isoformat(),
				"end_date": block_end.isoformat(),
				"docstatus": 1,
			},
			["name"],
		):
			week_start += timedelta(days=7)
			continue
		doc = site.insert(
			{
				"doctype": "Shift Assignment",
				"employee": employee,
				"company": company,
				"shift_type": shift_type,
				"start_date": block_start.isoformat(),
				"end_date": block_end.isoformat(),
				"status": "Active",
			}
		)
		site.submit(doc)
		created += 1
		week_start += timedelta(days=7)
	return created


def main():
	site = Site()
	company = (
		site.get_value("Global Defaults", "Global Defaults", "default_company")
		or first_name(site.get_list("Company"))
	)
	customer_group = first_name(site.get_list("Customer Group", {"is_group": 0})) or "Commercial"
	territory = first_name(site.get_list("Territory", {"is_group": 0})) or "All Territories"
	holiday = (
		site.get_value("Company", company, "default_holiday_list")
		or first_name(site.get_list("Holiday List"))
	)
	department = first_name(site.get_list("Department", {"department_name": "Operations"})) or first_name(
		site.get_list("Department", {"is_group": 0})
	)
	designation = first_name(site.get_list("Designation", {"name": "Agent"})) or first_name(
		site.get_list("Designation", {"name": "Customer Service Representative"})
	) or first_name(site.get_list("Designation"))
	structure = first_name(
		site.get_list("Salary Structure", {"docstatus": 1, "is_active": "Yes", "company": company})
	) or first_name(site.get_list("Salary Structure", {"docstatus": 1, "is_active": "Yes"}))
	print("context", {"company": company, "department": department, "designation": designation, "structure": structure})

	if site.exists("Customer", "Upright MRI"):
		site.set_value("Customer", "Upright MRI", {"campaign_name": "Upright MRI", "contracted_seats": 5, "service_type": "Back Office"})
		client = "Upright MRI"
	else:
		client = site.insert(
			{
				"doctype": "Customer",
				"customer_name": "Upright MRI",
				"customer_type": "Company",
				"customer_group": customer_group,
				"territory": territory,
				"campaign_name": "Upright MRI",
				"service_type": "Back Office",
				"contracted_seats": 5,
				"billing_currency": "USD",
			}
		)["name"]
	print("client", client)

	if not site.exists("Employee Grade", "Upright MRI"):
		site.insert({"doctype": "Employee Grade", "name": "Upright MRI", "grade_name": "Upright MRI"})
	print("campaign", "Upright MRI")

	shifts = {}
	schedules = {}
	for agent in AGENTS:
		label = agent["shift_label"]
		if label in shifts:
			continue
		if site.exists("Shift Type", label):
			site.set_value("Shift Type", label, {"start_time": agent["start_time"], "end_time": agent["end_time"]})
			shifts[label] = label
		else:
			shifts[label] = site.insert(
				{
					"doctype": "Shift Type",
					"name": label,
					"start_time": agent["start_time"],
					"end_time": agent["end_time"],
					"holiday_list": holiday,
					"enable_late_entry_marking": 1,
					"late_entry_grace_period": 10,
					"enable_early_exit_marking": 1,
					"early_exit_grace_period": 10,
					"working_hours_calculation_based_on": "Every Valid Check-in and Check-out",
					"determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
				}
			)["name"]
		existing_schedules = site.get_list(
			"Shift Schedule",
			{"shift_type": shifts[label], "frequency": "Every Week", "docstatus": 1},
			["name"],
			limit=5,
		)
		if existing_schedules:
			schedules[label] = existing_schedules[0]["name"]
		else:
			doc = site.insert(
				{
					"doctype": "Shift Schedule",
					"name": f"{label} Weekdays",
					"shift_type": shifts[label],
					"frequency": "Every Week",
					"repeat_on_days": [{"day": day} for day in WEEKDAYS],
				}
			)
			submitted = site.submit(doc)
			schedules[label] = submitted["name"] if isinstance(submitted, dict) else doc["name"]
	print("shifts", shifts)

	created = []
	for agent in AGENTS:
		mail = email_for(agent)
		existing = (
			site.get_value("Employee", {"company_email": mail})
			or site.get_value("Employee", {"employee_name": f"{agent['first_name']} {agent['last_name']}"})
		)
		payload = {
			"doctype": "Employee",
			"first_name": agent["first_name"],
			"last_name": agent["last_name"],
			"gender": agent["gender"],
			"date_of_birth": agent["date_of_birth"],
			"date_of_joining": agent["date_of_joining"],
			"company": company,
			"company_email": mail,
			"prefered_contact_email": "Company Email",
			"prefered_email": mail,
			"status": "Active",
			"employment_type": "Full-time",
			"department": department,
			"designation": designation,
			"ctc": agent["ctc"],
			"social_security_number": agent["social_security_number"],
			"bill_to_customer": client,
			"default_shift": shifts[agent["shift_label"]],
			"holiday_list": holiday,
			"grade": "Upright MRI",
			"salary_currency": "BZD",
			"billing_currency": "USD",
			"overtime_threshold_hours": 90,
			"user_id": mail,
		}
		if existing:
			site.set_value("Employee", existing, {k: v for k, v in payload.items() if k != "doctype"})
			name = existing
		else:
			if not site.exists("User", mail):
				user = site.insert(
					{
						"doctype": "User",
						"email": mail,
						"first_name": agent["first_name"],
						"last_name": agent["last_name"],
						"username": username_for(agent),
						"send_welcome_email": 0,
						"enabled": 1,
					}
				)
				print("user", user["name"])
			name = site.insert(payload)["name"]
		created.append(name)
		print("agent", name)

		if not site.get_list("Shift Schedule Assignment", {"employee": name, "shift_schedule": schedules[agent["shift_label"]]}, ["name"]):
			site.insert(
				{
					"doctype": "Shift Schedule Assignment",
					"employee": name,
					"company": company,
					"shift_schedule": schedules[agent["shift_label"]],
					"shift_status": "Active",
					"enabled": 1,
					"create_shifts_after": agent["date_of_joining"],
				}
			)
		_ensure_weekday_blocks(site, name, company, shifts[agent["shift_label"]], agent)

		if structure and not site.get_list(
			"Salary Structure Assignment",
			{"employee": name, "docstatus": 1, "salary_structure": structure},
			["name"],
		):
			ssa = site.insert(
				{
					"doctype": "Salary Structure Assignment",
					"employee": name,
					"salary_structure": structure,
					"company": company,
					"currency": "BZD",
					"from_date": agent["date_of_joining"],
					"base": agent["ctc"] * 10 * 8,
				}
			)
			site.submit(ssa)

	start = next_saturday(date.today())
	sat_count = 0
	for week in range(SATURDAY_WEEKS):
		day = start + timedelta(days=7 * week)
		agent = AGENTS[week % len(AGENTS)]
		employee = site.get_value("Employee", {"company_email": email_for(agent)})
		if not employee:
			continue
		if day < date.fromisoformat(agent["date_of_joining"]):
			continue
		if site.get_list(
			"Shift Assignment",
			{
				"employee": employee,
				"shift_type": shifts[agent["shift_label"]],
				"start_date": day.isoformat(),
				"end_date": day.isoformat(),
				"docstatus": 1,
			},
			["name"],
		):
			continue
		doc = site.insert(
			{
				"doctype": "Shift Assignment",
				"employee": employee,
				"company": company,
				"shift_type": shifts[agent["shift_label"]],
				"start_date": day.isoformat(),
				"end_date": day.isoformat(),
				"status": "Active",
			}
		)
		site.submit(doc)
		sat_count += 1
	print("done", {"agents": created, "saturday_assignments": sat_count, "client": client})


if __name__ == "__main__":
	main()
