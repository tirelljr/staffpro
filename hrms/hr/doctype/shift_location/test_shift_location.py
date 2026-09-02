# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from hrms.hr.staff_pro_shift_locations import DEFAULT_SHIFT_LOCATIONS, ensure_staff_pro_shift_locations
from hrms.tests.utils import HRMSTestSuite


class TestShiftLocation(HRMSTestSuite):
	def test_default_shift_locations_are_seeded_and_editable(self):
		ensure_staff_pro_shift_locations()

		for location_name in DEFAULT_SHIFT_LOCATIONS:
			self.assertTrue(frappe.db.exists("Shift Location", location_name))

		location = frappe.get_doc("Shift Location", "Santa Elena")
		location.checkin_radius = 250
		location.save()

		ensure_staff_pro_shift_locations()
		self.assertEqual(frappe.db.get_value("Shift Location", "Santa Elena", "checkin_radius"), 250)
