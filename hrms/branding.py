import json
import re
import shutil
from pathlib import Path

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

APP_TITLE = "Staff Pro BPO"
APP_LOGO = "/assets/hrms/images/staff-pro-bpo-logo.png"
APP_ICON = "/assets/hrms/images/staff-pro-bpo-icon.png"
FOOTER_POWERED = "Staff Pro BPO<br>developed by Tirell Arzu"
STAFF_PRO_TIMEZONE = "America/Belize"
USER_HIDDEN_SETTINGS_FIELDS = (
	"app_section",
	"default_app",
	"third_party_authentication",
	"social_logins",
	"role_profiles",
	"role_profile_name",
	"form_settings",
	"report_settings",
	"document_follow",
	"document_follow_notify",
	"follow_created_documents",
	"follow_commented_documents",
	"follow_liked_documents",
	"follow_assigned_documents",
	"follow_shared_documents",
	"email_settings",
	"thread_notify",
	"send_me_a_copy",
	"allowed_in_mentions",
	"email_signature",
	"workspace",
	"default_workspace",
	"connections_tab",
	"send_welcome_email",
	"search_bar",
	"notifications",
	"list_sidebar",
	"bulk_actions",
	"view_switcher",
	"form_sidebar",
	"timeline",
	"dashboard",
)
SYSTEM_HIDDEN_SETTINGS_FIELDS = (
	"default_app",
	"app_tab",
	"email_tab",
	"advanced_tab",
	"backups_tab",
)
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
	ensure_belize_timezone()
	hide_system_settings_app_tab()
	hide_user_settings_fields()


def update_website_context(context):
	"""Keep the website footer branded even if Website Settings still say ERPNext."""
	context["footer_powered"] = FOOTER_POWERED


def ensure_desk_bundles():
	"""Publish hashed desk CSS/JS so first login can load the custom BPO UI."""
	repair_desk_ltr_bundles()


def ensure_ltr_bundle_css():
	"""Publish the LTR desk stylesheet only (never the rtlcss mirror)."""
	ensure_hashed_bundle("hrms.bundle.css", ("css",))


def repair_desk_ltr_bundles():
	"""Rebuild-safe publish: desk CSS must come from dist/css, not dist/css-rtl."""
	ensure_hashed_bundle("hrms.bundle.css", ("css",))
	ensure_hashed_bundle("hrms.bundle.js", ("js",))


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
	"""Copy the newest bundle from ``folders[0]`` onto the hashed name in assets.json.

	Only the primary folder is used. ``css-rtl`` / ``js-rtl`` mirrors must never be
	published as the LTR assets the desk loads — that mirrors the sidebar to
	``right: 0`` and the menu appears blank.
	"""
	if not folders:
		return None
	directory = app_dist / folders[0]
	pattern = f"{Path(manifest_key).stem}.*{Path(manifest_key).suffix}"
	sources = []
	if directory.exists():
		sources = [
			path
			for path in directory.glob(pattern)
			if path.is_file() and path.stat().st_size and not path.name.endswith(".map")
		]
	if manifest_key.endswith(".css"):
		sources = [path for path in sources if css_bundle_is_ltr(path)]

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

	if dest.exists() and manifest_key.endswith(".css") and not css_bundle_is_ltr(dest):
		frappe.log_error(
			title="Staff Pro desk CSS is RTL",
			message=f"Refusing to publish mirrored stylesheet: {dest}",
		)
		return None

	return dest


def css_bundle_is_ltr(path: Path) -> bool:
	"""Detect rtlcss output mistakenly published as hrms.bundle.css."""
	try:
		text = path.read_text(encoding="utf-8", errors="replace")[:400_000]
	except OSError:
		return False
	compact = re.sub(r"\s+", "", text)
	if "direction:rtl" in compact:
		return False
	# rtlcss mirrors the desk sidebar onto the right edge of its container.
	if re.search(r"\.body-sidebar\{[^}]*position:absolute[^}]*right:0", compact):
		if not re.search(r"\.body-sidebar\{[^}]*left:0", compact):
			return False
	return True


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


