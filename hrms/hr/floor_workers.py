# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Floor workers: scheduled hours, working days, and the floorworkers tag."""

from __future__ import annotations

from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_time, getdate, nowdate

FLOOR_WORKER_TAG = "floorworkers"
LOOKBACK_DAYS = 14

WORK_DAY_FIELDS = (
	"work_monday",
	"work_tuesday",
	"work_wednesday",
	"work_thursday",
	"work_friday",
	"work_saturday",
	"work_sunday",
)

# Monday=0 … Sunday=6, matching datetime.weekday().
WEEKDAY_FIELDS = {index: field for index, field in enumerate(WORK_DAY_FIELDS)}

WEEKDAY_DEFAULTS = {
	"work_monday": 1,
	"work_tuesday": 1,
	"work_wednesday": 1,
	"work_thursday": 1,
	"work_friday": 1,
	"work_saturday": 0,
	"work_sunday": 0,
}

DEFAULT_START = "08:00:00"
DEFAULT_END = "17:00:00"


def apply_employee_floor_worker_rules(doc) -> None:
	"""Keep the tag, working days, and client-billing fields consistent on save."""
	meta = getattr(doc, "meta", None) or frappe.get_meta("Employee")
	if not meta.has_field("work_monday"):
		return

	if _should_fill_working_days(doc):
		defaults = group_working_days() if cint(doc.get("is_floor_worker")) else dict(WEEKDAY_DEFAULTS)
		for field, value in defaults.items():
			if meta.has_field(field):
				doc.set(field, value)

	if not meta.has_field("is_floor_worker"):
		return

	if cint(doc.get("is_floor_worker")):
		if meta.has_field("bill_to_customer"):
			doc.bill_to_customer = None
		if meta.has_field("billing_rate"):
			doc.billing_rate = 0
		if meta.has_field("default_shift"):
			doc.default_shift = None
		_set_tag(doc, FLOOR_WORKER_TAG, present=True)
	else:
		_set_tag(doc, FLOOR_WORKER_TAG, present=False)


def employee_works_on(employee, day) -> bool:
	field = WEEKDAY_FIELDS.get(getdate(day).weekday())
	if not field:
		return False
	return bool(cint(employee.get(field) if not isinstance(employee, str) else _day_value(employee, field)))


def effective_times(employee) -> tuple[str, str]:
	"""Individual times win. Otherwise use the Floor Worker group times in HR Settings."""
	start = _time_str(employee.get("floor_worker_start_time")) if hasattr(employee, "get") else ""
	end = _time_str(employee.get("floor_worker_end_time")) if hasattr(employee, "get") else ""
	group_start, group_end = group_times()
	return start or group_start, end or group_end


def group_times() -> tuple[str, str]:
	settings = _hr_settings()
	return (
		_time_str(settings.get("floor_worker_start_time")) or DEFAULT_START,
		_time_str(settings.get("floor_worker_end_time")) or DEFAULT_END,
	)


def group_working_days() -> dict[str, int]:
	settings = _hr_settings()
	days = {}
	for field, fallback in WEEKDAY_DEFAULTS.items():
		raw = settings.get(f"floor_{field}")
		days[field] = fallback if raw in (None, "") else cint(raw)
	return days


def run_scheduled_floor_worker_hours():
	"""Daily job: fill recent scheduled days that have no attendance yet."""
	today = getdate(nowdate())
	return ensure_floor_worker_hours(add_days(today, -LOOKBACK_DAYS), today)


