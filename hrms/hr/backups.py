# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Scheduled and on-demand database dumps for System Managers."""

from __future__ import annotations

import os
import re
from datetime import date, datetime

import frappe
from frappe import _
from frappe.utils import cint, format_datetime, getdate

PERIODS = ("Off", "Daily", "Weekly", "Monthly")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
BACKUP_FIELDS = (
	"staff_pro_backup_period",
	"staff_pro_backup_weekday",
	"staff_pro_backup_month_day",
	"staff_pro_backup_limit",
)


def period_is_due(period: str, weekday: str, month_day, today: date) -> bool:
	"""Return whether a saved backup period should run on this date."""
	period = period or "Off"
	if period == "Daily":
		return True
	if period == "Weekly":
		return WEEKDAYS[today.weekday()] == (weekday or "Monday")
	if period == "Monthly":
		return today.day == clamp_month_day(month_day)
	return False


def clamp_month_day(month_day) -> int:
	day = cint(month_day) or 1
	return min(max(day, 1), 28)


def clamp_limit(limit) -> int:
	keep = cint(limit) or 7
	return min(max(keep, 1), 90)


def is_database_dump(filename: str) -> bool:
	name = os.path.basename(filename or "").lower()
	return bool(re.fullmatch(r".*-database(?:-enc)?\.sql(?:\.gz)?", name))


def resolve_dump_path(folder: str, filename: str) -> str:
	"""Return a database dump that lives inside the backup folder."""
	name = os.path.basename(str(filename or ""))
	if not name or name != str(filename) or not is_database_dump(name):
		frappe.throw(_("That backup file is not available."))
	root = os.path.realpath(folder)
	path = os.path.realpath(os.path.join(root, name))
	try:
		inside = os.path.commonpath([root, path]) == root
	except ValueError:
		inside = False
	if not inside or not os.path.isfile(path):
		frappe.throw(_("That backup file is not available."))
	return path


def run_scheduled_backup():
	"""Dump the database when today matches the saved backup period."""
	settings = _read_settings()
	today = getdate()
	if not period_is_due(settings["period"], settings["weekday"], settings["month_day"], today):
		return
	path = take_database_dump()
	prune_dumps(settings["limit"], keep_path=path)


@frappe.whitelist()
def get_backup_state():
	_ensure_system_manager()
	return {"settings": _read_settings(), "dumps": list_dump_rows()}


@frappe.whitelist()
def save_backup_settings(period, weekday=None, month_day=None, limit=None):
	_ensure_system_manager()
	_ensure_backup_fields()
	period = str(period or "Off").strip()
	if period not in PERIODS:
		frappe.throw(_("Choose Off, Daily, Weekly, or Monthly."))
	weekday = str(weekday or "Monday").strip()
	if weekday not in WEEKDAYS:
		frappe.throw(_("Choose a weekday."))
	day = cint(month_day) or 1
	if day < 1 or day > 28:
		frappe.throw(_("Monthly backups run on a day from 1 to 28."))
	keep = cint(limit) or 7
	if keep < 1 or keep > 90:
		frappe.throw(_("Keep between 1 and 90 dumps."))

	values = {
		"staff_pro_backup_period": period,
		"staff_pro_backup_weekday": weekday,
		"staff_pro_backup_month_day": day,
		"staff_pro_backup_limit": keep,
	}
	for fieldname, value in values.items():
		frappe.db.set_single_value("System Settings", fieldname, value)
	frappe.clear_cache(doctype="System Settings")
	return get_backup_state()


@frappe.whitelist()
def dump_now():
	_ensure_system_manager()
	path = take_database_dump()
	settings = _read_settings()
	prune_dumps(settings["limit"], keep_path=path)
	state = get_backup_state()
	state["filename"] = os.path.basename(path)
	return state


@frappe.whitelist()
def download_dump(filename):
	_ensure_system_manager()
	path = resolve_dump_path(backup_folder(), filename)
	with open(path, "rb") as handle:
		frappe.local.response.filename = os.path.basename(path)
		frappe.local.response.filecontent = handle.read()
		frappe.local.response.type = "download"


