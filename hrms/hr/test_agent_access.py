# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils.password import update_password

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.kiosk import clock
from hrms.hr.agent_access import (
	_ping_command,
	_scan_live_hosts,
	apply_office_ipv4_defaults,
	best_client_ipv4,
	is_agent_access_exempt,
	is_container_peer_ipv4,
	is_scannable_private_ipv4,
	normalize_ipv4,
	parse_office_ipv4s,
	rank_office_ipv4s,
	scan_office_ipv4,
	validate_agent_clockin_ip,
	validate_or_bind_login_device,
)
from hrms.hr.doctype.employee_checkin.test_employee_checkin import make_checkin
from hrms.setup import get_custom_fields
from hrms.tests.utils import HRMSTestSuite

OFFICE_IP = "203.0.113.10"
OTHER_IP = "198.51.100.20"


def _ensure_fields():
	custom_fields = get_custom_fields()
	create_custom_fields(
		{doctype: fields for doctype, fields in custom_fields.items() if doctype in {"System Settings", "Employee"}},
		ignore_validate=True,
	)


def _set_ip_restriction(enabled: int, ips: str = ""):
	frappe.db.set_single_value("System Settings", "restrict_agent_clockin_to_office_ip", enabled)
	frappe.db.set_single_value("System Settings", "office_clockin_ipv4", ips)


def _set_device_restriction(enabled: int):
	frappe.db.set_single_value("System Settings", "restrict_agent_login_to_device", enabled)


def _make_agent_user(email: str, username: str, password: str = "KioskPass123") -> tuple[str, str]:
	employee = make_employee(email, company="_Test Company")
	user = frappe.db.get_value("Employee", employee, "user_id")
	frappe.db.set_value("User", user, {"username": username, "user_type": "Website User"})
	update_password(user, password)
	if frappe.get_meta("Employee").has_field("login_device_id"):
		frappe.db.set_value("Employee", employee, "login_device_id", None, update_modified=False)
	return employee, user


