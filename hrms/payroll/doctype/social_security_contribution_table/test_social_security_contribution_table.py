# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.payroll.social_security import BELIZE_SSB_2022_BANDS
from hrms.tests.utils import HRMSTestSuite


class TestSocialSecurityContributionTable(HRMSTestSuite):
	def test_rejects_inverted_band_range(self):
		doc = frappe.get_doc(
			{
				"doctype": "Social Security Contribution Table",
				"title": "_Test SS Invalid Band",
				"effective_from": "2022-04-04",
				"bands": [
					{
						"band_label": "Bad",
						"from_weekly_earnings": 100,
						"to_weekly_earnings": 50,
						"insurable_earnings": 90,
						"employee_amount": 1,
						"employer_amount": 1,
					}
				],
			}
		)
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_accepts_belize_bands(self):
		name = "_Test SS Valid Bands"
		if frappe.db.exists("Social Security Contribution Table", name):
			frappe.delete_doc("Social Security Contribution Table", name, force=1)
		doc = frappe.get_doc(
			{
				"doctype": "Social Security Contribution Table",
				"title": name,
				"effective_from": "2022-04-04",
				"injury_only_employer_amount": 2.6,
				"bands": [dict(band) for band in BELIZE_SSB_2022_BANDS],
			}
		)
		doc.insert()
		self.assertEqual(len(doc.bands), 13)
		frappe.delete_doc("Social Security Contribution Table", name, force=1)