def ensure_floor_worker_hours(
	from_date,
	to_date,
	employee: str | None = None,
) -> list[str]:
	"""Create scheduled attendance for floor workers. Existing days are left alone."""
	if not frappe.get_meta("Employee").has_field("is_floor_worker"):
		return []

	from_date = getdate(from_date)
	to_date = getdate(to_date)
	if from_date > to_date:
		return []

	filters = {"status": "Active", "is_floor_worker": 1}
	if employee:
		filters["name"] = employee

	fields = [
		"name",
		"date_of_joining",
		"relieving_date",
		"floor_worker_start_time",
		"floor_worker_end_time",
		*WORK_DAY_FIELDS,
	]
	workers = frappe.get_all("Employee", filters=filters, fields=fields)
	created = []
	for worker in workers:
		created.extend(_fill_worker(worker, from_date, to_date))
	return created


@frappe.whitelist()
def get_floor_worker_group_defaults() -> dict:
	"""Desk form: group start, end, and working days for a new Floor Worker."""
	if not frappe.has_permission("Employee", "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	start, end = group_times()
	return {"start_time": start, "end_time": end, "working_days": group_working_days()}


def is_floor_worker(employee: str | None) -> bool:
	if not employee or not frappe.get_meta("Employee").has_field("is_floor_worker"):
		return False
	return bool(cint(frappe.db.get_value("Employee", employee, "is_floor_worker")))


def _fill_worker(worker, from_date: date, to_date: date) -> list[str]:
	from hrms.hr.doctype.attendance.attendance import add_hours_entry

	start, end = effective_times(worker)
	joining = getdate(worker.date_of_joining) if worker.date_of_joining else None
	relieving = getdate(worker.relieving_date) if worker.relieving_date else None
	created = []
	day = from_date
	while day <= to_date:
		if joining and day < joining:
			day = add_days(day, 1)
			continue
		if relieving and day > relieving:
			break
		if not employee_works_on(worker, day):
			day = add_days(day, 1)
			continue
		if _day_already_marked(worker.name, day):
			day = add_days(day, 1)
			continue
		try:
			name = add_hours_entry(worker.name, day, start, end)
		except Exception:
			frappe.log_error(title=f"Floor worker hours {worker.name} {day}")
		else:
			if name:
				created.append(name)
		day = add_days(day, 1)
	return created


def _day_already_marked(employee: str, day: date) -> bool:
	return bool(
		frappe.db.exists(
			"Attendance",
			{
				"employee": employee,
				"attendance_date": day,
				"docstatus": ("<", 2),
			},
		)
	)


def _working_days_unset(doc) -> bool:
	return all(not cint(doc.get(field)) for field in WORK_DAY_FIELDS)


def _matches_weekday_defaults(doc) -> bool:
	return all(cint(doc.get(field)) == value for field, value in WEEKDAY_DEFAULTS.items())


def _should_fill_working_days(doc) -> bool:
	if _working_days_unset(doc):
		return True
	# A new Floor Worker left on Mon–Fri still inherits the group schedule.
	return bool(
		cint(doc.get("is_floor_worker"))
		and doc.is_new()
		and _matches_weekday_defaults(doc)
	)


def _day_value(employee: str, field: str) -> int:
	if not frappe.get_meta("Employee").has_field(field):
		return 0
	return cint(frappe.db.get_value("Employee", employee, field))


def _hr_settings() -> dict:
	try:
		return frappe.db.get_singles_dict("HR Settings") or {}
	except Exception:
		return {}


def _time_str(value) -> str:
	if not value:
		return ""
	if isinstance(value, timedelta):
		total = int(value.total_seconds())
		hours, remainder = divmod(total, 3600)
		minutes, seconds = divmod(remainder, 60)
		return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
	try:
		return get_time(value).strftime("%H:%M:%S")
	except Exception:
		text = str(value).strip()
		return text if text else ""


def _parse_tags(value) -> list[str]:
	return [part.strip() for part in (value or "").split(",") if part.strip()]


def _set_tag(doc, tag: str, present: bool) -> None:
	tags = _parse_tags(doc.get("_user_tags"))
	if present and tag not in tags:
		tags.append(tag)
	if not present:
		tags = [item for item in tags if item != tag]
	doc._user_tags = f",{','.join(tags)}," if tags else ""
