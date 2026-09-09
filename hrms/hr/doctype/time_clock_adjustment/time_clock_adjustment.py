# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_time, getdate, now_datetime, strip_html

HR_ROLES = frozenset({"HR User", "HR Manager", "System Manager", "Administrator"})

_TIME_TOKEN = re.compile(
	r"(?i)(?<![A-Za-z0-9:])(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?(?![A-Za-z0-9:])"
)
_DURATION_AFTER = re.compile(r"(?i)^\s*(hours?|hrs?|minutes?|mins?)\b")
_LEAD_IN = re.compile(r"(?i)\b(at|around|by|to|until|till)\s+$")
_IN_HINT = re.compile(
	r"(?i)\b(clock(?:ed)?\s*in|check(?:ed)?\s*in|came\s+in|arrived|start(?:ed)?|in\s+time|in\s+at)\b"
)
_OUT_HINT = re.compile(
	r"(?i)\b(clock(?:ed)?\s*out|check(?:ed)?\s*out|left(?:\s+at)?|leave\s+at|finish(?:ed)?|end(?:ed)?|out\s+time|out\s+at)\b"
)


class TimeClockAdjustment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action: DF.Literal["Edit", "Add"]
		attendance: DF.Link | None
		attendance_date: DF.Date
		company: DF.Link | None
		current_in_time: DF.Time | None
		current_out_time: DF.Time | None
		department: DF.Link | None
		employee: DF.Link
		employee_name: DF.Data | None
		in_log: DF.Data | None
		note: DF.SmallText | None
		out_log: DF.Data | None
		requested_by: DF.Link | None
		requested_in_time: DF.Time | None
		requested_out_time: DF.Time | None
		reviewed_by: DF.Link | None
		reviewed_on: DF.Datetime | None
		status: DF.Literal["Pending", "Approved", "Rejected"]
	# end: auto-generated types

	def validate(self):
		self.attendance_date = getdate(self.attendance_date)
		employee = frappe.db.get_value(
			"Employee", self.employee, ["employee_name", "department", "company"], as_dict=True
		)
		if employee:
			self.employee_name = self.employee_name or employee.employee_name
			self.department = self.department or employee.department
			self.company = self.company or employee.company
		if not self.requested_by:
			self.requested_by = frappe.session.user
		if not self.action:
			self.action = "Edit" if self.attendance else "Add"
		if not is_hr_user():
			session_employee = get_session_employee()
			if session_employee != self.employee:
				frappe.throw(_("You can only request changes for your own time clock."), frappe.PermissionError)
			if self.status != "Pending":
				frappe.throw(_("You cannot review this request."))


def is_hr_user(user: str | None = None) -> bool:
	return bool(HR_ROLES.intersection(frappe.get_roles(user or frappe.session.user)))


def get_session_employee() -> str | None:
	from hrms.api import get_current_employee_info

	info = get_current_employee_info()
	return info.get("name") if info else None


def get_permission_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_hr_user(user):
		return ""
	employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	if not employee:
		return "1=0"
	return f"`tabTime Clock Adjustment`.employee = {frappe.db.escape(employee)}"


def has_permission(doc, ptype=None, user=None, debug=False) -> bool:
	user = user or frappe.session.user
	if is_hr_user(user):
		return True
	employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	return bool(employee and doc.employee == employee)


def time_to_str(value) -> str | None:
	if value in (None, ""):
		return None
	if isinstance(value, timedelta):
		total = int(value.total_seconds()) % (24 * 3600)
		hours, rem = divmod(total, 3600)
		minutes, seconds = divmod(rem, 60)
		return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
	if isinstance(value, datetime):
		return value.strftime("%H:%M:%S")
	text = str(value).strip()
	if not text:
		return None
	try:
		parsed = get_time(text)
	except Exception:
		return None
	if isinstance(parsed, timedelta):
		return time_to_str(parsed)
	if hasattr(parsed, "hour"):
		return f"{parsed.hour:02d}:{parsed.minute:02d}:{getattr(parsed, 'second', 0):02d}"
	return text


def _same_time(left, right) -> bool:
	a = time_to_str(left)
	b = time_to_str(right)
	if not a and not b:
		return True
	if not a or not b:
		return False
	return a[:5] == b[:5]


def _hour_from_current(value) -> int | None:
	text = time_to_str(value)
	if not text:
		return None
	return int(text.split(":")[0])


