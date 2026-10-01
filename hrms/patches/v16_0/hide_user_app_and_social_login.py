"""Hide Default App and third-party login on the User form. Staff Pro stays on HRMS."""

from hrms.branding import hide_user_settings_fields


def execute():
	hide_user_settings_fields()
