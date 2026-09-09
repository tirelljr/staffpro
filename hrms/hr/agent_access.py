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
_FORWARD_HEADERS = (
	"CF-Connecting-IP",
	"True-Client-IP",
	"X-Real-IP",
	"X-Forwarded-For",
	"X-Client-IP",
	"Fastly-Client-IP",
	"Forwarded",
)


def request_ipv4() -> str:
	try:
		raw = frappe.local.request_ip or ""
	except Exception:
		raw = ""
	return normalize_ipv4(raw)


def normalize_ipv4(value: str | None) -> str:
	if not value:
		return ""
	text = str(value).strip().strip('"').strip("[]")
	if text.lower().startswith("for="):
		text = text[4:].strip().strip('"').strip("[]")
	if "," in text:
		text = text.split(",", 1)[0].strip()
	if text.startswith("::ffff:"):
		text = text[7:]
	if ":" in text and text.count(":") == 1:
		host, port = text.rsplit(":", 1)
		if port.isdigit():
			text = host
	try:
		ip = ipaddress.ip_address(text)
	except ValueError:
		return ""
	if ip.version != 4:
		return ""
	return str(ip)


def is_container_peer_ipv4(value: str | None) -> bool:
	"""True when the TCP peer is Docker/loopback, not the browser's address."""
	ip = normalize_ipv4(value)
	if not ip:
		return True
	addr = ipaddress.ip_address(ip)
	if addr.is_loopback or addr.is_link_local or addr.is_unspecified:
		return True
	parts = [int(part) for part in ip.split(".")]
	# docker0 (172.17.0.0/16) and default compose networks (172.18-31.x).
	return parts[0] == 172 and 17 <= parts[1] <= 31


def _header_value(name: str) -> str:
	try:
		value = frappe.get_request_header(name)
	except Exception:
		value = None
	if value:
		return str(value)
	try:
		headers = getattr(getattr(frappe.local, "request", None), "headers", None) or {}
		return str(headers.get(name) or headers.get(name.lower()) or "")
	except Exception:
		return ""


def _header_ipv4s() -> list[str]:
	found: list[str] = []
	for name in _FORWARD_HEADERS:
		raw = _header_value(name)
		if not raw:
			continue
		for token in raw.split(","):
			ip = normalize_ipv4(token)
			if ip and ip not in found:
				found.append(ip)
	return found


def request_ipv4s() -> list[str]:
	found = _header_ipv4s()
	peer = request_ipv4()
	if peer and peer not in found:
		found.append(peer)
	return found


def best_client_ipv4(reported: str | None = None) -> str:
	"""Browser IPv4: public forwarded address, then LAN, then a scanned client IP."""
	candidates = request_ipv4s()
	reported_ip = normalize_ipv4(reported)
	public = [ip for ip in candidates if not ipaddress.ip_address(ip).is_private]
	if public:
		return public[0]
	lan = [ip for ip in candidates if not is_container_peer_ipv4(ip)]
	if lan:
		return lan[0]
	if reported_ip:
		return reported_ip
	return candidates[0] if candidates else ""


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


def get_clockin_ip_status(
	*,
	ignore_session_exemption: bool = False,
	client_ip: str | None = None,
) -> dict:
	"""Whether office-IP restriction is on and whether this request may punch."""
	allowed_ips = get_allowed_office_ips()
	if not allowed_ips:
		return {"restricted": False, "allowed": True}

	if not ignore_session_exemption:
		user = getattr(frappe.session, "user", None)
		if user and is_agent_access_exempt(user):
			return {"restricted": True, "allowed": True}

	current = best_client_ipv4(client_ip)
	return {"restricted": True, "allowed": current in allowed_ips}


def is_office_clockin_ip_allowed(
	*,
	ignore_session_exemption: bool = False,
	client_ip: str | None = None,
) -> bool:
	return bool(
		get_clockin_ip_status(
			ignore_session_exemption=ignore_session_exemption,
			client_ip=client_ip,
		)["allowed"]
	)


def validate_agent_clockin_ip(
	employee: str | None = None,
	*,
	ignore_session_exemption: bool = False,
	client_ip: str | None = None,
):
	status = get_clockin_ip_status(
		ignore_session_exemption=ignore_session_exemption,
		client_ip=client_ip,
	)
	if status["allowed"]:
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


def _arp_cache_ipv4s() -> list[str]:
	import os
	import subprocess
	import sys

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

	try:
		completed = subprocess.run(
			["arp", "-a"] if sys.platform == "win32" else ["ip", "neigh"],
			capture_output=True,
			text=True,
			timeout=5,
			check=False,
		)
		for token in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", completed.stdout or ""):
			if is_scannable_private_ipv4(token):
				found.append(token)
	except (OSError, subprocess.TimeoutExpired):
		pass
	return _unique_ips(found)


def _ping_command(ip: str) -> list[str]:
	import sys

	if sys.platform == "win32":
		return ["ping", "-n", "1", "-w", "200", str(ip)]
	return ["ping", "-c", "1", "-W", "1", str(ip)]


def _scapy_iface_for_network(network):
	try:
		from scapy.all import get_if_addr, get_if_list
	except ImportError:
		return None

	for iface in get_if_list():
		try:
			addr = get_if_addr(iface)
		except Exception:
			continue
		try:
			if addr and ipaddress.ip_address(addr) in network:
				return iface
		except ValueError:
			continue
	return None


