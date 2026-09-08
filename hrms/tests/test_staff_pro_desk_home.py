# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import json
import tempfile
from pathlib import Path

import frappe

from hrms.boot import (
	STAFF_PRO_DESK_HOME,
	get_staff_pro_home_page,
	on_staff_pro_login,
	prepare_staff_pro_first_login,
	staff_pro_desk_home_path,
)
from hrms.branding import publish_hashed_bundle
from hrms.tests.utils import HRMSTestSuite


class TestStaffProDeskHome(HRMSTestSuite):
	def test_desk_admin_home_is_people_dashboard(self):
		self.assertEqual(staff_pro_desk_home_path(), f"/{STAFF_PRO_DESK_HOME}")
		self.assertEqual(get_staff_pro_home_page("Administrator"), STAFF_PRO_DESK_HOME)

	def test_login_sends_desk_admin_to_bpo_home(self):
		on_staff_pro_login()
		self.assertEqual(frappe.local.response.get("home_page"), staff_pro_desk_home_path())
		self.assertEqual(frappe.local.response.get("redirect_to"), staff_pro_desk_home_path())

	def test_first_login_setup_points_staff_pro_icon_at_bpo_home(self):
		prepare_staff_pro_first_login()
		if frappe.db.exists("DocType", "Desktop Icon") and frappe.db.exists("Desktop Icon", "Staff Pro BPO"):
			self.assertEqual(
				frappe.db.get_value("Desktop Icon", "Staff Pro BPO", "link"),
				staff_pro_desk_home_path(),
			)
		if frappe.get_meta("System Settings").has_field("default_app"):
			self.assertEqual(frappe.db.get_single_value("System Settings", "default_app"), "hrms")

	def test_missing_hashed_js_bundle_is_copied_from_newest_build(self):
		with tempfile.TemporaryDirectory() as tmp:
			app_dist = Path(tmp) / "dist"
			js_dir = app_dist / "js"
			js_dir.mkdir(parents=True)
			source = js_dir / "hrms.bundle.SOURCE1.js"
			source.write_text("window.hrms = window.hrms || {};", encoding="utf-8")
			manifest = Path(tmp) / "assets.json"
			manifest.write_text(json.dumps({"hrms.bundle.js": "hrms/dist/js/hrms.bundle.PYHPJZB7.js"}), encoding="utf-8")

			dest = publish_hashed_bundle(app_dist, manifest, "hrms.bundle.js", ("js", "js-rtl"))
			self.assertIsNotNone(dest)
			self.assertEqual(dest.name, "hrms.bundle.PYHPJZB7.js")
			self.assertTrue(dest.exists())
			self.assertIn("window.hrms", dest.read_text(encoding="utf-8"))
