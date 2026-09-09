# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import datetime

import frappe
from frappe.utils import getdate
from frappe.utils.password import update_password

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.kiosk import clock, get_kiosk_context, get_kiosk_profile, resolve_login, resolve_workstation_device
from hrms.hr.doctype.employee_checkin.test_employee_checkin import make_checkin
from hrms.hr.bpo_employee_labels import enable_username_login
from hrms.overrides.employee_master import (
	resolve_user_from_login,
	set_employee_username,
	suggest_username,
)
from hrms.tests.utils import HRMSTestSuite


class TestKioskLogin(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_suggest_username(self):
		self.assertEqual(suggest_username("Tirell", "Arzu"), "TArzu")
		self.assertEqual(suggest_username("Jane", "Doe"), "JDoe")

	def test_resolve_user_from_username(self):
		employee = make_employee("kiosk.resolve@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		frappe.db.set_value("User", user, "username", "KioskResolve")
		self.assertEqual(resolve_user_from_login("KioskResolve"), user)
		self.assertEqual(resolve_login("KioskResolve"), user)

	def test_enable_username_login(self):
		enable_username_login()
		self.assertEqual(frappe.db.get_single_value("System Settings", "allow_login_using_user_name"), 1)

	def test_kiosk_clock_in_with_username(self):
		employee = make_employee("kiosk.clock@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		frappe.db.set_value("User", user, "username", "KioskClock")
		update_password(user, "KioskPass123")

		result = clock("KioskClock", "KioskPass123", "IN")
		self.assertEqual(result["log_type"], "IN")
		self.assertEqual(result["employee"], employee)
		self.assertEqual(result["next_action"], "OUT")
		self.assertTrue(frappe.db.exists("Employee Checkin", result["checkin"]))

	def test_kiosk_rejects_bad_password(self):
		employee = make_employee("kiosk.badpass@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		frappe.db.set_value("User", user, "username", "KioskBad")
		update_password(user, "CorrectPass123")

		self.assertRaises(frappe.ValidationError, clock, "KioskBad", "wrong-password", "IN")

	def test_kiosk_profile_shows_punch_times(self):
		employee = make_employee("kiosk.profile@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		frappe.db.set_value("User", user, "username", "KioskProfile")
		update_password(user, "KioskPass123")

		clock("KioskProfile", "KioskPass123", "IN")
		frappe.set_user("Guest")
		profile = get_kiosk_profile("KioskProfile")
		self.assertEqual(profile["employee"], employee)
		self.assertEqual(profile["next_action"], "OUT")
		self.assertTrue(profile["last_in_label"])

	def test_kiosk_profile_lists_todays_sessions(self):
		employee = make_employee("kiosk.sessions@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		frappe.db.set_value("User", user, "username", "KioskSessions")
		day = getdate()
		morning_in = datetime.combine(day, datetime.min.time()).replace(hour=8, minute=0)
		morning_out = datetime.combine(day, datetime.min.time()).replace(hour=12, minute=9)
		afternoon_in = datetime.combine(day, datetime.min.time()).replace(hour=13, minute=27)
		make_checkin(employee, morning_in, log_type="IN")
		make_checkin(employee, morning_out, log_type="OUT")
		make_checkin(employee, afternoon_in, log_type="IN")

		profile = get_kiosk_profile("KioskSessions")
		self.assertEqual(len(profile["today_labels"]), 2)
		self.assertTrue(profile["today_labels"][0].endswith(" -"))
		self.assertIn("4h 9m", profile["today_labels"][1])
		self.assertEqual(profile["next_action"], "OUT")

	def test_kiosk_profile_unknown_user(self):
		self.assertEqual(get_kiosk_profile("NobodyHere"), {})

	def test_kiosk_context_has_company(self):
		context = get_kiosk_context()
		self.assertIn("company_name", context)
		self.assertIn("ip", context)

	def test_kiosk_context_uses_scanned_client_ip(self):
		from unittest.mock import patch

		frappe.local.request_ip = "172.19.0.1"
		with patch("hrms.hr.agent_access._header_ipv4s", return_value=[]):
			context = get_kiosk_context(client_ip="203.0.113.10")
		self.assertEqual(context["ip"], "203.0.113.10")

	def test_kiosk_clock_sets_cubicle_device_id(self):
		employee = make_employee("kiosk.device.bind@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		frappe.db.set_value("User", user, "username", "KioskDeviceBind")
		update_password(user, "KioskPass123")
		cubicle = _make_cubicle(employee)

		result = clock("KioskDeviceBind", "KioskPass123", "IN", device_id="browser-uuid-alpha")
		self.assertEqual(result["device_id"], "browser-uuid-alpha")
		self.assertEqual(frappe.db.get_value("Cubicle", cubicle, "device_id"), "browser-uuid-alpha")
		self.assertEqual(
			frappe.db.get_value("Employee Checkin", result["checkin"], "device_id"),
			"browser-uuid-alpha",
		)

	def test_kiosk_uses_existing_cubicle_device_id(self):
		employee = make_employee("kiosk.device.keep@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		frappe.db.set_value("User", user, "username", "KioskDeviceKeep")
		update_password(user, "KioskPass123")
		cubicle = _make_cubicle(employee, device_id="seat-device-77", ip_address="203.0.113.77")

		result = clock("KioskDeviceKeep", "KioskPass123", "IN", device_id="6506")
		self.assertEqual(result["device_id"], "seat-device-77")
		self.assertEqual(frappe.db.get_value("Cubicle", cubicle, "device_id"), "seat-device-77")
		profile = get_kiosk_profile("KioskDeviceKeep")
		self.assertEqual(profile["device_id"], "seat-device-77")
		self.assertEqual(resolve_workstation_device(employee), "seat-device-77")

		from unittest.mock import patch

		frappe.local.request_ip = "172.19.0.1"
		with patch("hrms.hr.agent_access._header_ipv4s", return_value=[]):
			context = get_kiosk_context(client_ip="203.0.113.77")
		self.assertEqual(context["device_id"], "seat-device-77")

	def test_typing_username_updates_user(self):
		employee = make_employee("kiosk.rename@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		result = set_employee_username(employee, "KioskRename")
		self.assertEqual(result["username"], "KioskRename")
		self.assertEqual(frappe.db.get_value("Employee", employee, "user_id"), user)
		self.assertEqual(frappe.db.get_value("User", user, "username"), "KioskRename")


def _make_cubicle(employee=None, device_id=None, ip_address=None):
	floor_name = f"Kiosk Floor {frappe.generate_hash(length=8)}"
	if not frappe.db.exists("Office Floor", floor_name):
		frappe.get_doc({"doctype": "Office Floor", "floor_name": floor_name}).insert()
	doc = frappe.get_doc(
		{
			"doctype": "Cubicle",
			"office_floor": floor_name,
			"row": "A",
			"seat_number": 1,
			"employee": employee,
			"device_id": device_id,
			"ip_address": ip_address,
		}
	)
	doc.insert()
	return doc.name
