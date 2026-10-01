# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Drop unused email, analytics, and customization chrome from desk."""

from hrms.branding import hide_system_settings_app_tab, hide_user_settings_fields
from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars


def execute():
	hide_user_settings_fields()
	hide_system_settings_app_tab()
	sync_staff_pro_sidebars()
