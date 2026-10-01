# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Add the Admin Backups page and hide the System Settings Backups tab."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.branding import hide_system_settings_app_tab
from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars
from hrms.setup import get_custom_fields


def execute():
	fields = [
		field
		for field in get_custom_fields().get("System Settings", [])
		if str(field.get("fieldname") or "").startswith("staff_pro_backup_")
	]
	if fields:
		create_custom_fields({"System Settings": fields}, ignore_validate=True)
	hide_system_settings_app_tab()
	sync_staff_pro_sidebars()
	frappe.clear_cache(doctype="System Settings")
