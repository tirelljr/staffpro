# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Office IPv4 clock-in lock and registered-device login lock for agents."""

from __future__ import annotations

import ipaddress
import re

import frappe
from frappe import _
from frappe.utils import cint

_SPLIT_IPS = re.compile(r"[\s,;]+")


def request_ipv4() -> str:
	try:
		raw = frappe.local.request_ip or ""
	except Exception:
		raw = ""
	return normalize_ipv4(raw)


def normalize_ipv4(value: str | None) -> str:
	if not value:
		return ""
	text = str(value).strip()
	if "," in text:
		text = text.split(",", 1)[0].strip()
	if text.startswith("::ffff:"):
		text = text[7:]
	try:
		ip = ipaddress.ip_address(text)
	except ValueError:
		return ""
	if ip.version != 4:
		return ""
	return str(ip)


def parse_office_ipv4s(raw: str | None) -> list[str]:
	if not raw:
		return []
	found: list[str] = []
	for token in _SPLIT_IPS.split(str(raw).strip()):
		ip = normalize_ipv4(token)
		if ip and ip not in found:
			found.append(ip)
	return found


def _system_setting(fieldname: str, default=None):
	if not frappe.db.exists("DocType", "System Settings"):
		return default
	if not frappe.get_meta("System Settings").has_field(fieldname):
		return default
	return frappe.db.get_single_value("System Settings", fieldname)


def get_allowed_office_ips() -> list[str]:
	if not cint(_system_setting("restrict_agent_clockin_to_office_ip", 0)):
		return []
	return parse_office_ipv4s(_system_setting("office_clockin_ipv4", ""))


def is_login_device_restricted() -> bool:
	return bool(cint(_system_setting("restrict_agent_login_to_device", 0)))


def is_agent_access_exempt(user: str | None = None) -> bool:
	from hrms.boot import is_staff_pro_desk_admin

	user = user or getattr(frappe.session, "user", None)
	if not user or user == "Guest":
		return False
	if user == "Administrator":
		return True
	return bool(is_staff_pro_desk_admin(user))


def validate_agent_clockin_ip(employee: str | None = None, *, ignore_session_exemption: bool = False):
	allowed = get_allowed_office_ips()
	if not allowed:
		return

	if not ignore_session_exemption:
		user = getattr(frappe.session, "user", None)
		if user and is_agent_access_exempt(user):
			return

	current = request_ipv4()
	if current in allowed:
		return

	frappe.throw(_("You can only clock in from the office network."))


def _employee_for_user(user: str) -> str | None:
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def validate_or_bind_login_device(user: str | None, device_id: str | None = None):
	if not is_login_device_restricted():
		return
	if not user or user in {"Guest", "Administrator"}:
		return
	if is_agent_access_exempt(user):
		return

	if not frappe.get_meta("Employee").has_field("login_device_id"):
		return

	employee = _employee_for_user(user)
	if not employee:
		return

	device = (device_id or frappe.form_dict.get("device_id") or "").strip()
	registered = (frappe.db.get_value("Employee", employee, "login_device_id") or "").strip()
	if not registered:
		if not device:
			frappe.throw(_("This account can only be used from a registered device."))
		frappe.db.set_value("Employee", employee, "login_device_id", device[:140], update_modified=False)
		return

	if device != registered:
		frappe.throw(_("This account can only be used from the registered device."))


def is_scannable_private_ipv4(value: str | None) -> bool:
	ip = normalize_ipv4(value)
	if not ip:
		return False
	addr = ipaddress.ip_address(ip)
	return bool(addr.is_private and not addr.is_loopback and not addr.is_link_local)


def office_default_ipv4() -> str:
	ips = parse_office_ipv4s(_system_setting("office_clockin_ipv4", ""))
	return ips[0] if ips else ""


def apply_office_ipv4_defaults(raw: str | None = None) -> dict:
	"""Set the first Office IPv4 as every active agent's default IP."""
	ips = parse_office_ipv4s(raw if raw is not None else _system_setting("office_clockin_ipv4", ""))
	if not ips:
		return {"default_ip": "", "employees": 0, "cubicles": 0}

	default_ip = ips[0]
	employees_updated = 0
	if frappe.get_meta("Employee").has_field("default_ipv4"):
		names = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
		for name in names:
			current = (frappe.db.get_value("Employee", name, "default_ipv4") or "").strip()
			if current == default_ip:
				continue
			frappe.db.set_value("Employee", name, "default_ipv4", default_ip, update_modified=False)
			employees_updated += 1

	cubicles_updated = 0
	if frappe.db.table_exists("Cubicle"):
		for name, ip_address in frappe.get_all("Cubicle", fields=["name", "ip_address"], as_list=True):
			if (ip_address or "").strip():
				continue
			frappe.db.set_value("Cubicle", name, "ip_address", default_ip, update_modified=False)
			cubicles_updated += 1

	return {"default_ip": default_ip, "employees": employees_updated, "cubicles": cubicles_updated}


