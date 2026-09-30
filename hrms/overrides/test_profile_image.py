# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import base64

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.overrides.employee_profile import update_my_profile_image
from hrms.tests.utils import HRMSTestSuite

PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


class TestProfileImage(HRMSTestSuite):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_agent_can_change_own_profile_photo(self):
		employee = make_employee("profile.photo@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		other = make_employee("profile.other@example.com", company="_Test Company")

		frappe.set_user(user)
		result = update_my_profile_image("photo.png", PNG)

		self.assertEqual(result["employee"], employee)
		self.assertTrue((result["user_image"] or "").startswith("/files/"))
		self.assertEqual(frappe.db.get_value("Employee", employee, "image"), result["user_image"])
		self.assertEqual(frappe.db.get_value("User", user, "user_image"), result["user_image"])
		self.assertFalse(frappe.db.get_value("Employee", other, "image"))

		with self.assertRaises(frappe.ValidationError):
			update_my_profile_image("notes.txt", base64.b64encode(b"not an image").decode())

		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			update_my_profile_image("photo.png", PNG)
