import json
import shutil
from pathlib import Path

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

APP_TITLE = "Staff Pro BPO"
APP_LOGO = "/assets/hrms/images/staff-pro-bpo-logo.png"
APP_ICON = "/assets/hrms/images/staff-pro-bpo-icon.png"
FOOTER_POWERED = "Staff Pro BPO<br>developed by Tirell Arzu"
_LOGO_DATA_URI = None


def staff_pro_logo_url() -> str:
	"""Return a data URI so salary-slip PDFs do not depend on network access."""
	global _LOGO_DATA_URI
	if _LOGO_DATA_URI:
		return _LOGO_DATA_URI

	import base64

	path = Path(__file__).resolve().parent / "public" / "images" / "staff-pro-bpo-logo.png"
	if path.is_file():
		_LOGO_DATA_URI = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()
		return _LOGO_DATA_URI
	return APP_LOGO


def apply_branding():
	"""Apply Staff Pro BPO name, logo, and favicon to site settings."""
	ensure_ltr_bundle_css()
	_set_if_field("Website Settings", "app_name", APP_TITLE)
	_set_if_field("Website Settings", "app_logo", APP_LOGO)
	_set_if_field("Website Settings", "splash_image", APP_LOGO)
	_set_if_field("Website Settings", "favicon", APP_ICON)
	_set_if_field("Website Settings", "footer_powered", FOOTER_POWERED)
	_set_if_field("Navbar Settings", "app_logo", APP_LOGO)
	_set_if_field("System Settings", "app_name", APP_TITLE)
	hide_system_settings_app_tab()


def update_website_context(context):
	"""Keep the website footer branded even if Website Settings still say ERPNext."""
	context["footer_powered"] = FOOTER_POWERED


def ensure_ltr_bundle_css():
	"""Copy the RTL bundle to the LTR path when Docker/Windows skips dist/css."""
	try:
		bench = Path(frappe.utils.get_bench_path())
	except Exception:
		return

	css_dir = bench / "apps/hrms/hrms/public/dist/css"
	rtl_dir = bench / "apps/hrms/hrms/public/dist/css-rtl"
	manifest = bench / "sites/assets/assets.json"
	if not rtl_dir.exists() or not manifest.exists():
		return

	rtl = sorted(rtl_dir.glob("hrms.bundle.*.css"), key=lambda p: p.stat().st_mtime, reverse=True)
	if not rtl:
		return

	wanted = Path(json.loads(manifest.read_text()).get("hrms.bundle.css") or "").name
	if not wanted:
		return

	css_dir.mkdir(parents=True, exist_ok=True)
	dest = css_dir / wanted
	if dest.exists() and dest.stat().st_size:
		return

	shutil.copy2(rtl[0], dest)
	map_src = rtl[0].with_suffix(".css.map")
	if map_src.exists():
		shutil.copy2(map_src, dest.with_suffix(".css.map"))


def hide_system_settings_app_tab() -> None:
	"""Hide Default App so login always stays on Staff Pro BPO."""
	if not frappe.db.exists("DocType", "System Settings"):
		return

	meta = frappe.get_meta("System Settings")
	if meta.has_field("default_app"):
		frappe.db.set_single_value("System Settings", "default_app", "hrms", update_modified=False)
		make_property_setter(
			"System Settings",
			"default_app",
			"hidden",
			1,
			"Check",
			validate_fields_for_doctype=False,
		)
	if meta.has_field("app_tab"):
		make_property_setter(
			"System Settings",
			"app_tab",
			"hidden",
			1,
			"Check",
			validate_fields_for_doctype=False,
		)
	frappe.clear_cache(doctype="System Settings")


def _set_if_field(doctype: str, fieldname: str, value: str) -> None:
	if not frappe.get_meta(doctype).has_field(fieldname):
		return
	frappe.db.set_single_value(doctype, fieldname, value)