def ensure_belize_timezone() -> None:
	"""Staff Pro always runs on Belize time. Keep System Settings locked to it."""
	if not frappe.db.exists("DocType", "System Settings"):
		return
	if not frappe.get_meta("System Settings").has_field("time_zone"):
		return

	if frappe.db.get_single_value("System Settings", "time_zone") != STAFF_PRO_TIMEZONE:
		frappe.db.set_single_value("System Settings", "time_zone", STAFF_PRO_TIMEZONE, update_modified=False)
	frappe.db.set_default("time_zone", STAFF_PRO_TIMEZONE)
	frappe.cache.set_value("time_zone", STAFF_PRO_TIMEZONE)
	if getattr(frappe.local, "system_settings", None) is not None:
		frappe.local.system_settings.time_zone = STAFF_PRO_TIMEZONE
	_sync_site_config_timezone()
	from hrms.hr.timezone import lock_all_user_timezones

	lock_all_user_timezones()
	make_property_setter(
		"System Settings",
		"time_zone",
		"read_only",
		1,
		"Check",
		validate_fields_for_doctype=False,
	)
	make_property_setter(
		"System Settings",
		"time_zone",
		"default",
		STAFF_PRO_TIMEZONE,
		"Text",
		validate_fields_for_doctype=False,
	)
	frappe.clear_cache(doctype="System Settings")


def lock_system_timezone(doc, method: str | None = None) -> None:
	"""Keep System Settings on Belize time even if someone edits the form."""
	if not doc.meta.has_field("time_zone"):
		return
	doc.time_zone = STAFF_PRO_TIMEZONE


def _sync_site_config_timezone() -> None:
	if frappe.flags.in_test:
		return
	from frappe.installer import update_site_config

	if frappe.conf.get("time_zone") == STAFF_PRO_TIMEZONE:
		return
	try:
		update_site_config("time_zone", STAFF_PRO_TIMEZONE)
		frappe.conf["time_zone"] = STAFF_PRO_TIMEZONE
	except OSError:
		return


def hide_system_settings_app_tab() -> None:
	"""Hide Default App and unused System Settings tabs."""
	if not frappe.db.exists("DocType", "System Settings"):
		return

	meta = frappe.get_meta("System Settings")
	if meta.has_field("default_app"):
		frappe.db.set_single_value("System Settings", "default_app", "hrms", update_modified=False)
	for fieldname in SYSTEM_HIDDEN_SETTINGS_FIELDS:
		if not meta.has_field(fieldname):
			continue
		make_property_setter(
			"System Settings",
			fieldname,
			"hidden",
			1,
			"Check",
			validate_fields_for_doctype=False,
		)
	frappe.clear_cache(doctype="System Settings")


def hide_user_settings_fields() -> None:
	"""Keep every user on HRMS and drop unused login settings from the User form."""
	if not frappe.db.exists("DocType", "User"):
		return

	meta = frappe.get_meta("User")
	for fieldname in USER_HIDDEN_SETTINGS_FIELDS:
		if not meta.has_field(fieldname):
			continue
		make_property_setter(
			"User",
			fieldname,
			"hidden",
			1,
			"Check",
			validate_fields_for_doctype=False,
		)

	if meta.has_field("default_app") and frappe.db.has_column("User", "default_app"):
		frappe.db.sql(
			"""
			UPDATE `tabUser`
			SET default_app = 'hrms'
			WHERE IFNULL(default_app, '') != 'hrms'
			"""
		)

	frappe.clear_cache(doctype="User")


def _set_if_field(doctype: str, fieldname: str, value: str) -> None:
	if not frappe.get_meta(doctype).has_field(fieldname):
		return
	frappe.db.set_single_value(doctype, fieldname, value)
