import frappe

APP_TITLE = "Staff Pro BPO"
APP_LOGO = "/assets/hrms/images/staff-pro-bpo-logo.png"
APP_ICON = "/assets/hrms/images/staff-pro-bpo-icon.png"


def apply_branding():
	"""Apply Staff Pro BPO name, logo, and favicon to site settings."""
	_set_if_field("Website Settings", "app_name", APP_TITLE)
	_set_if_field("Website Settings", "app_logo", APP_LOGO)
	_set_if_field("Website Settings", "splash_image", APP_LOGO)
	_set_if_field("Website Settings", "favicon", APP_ICON)
	_set_if_field("Navbar Settings", "app_logo", APP_LOGO)
	_set_if_field("System Settings", "app_name", APP_TITLE)


def _set_if_field(doctype: str, fieldname: str, value: str) -> None:
	if not frappe.get_meta(doctype).has_field(fieldname):
		return
	frappe.db.set_single_value(doctype, fieldname, value)
