# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import os
import tempfile
from datetime import date

import frappe

from hrms.hr.backups import is_database_dump, period_is_due, resolve_dump_path
from hrms.tests.utils import HRMSTestSuite

WEDNESDAY = date(2026, 9, 30)


class TestBackupSchedule(HRMSTestSuite):
	def test_off_never_runs(self):
		self.assertFalse(period_is_due("Off", "Wednesday", 30, WEDNESDAY))
		self.assertFalse(period_is_due("", "Wednesday", 30, WEDNESDAY))

	def test_daily_runs_every_day(self):
		self.assertTrue(period_is_due("Daily", "Monday", 1, WEDNESDAY))

	def test_weekly_matches_the_weekday(self):
		self.assertTrue(period_is_due("Weekly", "Wednesday", 1, WEDNESDAY))
		self.assertFalse(period_is_due("Weekly", "Monday", 1, WEDNESDAY))

	def test_monthly_clamps_to_day_28(self):
		self.assertTrue(period_is_due("Monthly", "Monday", 30, date(2026, 9, 28)))
		self.assertFalse(period_is_due("Monthly", "Monday", 30, WEDNESDAY))

	def test_dump_path_stays_inside_the_backup_folder(self):
		with tempfile.TemporaryDirectory() as folder:
			name = "20260930_120000-site-database.sql.gz"
			path = os.path.join(folder, name)
			with open(path, "wb") as handle:
				handle.write(b"dump")
			self.assertEqual(resolve_dump_path(folder, name), os.path.realpath(path))
			self.assertRaises(frappe.ValidationError, resolve_dump_path, folder, "../secret-database.sql.gz")
			self.assertRaises(frappe.ValidationError, resolve_dump_path, folder, "notes.txt")
			self.assertFalse(is_database_dump("site-files.tar"))
			self.assertTrue(is_database_dump(name))
			self.assertTrue(is_database_dump("20260930_120000-site-database-enc.sql.gz"))
