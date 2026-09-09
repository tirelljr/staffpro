# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Guest clock-in / username helpers for the Staff Pro login kiosk."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime, time_diff_in_hours

from hrms.hr.agent_access import best_client_ipv4, normalize_ipv4, validate_agent_clockin_ip
from hrms.overrides.employee_master import resolve_user_from_login


def _request_ip(reported: str | None = None) -> str:
	return best_client_ipv4(reported)


def _employee_cubicle(employee: str | None) -> dict | None:
	if not employee or not frappe.db.table_exists("Cubicle"):
		return None
	return frappe.db.get_value(
		"Cubicle",
		{"employee": employee},
		["name", "device_id", "ip_address"],
		as_dict=True,
	)


def _cubicle_for_ip(ip: str | None) -> dict | None:
	address = normalize_ipv4(ip)
	if not address or not frappe.db.table_exists("Cubicle"):
		return None
	return frappe.db.get_value(
		"Cubicle",
		{"ip_address": address},
		["name", "device_id", "employee"],
		as_dict=True,
	)


def _login_device_id(employee: str | None) -> str:
	if not employee or not frappe.get_meta("Employee").has_field("login_device_id"):
		return ""
	return (frappe.db.get_value("Employee", employee, "login_device_id") or "").strip()


def resolve_workstation_device(
	employee: str | None = None,
	client_ip: str | None = None,
	fallback: str | None = None,
) -> str:
	"""Prefer the cubicle Device ID, then the registered login device, then a fallback."""
	if employee:
		cubicle = _employee_cubicle(employee)
		if cubicle and (cubicle.device_id or "").strip():
			return cubicle.device_id.strip()[:140]
		registered = _login_device_id(employee)
		if registered:
			return registered[:140]
	cubicle = _cubicle_for_ip(client_ip)
	if cubicle and (cubicle.device_id or "").strip():
		return cubicle.device_id.strip()[:140]
	return (fallback or "").strip()[:140]


def bind_cubicle_device(employee: str | None, device_id: str | None) -> str:
	"""Write the real device ID onto the agent's assigned cubicle when it is empty."""
	device = (device_id or "").strip()[:140]
	if not employee or not device:
		return ""
	cubicle = _employee_cubicle(employee)
	if not cubicle:
		return ""
	current = (cubicle.device_id or "").strip()
	if current:
		return current
	frappe.db.set_value("Cubicle", cubicle.name, "device_id", device, update_modified=False)
	return device


def _default_company() -> dict:
	company = frappe.defaults.get_global_default("company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	if not company and frappe.db.exists("DocType", "Company"):
		company = frappe.db.get_value("Company", {}, "name")
	return {"company_id": company or "", "company_name": company or "Staff Pro"}


@frappe.whitelist(allow_guest=True)
def get_kiosk_context(client_ip: str | None = None) -> dict:
	company = _default_company()
	ip = _request_ip(client_ip)
	return {
		"ip": ip,
		"device_id": resolve_workstation_device(client_ip=ip),
		"company_id": company["company_id"],
		"company_name": company["company_name"] or "Staff Pro",
		"allow_geolocation_tracking": cint(
			frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking")
		),
	}


def _find_user(login: str) -> str:
	user = resolve_user_from_login(login)
	if not user or user in {"Guest", "Administrator"}:
		frappe.throw(_("Invalid username or password"))
	enabled = frappe.db.get_value("User", user, "enabled")
	if not enabled:
		frappe.throw(_("Invalid username or password"))
	return user


def _authenticate(username: str, password: str) -> str:
	from frappe.utils.password import check_password

	user = _find_user(username)
	try:
		check_password(user, password)
	except frappe.AuthenticationError:
		frappe.throw(_("Invalid username or password"))
	return user


def _employee_for_user(user: str) -> dict:
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["name", "employee_name", "first_name", "company"],
		as_dict=True,
	)
	if not employee:
		frappe.throw(_("No active employee is linked to this username."))
	return employee


def _format_clock(value) -> str:
	if not value:
		return ""
	dt = get_datetime(value)
	return dt.strftime("%I:%M %p").lstrip("0")


def _hours_label(hours: float) -> str:
	total_minutes = int(round(max(flt(hours), 0) * 60))
	return f"{total_minutes // 60}h {total_minutes % 60}m"


def _pair_label(start, end) -> str:
	if not start or not end:
		return ""
	start_dt = get_datetime(start)
	end_dt = get_datetime(end)
	hours = max(flt(time_diff_in_hours(end_dt, start_dt)), 0)
	return f"{_format_clock(start_dt)} - {_format_clock(end_dt)} ({_hours_label(hours)})"


def _session_label(pair: dict) -> str:
	if pair.get("open"):
		return f"{_format_clock(pair['in_time'])} -" if pair.get("in_time") else ""
	return _pair_label(pair.get("in_time"), pair.get("out_time"))


def _pair_today_logs(logs: list) -> list[dict]:
	pairs: list[dict] = []
	pending_in = None
	for row in logs:
		if row.log_type == "IN":
			if pending_in is None:
				pending_in = row
			continue
		if row.log_type == "OUT" and pending_in is not None:
			pairs.append({"in_time": pending_in.time, "out_time": row.time, "open": False})
			pending_in = None
	if pending_in is not None:
		pairs.append({"in_time": pending_in.time, "out_time": None, "open": True})
	return pairs