def take_database_dump() -> str:
	from frappe.utils.backups import new_backup

	# new_backup deletes files older than keep_backups_for_hours before it dumps.
	# Hold that cleanup back so the saved dump limit is what removes old files.
	had_limit = "keep_backups_for_hours" in frappe.conf
	previous_limit = frappe.conf.get("keep_backups_for_hours") if had_limit else None
	frappe.conf.keep_backups_for_hours = 24 * 366 * 90
	try:
		backup = new_backup(ignore_files=True, force=True)
	finally:
		if had_limit:
			frappe.conf.keep_backups_for_hours = previous_limit
		else:
			try:
				del frappe.conf["keep_backups_for_hours"]
			except Exception:
				frappe.conf.keep_backups_for_hours = None
	path = getattr(backup, "backup_path_db", None)
	if not path or not os.path.isfile(path):
		frappe.throw(_("The database dump did not finish."))
	real = os.path.realpath(path)
	folder = os.path.realpath(backup_folder())
	try:
		inside = os.path.commonpath([folder, real]) == folder
	except ValueError:
		inside = False
	if inside and is_database_dump(os.path.basename(real)):
		return real
	return resolve_dump_path(folder, os.path.basename(real))


def prune_dumps(limit, keep_path=None) -> None:
	keep = clamp_limit(limit)
	rows = _dump_files()
	rows.sort(key=lambda row: row["mtime"], reverse=True)
	keep_names = {row["filename"] for row in rows[:keep]}
	if keep_path:
		keep_names.add(os.path.basename(keep_path))
	for row in rows:
		if row["filename"] in keep_names:
			continue
		_remove_backup_file(row["path"], row["filename"])
	_prune_site_config_copies(keep)


def list_dump_rows() -> list[dict]:
	rows = _dump_files()
	rows.sort(key=lambda row: row["mtime"], reverse=True)
	return [
		{
			"filename": row["filename"],
			"created": format_datetime(row["created"]),
			"size": _format_size(row["size"]),
		}
		for row in rows
	]


def _prune_site_config_copies(limit: int) -> None:
	folder = backup_folder()
	rows = []
	try:
		names = os.listdir(folder)
	except OSError:
		return
	for name in names:
		lower = name.lower()
		if "site_config_backup" not in lower or not lower.endswith(".json"):
			continue
		path = os.path.join(folder, name)
		if not os.path.isfile(path):
			continue
		rows.append({"filename": name, "path": path, "mtime": os.stat(path).st_mtime})
	rows.sort(key=lambda row: row["mtime"], reverse=True)
	for row in rows[limit:]:
		_remove_backup_file(row["path"], row["filename"])


def _remove_backup_file(path: str, filename: str) -> None:
	try:
		os.remove(path)
	except OSError:
		frappe.log_error(title="Backup prune failed", message=filename)


def backup_folder() -> str:
	try:
		from frappe.utils.backups import get_backup_path

		folder = get_backup_path()
	except ImportError:
		folder = frappe.utils.get_site_path(frappe.conf.get("backup_path") or "private/backups")
	os.makedirs(folder, exist_ok=True)
	return folder


def _dump_files() -> list[dict]:
	folder = backup_folder()
	rows = []
	try:
		names = os.listdir(folder)
	except OSError:
		return rows
	for name in names:
		if not is_database_dump(name):
			continue
		path = os.path.join(folder, name)
		if not os.path.isfile(path):
			continue
		stat = os.stat(path)
		rows.append(
			{
				"filename": name,
				"path": path,
				"mtime": stat.st_mtime,
				"size": stat.st_size,
				"created": datetime.fromtimestamp(stat.st_mtime),
			}
		)
	return rows


def _read_settings() -> dict:
	return {
		"period": _field_value("staff_pro_backup_period", "Off"),
		"weekday": _field_value("staff_pro_backup_weekday", "Monday"),
		"month_day": clamp_month_day(_field_value("staff_pro_backup_month_day", 1)),
		"limit": clamp_limit(_field_value("staff_pro_backup_limit", 7)),
	}


def _field_value(fieldname: str, default):
	if not frappe.db.exists("DocType", "System Settings"):
		return default
	if not frappe.get_meta("System Settings").has_field(fieldname):
		return default
	value = frappe.db.get_single_value("System Settings", fieldname)
	return default if value in (None, "") else value


def _ensure_backup_fields() -> None:
	if frappe.get_meta("System Settings").has_field("staff_pro_backup_period"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	from hrms.setup import get_custom_fields

	fields = [
		field
		for field in get_custom_fields().get("System Settings", [])
		if str(field.get("fieldname") or "") in BACKUP_FIELDS
	]
	if not fields:
		frappe.throw(_("Backup settings are not available yet."))
	create_custom_fields({"System Settings": fields}, ignore_validate=True)
	frappe.clear_cache(doctype="System Settings")


def _ensure_system_manager() -> None:
	frappe.only_for("System Manager")


def _format_size(size: int) -> str:
	size = int(size or 0)
	if size < 1024:
		return _("{0} B").format(size)
	if size < 1024 * 1024:
		return _("{0} KB").format(f"{size / 1024:.1f}")
	return _("{0} MB").format(f"{size / (1024 * 1024):.1f}")
