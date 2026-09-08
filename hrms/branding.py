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
	ensure_desk_bundles()
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


def ensure_desk_bundles():
	"""Publish hashed desk CSS/JS so first login can load the custom BPO UI."""
	ensure_hashed_bundle("hrms.bundle.css", ("css", "css-rtl"))
	ensure_hashed_bundle("hrms.bundle.js", ("js", "js-rtl"))


def ensure_ltr_bundle_css():
	"""Copy the RTL bundle to the LTR path when Docker/Windows skips dist/css."""
	ensure_hashed_bundle("hrms.bundle.css", ("css", "css-rtl"))


def ensure_hashed_bundle(manifest_key: str, folders: tuple[str, ...]):
	"""Copy the newest built bundle onto the hashed name assets.json expects."""
	try:
		bench = Path(frappe.utils.get_bench_path())
	except Exception:
		return None

	app_dist = bench / "apps/hrms/hrms/public/dist"
	manifest = bench / "sites/assets/assets.json"
	dest = publish_hashed_bundle(app_dist, manifest, manifest_key, folders)
	if dest:
		_publish_sites_asset_copy(dest)
	return dest


def publish_hashed_bundle(
	app_dist: Path,
	manifest: Path,
	manifest_key: str,
	folders: tuple[str, ...],
):
	"""If the hashed bundle is missing, copy the newest matching file onto that name."""
	sources = []
	for folder in folders:
		directory = app_dist / folder
		if directory.exists():
			pattern = f"{Path(manifest_key).stem}.*{Path(manifest_key).suffix}"
			sources.extend(
				path
				for path in directory.glob(pattern)
				if path.is_file() and path.stat().st_size and not path.name.endswith(".map")
			)

	if not sources:
		return None

	newest = max(sources, key=lambda path: path.stat().st_mtime)
	wanted = _wanted_bundle_name(manifest, manifest_key) or newest.name
	dest_dir = app_dist / folders[0]
	dest_dir.mkdir(parents=True, exist_ok=True)
	dest = dest_dir / wanted
	if dest.resolve() != newest.resolve():
		if not dest.exists() or dest.stat().st_size != newest.stat().st_size:
			shutil.copy2(newest, dest)
			map_src = newest.with_name(newest.name + ".map")
			if not map_src.exists():
				map_src = newest.with_suffix(newest.suffix + ".map")
			if map_src.exists():
				shutil.copy2(map_src, dest.with_name(dest.name + ".map"))

	return dest


def _wanted_bundle_name(manifest: Path, manifest_key: str) -> str:
	if not manifest.exists():
		return ""
	try:
		return Path(json.loads(manifest.read_text(encoding="utf-8")).get(manifest_key) or "").name
	except (OSError, json.JSONDecodeError, TypeError):
		return ""


def _publish_sites_asset_copy(source: Path):
	"""Windows/Docker often fail to symlink sites/assets/hrms -> the app dist folder."""
	try:
		bench = Path(frappe.utils.get_bench_path())
	except Exception:
		return

	relative = Path("hrms") / "dist" / source.parent.name / source.name
	dest = bench / "sites/assets" / relative
	dest.parent.mkdir(parents=True, exist_ok=True)
	try:
		shutil.copy2(source, dest)
	except OSError:
		return


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