def apply_office_ipv4_defaults_on_settings(doc, method=None):
	if not cint(getattr(doc, "restrict_agent_clockin_to_office_ip", 0)):
		return
	apply_office_ipv4_defaults(getattr(doc, "office_clockin_ipv4", ""))


def _unique_ips(values) -> list[str]:
	found: list[str] = []
	for value in values:
		ip = normalize_ipv4(value)
		if ip and ip not in found:
			found.append(ip)
	return found


def _local_ipv4s() -> list[str]:
	import socket

	found: list[str] = []
	try:
		for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
			found.append(info[4][0])
	except OSError:
		pass
	try:
		probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		probe.connect(("10.255.255.255", 1))
		found.append(probe.getsockname()[0])
		probe.close()
	except OSError:
		pass
	return [ip for ip in _unique_ips(found) if is_scannable_private_ipv4(ip)]


def _arp_ipv4s() -> list[str]:
	import os

	found: list[str] = []
	arp_path = "/proc/net/arp"
	if os.path.exists(arp_path):
		try:
			with open(arp_path, encoding="utf-8") as handle:
				next(handle, None)
				for line in handle:
					token = (line.split() or [""])[0]
					if is_scannable_private_ipv4(token):
						found.append(token)
		except OSError:
			pass
	return _unique_ips(found)


def _subnets_to_scan(seed_ip: str | None) -> list:
	networks = []
	seen = set()
	candidates = []
	if is_scannable_private_ipv4(seed_ip):
		candidates.append(seed_ip)
	candidates.extend(_local_ipv4s())
	for ip in candidates:
		network = ipaddress.ip_network(f"{ip}/24", strict=False)
		key = str(network)
		if key in seen or network.num_addresses > 256:
			continue
		seen.add(key)
		networks.append(network)
		if len(networks) >= 2:
			break
	return networks


def _host_is_reachable(ip: str, timeout: float = 0.2) -> bool:
	import socket
	import subprocess

	for port in (445, 139, 80, 443, 22):
		try:
			with socket.create_connection((str(ip), port), timeout=timeout):
				return True
		except ConnectionRefusedError:
			return True
		except OSError:
			continue

	try:
		completed = subprocess.run(
			["ping", "-c", "1", "-W", "1", str(ip)],
			capture_output=True,
			timeout=2,
			check=False,
		)
		return completed.returncode == 0
	except (OSError, subprocess.TimeoutExpired):
		return False


def _sweep_private_subnet(network) -> list[str]:
	from concurrent.futures import ThreadPoolExecutor, as_completed

	hosts = [str(host) for host in network.hosts()]
	live: list[str] = []
	with ThreadPoolExecutor(max_workers=64) as pool:
		futures = {pool.submit(_host_is_reachable, host): host for host in hosts}
		for future in as_completed(futures):
			host = futures[future]
			try:
				if future.result():
					live.append(host)
			except Exception:
				continue
	return sorted(live, key=lambda value: ipaddress.ip_address(value))


def discover_office_ipv4s(seed_ip: str | None = None) -> list[str]:
	"""Discover live private IPv4 hosts on the office LAN the server can see."""
	seed = normalize_ipv4(seed_ip) or request_ipv4()
	found = []
	if seed:
		found.append(seed)
	found.extend(_local_ipv4s())
	found.extend(_arp_ipv4s())

	if not getattr(frappe.flags, "in_test", False):
		for network in _subnets_to_scan(seed):
			found.extend(_sweep_private_subnet(network))

	return _unique_ips(found)


@frappe.whitelist()
def scan_office_ipv4() -> dict:
	frappe.only_for(["System Manager", "Administrator", "HR Manager"])
	ips = discover_office_ipv4s()
	if not ips:
		frappe.throw(_("Could not detect IPv4 addresses on the office network."))

	applied = apply_office_ipv4_defaults("\n".join(ips))
	return {
		"ip": ips[0],
		"ips": ips,
		"count": len(ips),
		"default_ip": applied["default_ip"],
		"employees": applied["employees"],
		"cubicles": applied["cubicles"],
	}