class TestAgentAccess(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		_ensure_fields()
		_set_ip_restriction(0, "")
		_set_device_restriction(0)
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)
		frappe.local.request_ip = OFFICE_IP

	def tearDown(self):
		frappe.set_user("Administrator")
		_set_ip_restriction(0, "")
		_set_device_restriction(0)
		frappe.local.request_ip = "127.0.0.1"

	def test_normalize_and_parse_ipv4(self):
		self.assertEqual(normalize_ipv4("203.0.113.10"), OFFICE_IP)
		self.assertEqual(normalize_ipv4("::ffff:203.0.113.10"), OFFICE_IP)
		self.assertEqual(normalize_ipv4("203.0.113.10, 10.0.0.1"), OFFICE_IP)
		self.assertEqual(normalize_ipv4("2001:db8::1"), "")
		self.assertEqual(normalize_ipv4("not-an-ip"), "")
		self.assertEqual(
			parse_office_ipv4s("203.0.113.10\n198.51.100.20, 203.0.113.10"),
			[OFFICE_IP, OTHER_IP],
		)
		self.assertEqual(normalize_ipv4("for=203.0.113.10"), OFFICE_IP)
		self.assertEqual(normalize_ipv4("203.0.113.10:1234"), OFFICE_IP)

	def test_container_peer_and_best_client_ip(self):
		from unittest.mock import patch

		self.assertTrue(is_container_peer_ipv4("172.19.0.1"))
		self.assertTrue(is_container_peer_ipv4("127.0.0.1"))
		self.assertFalse(is_container_peer_ipv4(OFFICE_IP))
		self.assertFalse(is_container_peer_ipv4("192.168.1.20"))

		with patch("hrms.hr.agent_access._header_ipv4s", return_value=[]):
			frappe.local.request_ip = "172.19.0.1"
			self.assertEqual(best_client_ipv4(OFFICE_IP), OFFICE_IP)
			frappe.local.request_ip = OTHER_IP
			self.assertEqual(best_client_ipv4(OFFICE_IP), OTHER_IP)

		frappe.local.request_ip = "172.19.0.1"
		with patch("hrms.hr.agent_access._header_ipv4s", return_value=[OFFICE_IP]):
			self.assertEqual(best_client_ipv4(OTHER_IP), OFFICE_IP)

	def test_clock_uses_scanned_ip_behind_docker(self):
		from unittest.mock import patch

		_set_ip_restriction(1, OFFICE_IP)
		employee, _user = _make_agent_user("kiosk.ip.docker@example.com", "KioskIpDocker")
		frappe.local.request_ip = "172.19.0.1"
		frappe.set_user("Guest")
		with patch("hrms.hr.agent_access._header_ipv4s", return_value=[]):
			result = clock("KioskIpDocker", "KioskPass123", "IN", client_ip=OFFICE_IP)
		self.assertEqual(result["log_type"], "IN")
		self.assertEqual(result["employee"], employee)

	def test_clock_rejects_spoofed_ip_when_peer_is_public(self):
		from unittest.mock import patch

		_set_ip_restriction(1, OFFICE_IP)
		_make_agent_user("kiosk.ip.spoof@example.com", "KioskIpSpoof")
		frappe.local.request_ip = OTHER_IP
		frappe.set_user("Guest")
		with patch("hrms.hr.agent_access._header_ipv4s", return_value=[]), self.assertRaises(frappe.ValidationError):
			clock("KioskIpSpoof", "KioskPass123", "IN", client_ip=OFFICE_IP)

	def test_clock_rejects_non_office_ip(self):
		_set_ip_restriction(1, OFFICE_IP)
		_make_agent_user("kiosk.ip.deny@example.com", "KioskIpDeny")
		frappe.local.request_ip = OTHER_IP
		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			clock("KioskIpDeny", "KioskPass123", "IN")

	def test_clock_allows_office_ip(self):
		_set_ip_restriction(1, OFFICE_IP)
		employee, _user = _make_agent_user("kiosk.ip.allow@example.com", "KioskIpAllow")
		frappe.local.request_ip = OFFICE_IP
		frappe.set_user("Guest")
		result = clock("KioskIpAllow", "KioskPass123", "IN")
		self.assertEqual(result["log_type"], "IN")
		self.assertEqual(result["employee"], employee)

	def test_desk_admin_checkin_skips_ip(self):
		_set_ip_restriction(1, OFFICE_IP)
		frappe.local.request_ip = OTHER_IP
		frappe.set_user("Administrator")
		self.assertTrue(is_agent_access_exempt("Administrator"))
		employee = make_employee("kiosk.ip.admin@example.com", company="_Test Company")
		log = make_checkin(employee)
		self.assertTrue(log.name)

	def test_agent_checkin_rejects_non_office_ip(self):
		_set_ip_restriction(1, OFFICE_IP)
		frappe.local.request_ip = OTHER_IP
		with self.assertRaises(frappe.ValidationError):
			validate_agent_clockin_ip("EMP-0001", ignore_session_exemption=True)

	def test_login_device_binds_on_first_use(self):
		_set_device_restriction(1)
		employee, user = _make_agent_user("kiosk.device.bind@example.com", "KioskDeviceBind")
		validate_or_bind_login_device(user, "device-alpha")
		self.assertEqual(frappe.db.get_value("Employee", employee, "login_device_id"), "device-alpha")
		validate_or_bind_login_device(user, "device-alpha")

	def test_login_device_requires_id_on_first_use(self):
		_set_device_restriction(1)
		_employee, user = _make_agent_user("kiosk.device.empty@example.com", "KioskDeviceEmpty")
		with self.assertRaises(frappe.ValidationError):
			validate_or_bind_login_device(user, "")

	def test_login_device_rejects_mismatch(self):
		_set_device_restriction(1)
		employee, user = _make_agent_user("kiosk.device.deny@example.com", "KioskDeviceDeny")
		frappe.db.set_value("Employee", employee, "login_device_id", "device-alpha")
		with self.assertRaises(frappe.ValidationError):
			validate_or_bind_login_device(user, "device-other")

	def test_login_device_skips_desk_admin(self):
		_set_device_restriction(1)
		validate_or_bind_login_device("Administrator", "device-other")

	def test_scan_office_ipv4(self):
		from unittest.mock import patch

		frappe.local.request_ip = OFFICE_IP
		with patch("hrms.hr.agent_access._header_ipv4s", return_value=[]):
			result = scan_office_ipv4()
		self.assertEqual(result["ip"], OFFICE_IP)
		self.assertIn(OFFICE_IP, result["ips"])
		self.assertIn("methods", result)
		self.assertIn("networks", result)

	def test_scan_office_ipv4_uses_client_network_ip(self):
		from unittest.mock import patch

		real_ip = "179.42.242.87"
		frappe.local.request_ip = "172.19.0.1"
		with patch("hrms.hr.agent_access._header_ipv4s", return_value=[]):
			result = scan_office_ipv4(client_ip=real_ip, client_ips=real_ip)
		self.assertEqual(result["ip"], real_ip)
		self.assertEqual(result["ips"][0], real_ip)
		self.assertIn("client", result["methods"])
		self.assertNotIn("172.19.0.1", result["ips"])
		self.assertEqual(rank_office_ipv4s([real_ip, "172.19.0.1", "192.168.1.20"]), [real_ip, "192.168.1.20"])

	def test_private_scan_scope(self):
		self.assertTrue(is_scannable_private_ipv4("192.168.1.20"))
		self.assertTrue(is_scannable_private_ipv4("10.0.0.8"))
		self.assertFalse(is_scannable_private_ipv4(OFFICE_IP))
		self.assertFalse(is_scannable_private_ipv4("127.0.0.1"))
		self.assertFalse(is_scannable_private_ipv4("8.8.8.8"))

	def test_ping_command_is_platform_specific(self):
		cmd = _ping_command("192.168.1.20")
		self.assertEqual(cmd[0], "ping")
		self.assertIn("192.168.1.20", cmd)

	def test_scan_live_hosts_uses_arp_then_icmp(self):
		from unittest.mock import patch

		import ipaddress

		network = ipaddress.ip_network("192.168.1.0/24")
		with (
			patch("hrms.hr.agent_access._scapy_arp_scan", return_value=["192.168.1.10"]),
			patch("hrms.hr.agent_access._scapy_icmp_sweep", return_value=["192.168.1.20", "192.168.1.10"]),
			patch("hrms.hr.agent_access._sweep_private_subnet") as fallback,
		):
			hosts, methods = _scan_live_hosts(network)

		self.assertEqual(hosts, ["192.168.1.10", "192.168.1.20"])
		self.assertEqual(methods, ["arp", "icmp"])
		fallback.assert_not_called()

	def test_apply_office_ipv4_defaults_to_agents(self):
		employee = make_employee("kiosk.default.ip@example.com", company="_Test Company")
		if frappe.get_meta("Employee").has_field("default_ipv4"):
			frappe.db.set_value("Employee", employee, "default_ipv4", None, update_modified=False)
		_set_ip_restriction(1, OFFICE_IP)
		applied = apply_office_ipv4_defaults(OFFICE_IP)
		self.assertEqual(applied["default_ip"], OFFICE_IP)
		if frappe.get_meta("Employee").has_field("default_ipv4"):
			self.assertEqual(frappe.db.get_value("Employee", employee, "default_ipv4"), OFFICE_IP)
