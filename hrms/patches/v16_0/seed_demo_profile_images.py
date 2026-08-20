# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Attach bundled demo headshots to existing Staff Pro demo employees."""

import frappe


def execute():
	try:
		from hrms.import_hr_demo_data import seed_demo_profile_images

		seed_demo_profile_images()
	except Exception:
		frappe.log_error(title="Demo profile image seed failed")
