# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Staff Pro always runs on America/Belize. Never use the browser or UTC clock."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import frappe
from frappe.utils import get_datetime

from hrms.branding import STAFF_PRO_TIMEZONE


def belize_tz():
	return ZoneInfo(STAFF_PRO_TIMEZONE)


def belize_now() -> datetime:
	"""Naive Belize wall-clock now. This is what Frappe stores for Datetime fields."""
	return datetime.now(belize_tz()).replace(tzinfo=None, microsecond=0)


def belize_today():
	return belize_now().date()


def apply_request_timezone() -> None:
	"""Force this request to treat 'now' as Belize, even if cache still has another zone."""
	if getattr(frappe, "conf", None) is not None:
		frappe.conf["time_zone"] = STAFF_PRO_TIMEZONE

	settings = getattr(frappe.local, "system_settings", None)
	if settings is not None:
		settings.time_zone = STAFF_PRO_TIMEZONE
		return

	if not getattr(frappe, "db", None):
		return
	try:
		settings = frappe.get_cached_doc("System Settings")
	except Exception:
		return
	settings.time_zone = STAFF_PRO_TIMEZONE
	frappe.local.system_settings = settings


def lock_user_timezone(doc, method: str | None = None) -> None:
	"""Users cannot pick a personal timezone. Desk and clock-in stay on Belize."""
	if not doc.meta.has_field("time_zone"):
		return
	doc.time_zone = STAFF_PRO_TIMEZONE


def lock_all_user_timezones() -> None:
	if not frappe.db.exists("DocType", "User"):
		return
	if not frappe.get_meta("User").has_field("time_zone"):
		return

	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	frappe.db.sql(
		"""
		update `tabUser`
		set time_zone = %s
		where ifnull(time_zone, '') != %s
		""",
		(STAFF_PRO_TIMEZONE, STAFF_PRO_TIMEZONE),
	)
	make_property_setter(
		"User",
		"time_zone",
		"read_only",
		1,
		"Check",
		validate_fields_for_doctype=False,
	)
	make_property_setter(
		"User",
		"time_zone",
		"default",
		STAFF_PRO_TIMEZONE,
		"Text",
		validate_fields_for_doctype=False,
	)
	frappe.clear_cache(doctype="User")


def stamp_live_checkin_time(doc) -> None:
	"""Live punches use Belize now. Explicit backdated times from admin/tests are kept."""
	apply_request_timezone()
	now = belize_now()
	if getattr(doc.flags, "staff_pro_live_clock", False) or not doc.time:
		doc.time = now
		return

	submitted = get_datetime(doc.time).replace(microsecond=0)
	if doc.is_new() and submitted == frappe.utils.now_datetime().replace(microsecond=0):
		doc.time = now
		return
	doc.time = submitted