def _scapy_arp_scan(network) -> list[str]:
	"""Layer-2 ARP who-has sweep of a local /24. Requires raw sockets / Npcap."""
	try:
		from scapy.all import ARP, Ether, srp
	except ImportError:
		return []

	kwargs = {"timeout": 3, "verbose": False, "retry": 1}
	iface = _scapy_iface_for_network(network)
	if iface:
		kwargs["iface"] = iface

	try:
		packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=str(network))
		answered, _ = srp(packet, **kwargs)
	except Exception:
		frappe.logger("hrms").warning("BPO IPv4 ARP scan failed on %s", network)
		return []

	found = []
	for _sent, received in answered:
		try:
			ip = received[ARP].psrc
		except (IndexError, AttributeError):
			continue
		if is_scannable_private_ipv4(ip):
			found.append(ip)
	return _unique_ips(found)


def _scapy_icmp_sweep(network) -> list[str]:
	"""ICMP echo sweep for live hosts on a private /24."""
	try:
		from scapy.all import ICMP, IP, sr
	except ImportError:
		return []

	targets = [str(host) for host in network.hosts()]
	kwargs = {"timeout": 2, "verbose": False}
	iface = _scapy_iface_for_network(network)
	if iface:
		kwargs["iface"] = iface

	try:
		packets = [IP(dst=ip) / ICMP() for ip in targets]
		answered, _ = sr(packets, **kwargs)
	except Exception:
		frappe.logger("hrms").warning("BPO IPv4 ICMP sweep failed on %s", network)
		return []

	found = []
	for _sent, received in answered:
		try:
			if ICMP not in received or received[ICMP].type != 0:
				continue
			ip = received[IP].src
		except (IndexError, AttributeError):
			continue
		if is_scannable_private_ipv4(ip):
			found.append(ip)
	return _unique_ips(found)


def _scan_live_hosts(network) -> tuple[list[str], list[str]]:
	"""Discover live private hosts: ARP, then ICMP, then TCP/ping fallback."""
	methods: list[str] = []
	found: list[str] = []

	arp_hosts = _scapy_arp_scan(network)
	if arp_hosts:
		found.extend(arp_hosts)
		methods.append("arp")

	icmp_hosts = _scapy_icmp_sweep(network)
	if icmp_hosts:
		found.extend(icmp_hosts)
		methods.append("icmp")

	if found:
		return _unique_ips(found), methods

	fallback = _sweep_private_subnet(network)
	if fallback:
		return fallback, ["tcp-ping"]
	return [], methods


def _subnets_to_scan(seed_ip: str | None) -> list:
	networks = []
	seen = set()
	candidates = []
	if is_scannable_private_ipv4(seed_ip) and not is_container_peer_ipv4(seed_ip):
		candidates.append(seed_ip)
	candidates.extend(ip for ip in _local_ipv4s() if not is_container_peer_ipv4(ip))
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
			_ping_command(ip),
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


def rank_office_ipv4s(values) -> list[str]:
	"""Public client IPs first, then real LAN hosts. Drop Docker/loopback peers."""
	public: list[str] = []
	private: list[str] = []
	for ip in _unique_ips(values):
		if is_container_peer_ipv4(ip):
			continue
		if ipaddress.ip_address(ip).is_private:
			private.append(ip)
		else:
			public.append(ip)
	return public + private


def _parse_client_ips(client_ip: str | None = None, client_ips=None) -> list[str]:
	values: list[str] = []
	if isinstance(client_ips, (list, tuple)):
		values.extend(client_ips)
	elif client_ips:
		values.extend(parse_office_ipv4s(str(client_ips)))
	if client_ip:
		values.insert(0, client_ip)
	return rank_office_ipv4s(values)


def discover_office_network(seed_ip: str | None = None, client_ips: list[str] | None = None) -> dict:
	"""Discover the browser's real network IPv4, then live hosts on a reachable office LAN."""
	scanned = rank_office_ipv4s(client_ips or [])
	methods: list[str] = []
	if scanned:
		methods.append("client")

	seed = scanned[0] if scanned else normalize_ipv4(seed_ip) or best_client_ipv4()
	found = list(scanned)
	if seed and seed not in found and not is_container_peer_ipv4(seed):
		found.append(seed)

	found.extend(ip for ip in _local_ipv4s() if not is_container_peer_ipv4(ip))
	cache_ips = [ip for ip in _arp_cache_ipv4s() if not is_container_peer_ipv4(ip)]
	if cache_ips:
		found.extend(cache_ips)
		methods.append("arp-cache")

	networks = []
	if not getattr(frappe.flags, "in_test", False):
		lan_seed = seed if is_scannable_private_ipv4(seed) and not is_container_peer_ipv4(seed) else None
		for network in _subnets_to_scan(lan_seed):
			networks.append(str(network))
			hosts, used = _scan_live_hosts(network)
			found.extend(ip for ip in hosts if not is_container_peer_ipv4(ip))
			methods.extend(used)

	return {
		"ips": rank_office_ipv4s(found),
		"methods": list(dict.fromkeys(methods)),
		"networks": networks,
	}


def discover_office_ipv4s(seed_ip: str | None = None) -> list[str]:
	return discover_office_network(seed_ip)["ips"]


@frappe.whitelist()
def scan_office_ipv4(client_ip: str | None = None, client_ips: str | list | None = None) -> dict:
	frappe.only_for(["System Manager", "Administrator", "HR Manager"])
	scanned = _parse_client_ips(client_ip, client_ips)
	discovery = discover_office_network(client_ips=scanned)
	ips = discovery["ips"]
	if not ips:
		frappe.throw(_("Could not detect a real network IPv4 address."))

	applied = apply_office_ipv4_defaults("\n".join(ips))
	return {
		"ip": ips[0],
		"ips": ips,
		"count": len(ips),
		"default_ip": applied["default_ip"],
		"employees": applied["employees"],
		"cubicles": applied["cubicles"],
		"methods": discovery["methods"],
		"networks": discovery["networks"],
	}