def parse_requested_times(note: str | None, current_in=None, current_out=None) -> dict[str, str | None]:
	"""Pull requested IN/OUT times from a free-text time-clock note."""
	text = strip_html(note or "").strip()
	if not text:
		return {"in_time": None, "out_time": None}

	has_in = bool(_IN_HINT.search(text))
	has_out = bool(_OUT_HINT.search(text))
	matches = []
	for match in _TIME_TOKEN.finditer(text):
		start = match.start()
		end = match.end()
		if _DURATION_AFTER.search(text[end:]):
			continue
		hour = int(match.group(1))
		minute = int(match.group(2) or 0)
		meridiem = (match.group(3) or "").lower().replace(".", "")
		has_minutes = bool(match.group(2))
		lead = text[max(0, start - 16) : start]
		if hour > 23 or minute > 59:
			continue
		if not has_minutes and not meridiem and not _LEAD_IN.search(lead):
			continue
		matches.append(
			{
				"hour": hour,
				"minute": minute,
				"meridiem": meridiem,
				"lead": lead.lower(),
				"start": start,
			}
		)

	if not matches:
		return {"in_time": None, "out_time": None}

	def _as_clock(item, role: str) -> str:
		hour = item["hour"]
		minute = item["minute"]
		meridiem = item["meridiem"]
		if meridiem.startswith("p") and hour < 12:
			hour += 12
		elif meridiem.startswith("a") and hour == 12:
			hour = 0
		elif not meridiem and hour <= 12:
			if role == "out":
				current_in_hour = _hour_from_current(current_in)
				if hour <= 7 or (current_in_hour is not None and hour < current_in_hour):
					hour += 12
			elif role == "in" and hour == 12:
				hour = 0
		return f"{hour:02d}:{minute:02d}:00"

	in_time = None
	out_time = None
	if len(matches) >= 2:
		first, second = matches[0], matches[1]
		first_out = bool(_OUT_HINT.search(first["lead"]))
		second_in = bool(_IN_HINT.search(second["lead"]))
		if first_out and not second_in:
			out_time = _as_clock(first, "out")
			in_time = _as_clock(second, "in")
		else:
			in_time = _as_clock(first, "in")
			out_time = _as_clock(second, "out")
	else:
		item = matches[0]
		lead_out = bool(_OUT_HINT.search(item["lead"]))
		lead_in = bool(_IN_HINT.search(item["lead"]))
		if lead_out or (has_out and not has_in) or (current_in and not current_out and not lead_in):
			out_time = _as_clock(item, "out")
		elif lead_in or has_in or not current_in:
			in_time = _as_clock(item, "in")
		else:
			out_time = _as_clock(item, "out")

	return {"in_time": in_time, "out_time": out_time}


def serialize_adjustment(doc) -> dict:
	return {
		"name": doc.name,
		"employee": doc.employee,
		"employee_name": doc.employee_name,
		"department": doc.department,
		"attendance_date": str(getdate(doc.attendance_date)) if doc.attendance_date else "",
		"attendance": doc.attendance,
		"action": doc.action,
		"in_log": doc.in_log,
		"out_log": doc.out_log,
		"current_in_time": time_to_str(doc.current_in_time),
		"current_out_time": time_to_str(doc.current_out_time),
		"requested_in_time": time_to_str(doc.requested_in_time),
		"requested_out_time": time_to_str(doc.requested_out_time),
		"note": doc.note,
		"status": doc.status,
		"requested_by": doc.requested_by,
		"reviewed_by": doc.reviewed_by,
		"reviewed_on": str(doc.reviewed_on) if doc.reviewed_on else None,
	}


def _pair_for_attendance(employee: str, attendance_date, attendance=None, in_log=None, out_log=None):
	from hrms.payroll.daily_pay import pair_checkin_logs

	if in_log:
		in_time = frappe.db.get_value("Employee Checkin", in_log, "time")
		out_time = frappe.db.get_value("Employee Checkin", out_log, "time") if out_log else None
		return in_log, out_log, in_time, out_time

	logs = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [f"{attendance_date} 00:00:00", f"{attendance_date} 23:59:59"]],
		},
		fields=["name", "log_type", "time"],
		order_by="time asc",
	)
	pairs = (pair_checkin_logs(logs) or {}).get("pairs") or []
	if not pairs:
		return None, None, getattr(attendance, "in_time", None), getattr(attendance, "out_time", None)

	chosen = pairs[0]
	if attendance and getattr(attendance, "in_time", None):
		target = time_to_str(attendance.in_time)
		for pair in pairs:
			if _same_time(pair.get("in_time"), target):
				chosen = pair
				break
	return chosen.get("in_log"), chosen.get("out_log"), chosen.get("in_time"), chosen.get("out_time")


