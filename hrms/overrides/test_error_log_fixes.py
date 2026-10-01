# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import unittest
from datetime import date

from hrms.hr.force_delete import ROLE_CHILD_TABLES
from hrms.overrides.fiscal_year import calendar_year_period, expected_fiscal_year_end, years_to_cover


class TestErrorLogFixes(unittest.TestCase):
	def test_role_unlink_keeps_doctype_docperms(self):
		self.assertNotIn("DocPerm", {doctype for doctype, _field in ROLE_CHILD_TABLES})

	def test_fiscal_year_end_is_one_year_minus_a_day(self):
		self.assertEqual(expected_fiscal_year_end("2026-01-01"), date(2026, 12, 31))
		self.assertEqual(expected_fiscal_year_end("2025-12-31"), date(2026, 12, 30))

	def test_payroll_ytd_uses_calendar_year_not_fiscal_year(self):
		self.assertEqual(calendar_year_period("2026-09-16"), (date(2026, 1, 1), date(2026, 12, 31)))
		self.assertEqual(calendar_year_period(date(2025, 12, 31)), (date(2025, 1, 1), date(2025, 12, 31)))

	def test_fiscal_years_cover_previous_current_next_and_existing_docs(self):
		self.assertEqual(years_to_cover("2026-09-16"), [2025, 2026, 2027])
		self.assertEqual(years_to_cover("2026-09-16", extra=(2024, 2026)), [2024, 2025, 2026, 2027])
