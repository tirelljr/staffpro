# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import cint

from hrms.hr.late_entry import DEFAULT_LATE_GRACE_MINUTES, late_entry_grace_for_shift


class TestLateEntryDefaults(IntegrationTestCase):
	def test_new_shift_type_defaults_from_docmeta(self):
		meta = frappe.get_meta("Shift Type")
		self.assertEqual(cint(meta.get_field("enable_late_entry_marking").default), 1)
		self.assertEqual(cint(meta.get_field("late_entry_grace_period").default), DEFAULT_LATE_GRACE_MINUTES)

	def test_late_entry_grace_for_shift_uses_grace_when_enabled(self):
		shift = frappe.get_doc(
			{
				"doctype": "Shift Type",
				"name": f"_test_late_{frappe.generate_hash(length=6)}",
				"start_time": "09:00:00",
				"end_time": "17:00:00",
				"enable_late_entry_marking": 1,
				"late_entry_grace_period": 15,
			}
		).insert(ignore_permissions=True)
		try:
			enabled, grace = late_entry_grace_for_shift(shift.name)
			self.assertTrue(enabled)
			self.assertEqual(grace, 15)
		finally:
			shift.delete(ignore_permissions=True)