def create_from_hours_note(
	attendance_name: str,
	note: str,
	requested_in_time: str | None = None,
	requested_out_time: str | None = None,
	in_log: str | None = None,
	out_log: str | None = None,
) -> dict | None:
	if not frappe.db.table_exists("Time Clock Adjustment"):
		return None

	attendance = frappe.db.get_value(
		"Attendance",
		attendance_name,
		["name", "employee", "attendance_date", "in_time", "out_time", "department", "company", "shift"],
		as_dict=True,
	)
	if not attendance:
		return None

	pair_in, pair_out, pair_in_time, pair_out_time = _pair_for_attendance(
		attendance.employee,
		attendance.attendance_date,
		attendance,
		in_log=in_log,
		out_log=out_log,
	)
	current_in = time_to_str(pair_in_time or attendance.in_time)
	current_out = time_to_str(pair_out_time or attendance.out_time)
	parsed = parse_requested_times(note, current_in, current_out)
	req_in = time_to_str(requested_in_time) or parsed.get("in_time")
	req_out = time_to_str(requested_out_time) or parsed.get("out_time")
	if not req_in and not req_out:
		return None
	if not req_in:
		req_in = current_in
	if not req_out and current_out:
		req_out = current_out
	if _same_time(req_in, current_in) and _same_time(req_out, current_out):
		return None

	values = {
		"employee": attendance.employee,
		"employee_name": frappe.db.get_value("Employee", attendance.employee, "employee_name"),
		"department": attendance.department,
		"company": attendance.company,
		"attendance_date": attendance.attendance_date,
		"attendance": attendance.name,
		"action": "Edit",
		"status": "Pending",
		"current_in_time": current_in,
		"current_out_time": current_out,
		"requested_in_time": req_in,
		"requested_out_time": req_out,
		"in_log": pair_in,
		"out_log": pair_out,
		"note": strip_html(note or "").strip(),
		"requested_by": frappe.session.user,
	}

	existing = frappe.db.exists(
		"Time Clock Adjustment",
		{
			"employee": attendance.employee,
			"attendance_date": attendance.attendance_date,
			"attendance": attendance.name,
			"status": "Pending",
		},
	)
	if existing:
		doc = frappe.get_doc("Time Clock Adjustment", existing)
		doc.update(values)
		doc.flags.ignore_permissions = True
		doc.save()
	else:
		doc = frappe.get_doc({"doctype": "Time Clock Adjustment", **values})
		doc.flags.ignore_permissions = True
		doc.insert()
	return serialize_adjustment(doc)


def pending_adjustments_for_rows(rows: list) -> dict[str, dict]:
	if not rows or not frappe.db.table_exists("Time Clock Adjustment"):
		return {}

	names = [row.get("name") for row in rows if row.get("name")]
	if not names:
		return {}

	found = frappe.get_all(
		"Time Clock Adjustment",
		filters={"attendance": ["in", names], "status": "Pending"},
		fields=[
			"name",
			"employee",
			"employee_name",
			"department",
			"attendance_date",
			"attendance",
			"action",
			"in_log",
			"out_log",
			"current_in_time",
			"current_out_time",
			"requested_in_time",
			"requested_out_time",
			"note",
			"status",
			"requested_by",
			"reviewed_by",
			"reviewed_on",
		],
		order_by="creation desc",
	)
	by_attendance: dict[str, dict] = {}
	for row in found:
		if row.attendance and row.attendance not in by_attendance:
			by_attendance[row.attendance] = serialize_adjustment(row)
	return by_attendance


def pending_by_employee_date(employees: list[str], on_date) -> dict[str, dict]:
	if not employees or not frappe.db.table_exists("Time Clock Adjustment"):
		return {}
	found = frappe.get_all(
		"Time Clock Adjustment",
		filters={
			"employee": ["in", employees],
			"attendance_date": getdate(on_date),
			"status": "Pending",
		},
		fields=[
			"name",
			"employee",
			"employee_name",
			"department",
			"attendance_date",
			"attendance",
			"action",
			"in_log",
			"out_log",
			"current_in_time",
			"current_out_time",
			"requested_in_time",
			"requested_out_time",
			"note",
			"status",
			"requested_by",
			"reviewed_by",
			"reviewed_on",
		],
		order_by="creation desc",
	)
	by_employee: dict[str, dict] = {}
	for row in found:
		if row.employee not in by_employee:
			by_employee[row.employee] = serialize_adjustment(row)
	return by_employee