def _is_today_session(pair: dict, today) -> bool:
	in_dt = get_datetime(pair.get("in_time")) if pair.get("in_time") else None
	out_dt = get_datetime(pair.get("out_time")) if pair.get("out_time") else None
	if pair.get("open") and in_dt:
		return True
	return bool((in_dt and getdate(in_dt) == today) or (out_dt and getdate(out_dt) == today))


def _checkin_summary(employee: str) -> dict:
	today = getdate()
	logs = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": [">=", get_datetime(f"{add_days(today, -1)} 00:00:00")]},
		fields=["log_type", "time"],
		order_by="time asc",
		ignore_permissions=True,
	)
	pairs = _pair_today_logs(logs)
	today_pairs = [pair for pair in pairs if _is_today_session(pair, today)]
	today_labels = []
	for pair in reversed(today_pairs):
		label = _session_label(pair)
		if label:
			today_labels.append(label)

	last = logs[-1] if logs else None
	next_action = "OUT" if last and last.log_type == "IN" else "IN"
	open_pair = next((pair for pair in reversed(today_pairs) if pair.get("open")), None)
	completed = [pair for pair in reversed(today_pairs) if not pair.get("open")]
	last_in = next((row for row in reversed(logs) if row.log_type == "IN"), None)
	worked = sum(
		max(flt(time_diff_in_hours(get_datetime(pair["out_time"]), get_datetime(pair["in_time"]))), 0)
		for pair in today_pairs
		if not pair.get("open") and pair.get("in_time") and pair.get("out_time")
	)

	return {
		"next_action": next_action,
		"last_in": last_in.time if last_in else None,
		"last_in_label": _session_label(open_pair) if open_pair else "",
		"last_pair_label": _session_label(completed[0]) if completed else "",
		"today_labels": today_labels,
		"today_hours_label": _hours_label(worked) if today_pairs else "",
		"employee_name": frappe.db.get_value("Employee", employee, "employee_name") or "",
	}


def _profile(employee: dict, username: str, client_ip: str | None = None) -> dict:
	summary = _checkin_summary(employee.name)
	summary.update(
		{
			"username": username,
			"employee": employee.name,
			"employee_name": employee.employee_name or "",
			"company": employee.company or "",
			"device_id": resolve_workstation_device(employee.name, client_ip),
		}
	)
	return summary


@frappe.whitelist(allow_guest=True)
def get_kiosk_profile(username: str | None = None, client_ip: str | None = None) -> dict:
	"""Return an employee's name and last punch times without starting a session."""
	login = (username or "").strip()
	if not login:
		return {}

	user = resolve_user_from_login(login)
	if not user or user in {"Guest", "Administrator"}:
		return {}
	if not frappe.db.get_value("User", user, "enabled"):
		return {}

	employee = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["name", "employee_name", "first_name", "company"],
		as_dict=True,
	)
	if not employee:
		return {}

	return _profile(employee, frappe.db.get_value("User", user, "username") or login, _request_ip(client_ip))


@frappe.whitelist(allow_guest=True)
def clock(
	username: str,
	password: str,
	log_type: str | None = None,
	latitude: str | float | None = None,
	longitude: str | float | None = None,
	device_id: str | None = None,
	client_ip: str | None = None,
) -> dict:
	"""Authenticate with a username and create an Employee Checkin without keeping a session."""
	if not (username or "").strip() or not password:
		frappe.throw(_("Username and password are required."))

	user = _authenticate(username, password)
	employee = _employee_for_user(user)
	validate_agent_clockin_ip(employee.name, ignore_session_exemption=True, client_ip=client_ip)
	summary = _checkin_summary(employee.name)
	action = (log_type or "").strip().upper() or summary["next_action"]
	if action not in {"IN", "OUT"}:
		frappe.throw(_("Invalid clock action."))

	ip = _request_ip(client_ip)
	workstation_id = resolve_workstation_device(employee.name, ip, device_id)
	if not workstation_id:
		workstation_id = (device_id or "").strip()[:140]
	bound = bind_cubicle_device(employee.name, workstation_id)
	workstation_id = bound or workstation_id

	doc = frappe.new_doc("Employee Checkin")
	doc.employee = employee.name
	doc.employee_name = employee.employee_name
	doc.time = now_datetime().replace(microsecond=0)
	doc.log_type = action
	doc.device_id = workstation_id or None
	if latitude not in (None, ""):
		doc.latitude = flt(latitude)
	if longitude not in (None, ""):
		doc.longitude = flt(longitude)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)

	profile = _profile(employee, frappe.db.get_value("User", user, "username") or username, ip)
	profile.update(
		{
			"log_type": action,
			"time": doc.time,
			"time_label": _format_clock(doc.time),
			"checkin": doc.name,
			"device_id": workstation_id or profile.get("device_id") or "",
		}
	)
	return profile


@frappe.whitelist(allow_guest=True)
def resolve_login(username: str | None = None) -> str:
	"""Map a typed username or email to the User name Frappe login expects."""
	return resolve_user_from_login(username) or (username or "").strip()


@frappe.whitelist(allow_guest=True)
def send_password_reset(username: str) -> dict:
	"""Send a password reset email for a username or email address."""
	login = (username or "").strip()
	if not login:
		frappe.throw(_("Please enter your username."))

	user = resolve_user_from_login(login)
	if not user or user in {"Guest", "Administrator"}:
		# Same response whether the user exists or not.
		return {"ok": True}

	user_doc = frappe.get_doc("User", user)
	if not user_doc.enabled or not user_doc.email:
		return {"ok": True}

	user_doc.reset_password(send_email=True)
	return {"ok": True}
