# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.bpo_hourly_rate import apply_hourly_rate, find_hourly_rate_targets
from hrms.tests.utils import HRMSTestSuite


class TestBPOHourlyRate(HRMSTestSuite):
	def test_apply_hourly_rate_to_other_agents(self):
		source = make_employee("hourly_source@example.com", company="_Test Company")
		other = make_employee("hourly_other@example.com", company="_Test Company")
		frappe.db.set_value("Employee", source, "ctc", 14.5)

		result = apply_hourly_rate(
			source_employee=source,
			hourly_rate=14.5,
			employees=[other],
			company="_Test Company",
		)
		self.assertEqual(result["updated"], 2)
		self.assertEqual(flt(frappe.db.get_value("Employee", other, "ctc")), 14.5)
		self.assertEqual(flt(frappe.db.get_value("Employee", source, "ctc")), 14.5)

	def test_change_this_agent_hourly_rate(self):
		source = make_employee("hourly_self@example.com", company="_Test Company")
		frappe.db.set_value("Employee", source, "ctc", 18)

		result = apply_hourly_rate(
			source_employee=source,
			hourly_rate=20.5,
			company="_Test Company",
		)
		self.assertEqual(result["updated"], 1)
		self.assertEqual(flt(frappe.db.get_value("Employee", source, "ctc")), 20.5)

	def test_apply_hourly_rate_by_branch(self):
		branch = "Hourly Rate Branch"
		if not frappe.db.exists("Branch", branch):
			frappe.get_doc({"doctype": "Branch", "branch": branch}).insert()

		source = make_employee("hourly_branch_src@example.com", company="_Test Company")
		teammate = make_employee(
			"hourly_branch_peer@example.com",
			company="_Test Company",
			branch=branch,
		)
		frappe.db.set_value("Employee", teammate, "branch", branch)

		targets = find_hourly_rate_targets(
			source_employee=source,
			branches=[branch],
			company="_Test Company",
		)
		self.assertIn(teammate, targets)
		self.assertNotIn(source, targets)

		apply_hourly_rate(
			source_employee=source,
			hourly_rate=11,
			branches=[branch],
			company="_Test Company",
		)
		self.assertEqual(flt(frappe.db.get_value("Employee", teammate, "ctc")), 11)
		self.assertEqual(flt(frappe.db.get_value("Employee", source, "ctc")), 11)