def apply_time_clock_adjustment(doc) -> str:
	from hrms.hr.doctype.attendance.attendance import add_hours_entry, update_hours_entry

	attendance_date = getdate(doc.attendance_date)
	in_time = time_to_str(doc.requested_in_time) or time_to_str(doc.current_in_time)
	out_time = time_to_str(doc.requested_out_time) or time_to_str(doc.current_out_time)
	if not in_time:
		frappe.throw(_("Requested in time is required to apply this change."))
	working_now = 0 if out_time else 1
	comment = _("Approved time clock adjustment")
	if doc.note:
		comment = f"{comment}: {doc.note}"

	if (doc.action or "Edit") == "Add" or not doc.attendance:
		return add_hours_entry(
			doc.employee,
			attendance_date,
			in_time,
			out_time=out_time,
			comment=comment,
			working_now=working_now,
		)

	return update_hours_entry(
		doc.attendance,
		attendance_date,
		in_time,
		out_time=out_time,
		comment=comment,
		working_now=working_now,
		in_log=doc.in_log or None,
		out_log=doc.out_log or None,
	)


@frappe.whitelist()
def review_time_clock_adjustment(name: str, action: str, comment: str | None = None) -> dict:
	frappe.only_for(list(HR_ROLES))
	if not name:
		frappe.throw(_("Adjustment is required."))
	kind = (action or "").strip().lower()
	if kind not in ("approve", "reject"):
		frappe.throw(_("Action must be approve or reject."))

	doc = frappe.get_doc("Time Clock Adjustment", name)
	if doc.status != "Pending":
		frappe.throw(_("This request has already been reviewed."))

	if kind == "approve":
		attendance_name = apply_time_clock_adjustment(doc)
		doc.attendance = attendance_name or doc.attendance
		doc.status = "Approved"
		note = strip_html(comment or "").strip() or _("Time change approved.")
	else:
		doc.status = "Rejected"
		note = strip_html(comment or "").strip() or _("Time change rejected.")

	doc.reviewed_by = frappe.session.user
	doc.reviewed_on = now_datetime()
	doc.flags.ignore_permissions = True
	doc.save()

	if doc.attendance:
		from hrms.hr.doctype.attendance.attendance import _add_hours_comment

		_add_hours_comment(doc.attendance, note)
	return serialize_adjustment(doc)


@frappe.whitelist()
def get_time_clock_adjustments(
	status: str | None = None,
	department: str | None = None,
	from_date: str | date | None = None,
	to_date: str | date | None = None,
) -> dict:
	frappe.only_for(list(HR_ROLES))
	filters: dict = {}
	selected = (status or "Pending").strip()
	if selected and selected != "All":
		filters["status"] = selected
	if department and department != "__none__":
		filters["department"] = department
	elif department == "__none__":
		filters["department"] = ["in", ["", None]]
	if from_date and to_date:
		filters["attendance_date"] = ["between", [getdate(from_date), getdate(to_date)]]
	elif from_date:
		filters["attendance_date"] = [">=", getdate(from_date)]
	elif to_date:
		filters["attendance_date"] = ["<=", getdate(to_date)]

	rows = frappe.get_all(
		"Time Clock Adjustment",
		filters=filters,
		fields=[
			"name",
			"employee",
			"employee_name",
			"department",
			"attendance_date",
			"attendance",
			"action",
			"in_log",
			"out_log",
			"current_in_time",
			"current_out_time",
			"requested_in_time",
			"requested_out_time",
			"note",
			"status",
			"requested_by",
			"reviewed_by",
			"reviewed_on",
			"creation",
		],
		order_by="attendance_date desc, creation desc",
		limit=200,
	)
	departments = sorted(
		{
			row
			for row in frappe.get_all(
				"Time Clock Adjustment",
				pluck="department",
				distinct=True,
			)
			if row
		}
	)
	return {
		"rows": [serialize_adjustment(row) for row in rows],
		"departments": departments,
		"status": selected,
	}
