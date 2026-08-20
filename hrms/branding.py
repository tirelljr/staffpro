import json
import shutil
from pathlib import Path

import frappe

APP_TITLE = "Staff Pro BPO"
APP_LOGO = "/assets/hrms/images/staff-pro-bpo-logo.png"
APP_ICON = "/assets/hrms/images/staff-pro-bpo-icon.png"


def apply_branding():
	"""Apply Staff Pro BPO name, logo, and favicon to site settings."""
	ensure_ltr_bundle_css()
	_set_if_field("Website Settings", "app_name", APP_TITLE)
	_set_if_field("Website Settings", "app_logo", APP_LOGO)
	_set_if_field("Website Settings", "splash_image", APP_LOGO)
	_set_if_field("Website Settings", "favicon", APP_ICON)
	_set_if_field("Navbar Settings", "app_logo", APP_LOGO)
	_set_if_field("System Settings", "app_name", APP_TITLE)


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


def _set_if_field(doctype: str, fieldname: str, value: str) -> None:
	if not frappe.get_meta(doctype).has_field(fieldname):
		return
	frappe.db.set_single_value(doctype, fieldname, value)
