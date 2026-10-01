# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Vacation accrues from hours worked after 2 weeks and becomes usable on each work anniversary.

The grant looks back one year only, is capped (default 10 days), and unused granted days
are paid out on the next anniversary. Time cannot be taken before 1 year of continuous service,
and only one week at a time.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate

PTO_LEAVE_TYPE = "Paid Holiday"
PAYOUT_COMPONENT = "PTO Payout"
ONE_WEEK_DAYS = 5
APPLICABLE_AFTER_DAYS = 365

DEFAULT_WAIT_DAYS = 14
DEFAULT_MINUTES = 15
DEFAULT_HOURS_PER_UNIT = 8
DEFAULT_MAX_DAYS = 10


def process_pto_anniversaries(as_of=None, employee: str | None = None) -> None:
	"""Daily job: on each work anniversary, pay unused vacation and grant the lookback year."""
	if not frappe.db.table_exists("Employee") or not frappe.db.table_exists("Leave Allocation"):
		return

	ensure_paid_holiday_leave_type()
	today = getdate(as_of or getattr(frappe.flags, "current_date", None) or getdate())
	for emp in _employees(employee):
		joining = getdate(emp.date_of_joining) if emp.date_of_joining else None
		if not joining:
			continue
		if emp.relieving_date and getdate(emp.relieving_date) < today:
			continue
		if today < first_anniversary(joining):
			continue

		frappe.db.savepoint("pto_anniversary_employee")
		try:
			_pay_ended_allocations(emp, today)
			_ensure_current_allocation(emp, today, joining)
		except Exception:
			frappe.db.rollback(save_point="pto_anniversary_employee")
			frappe.log_error(title=_("Vacation anniversary failed for {0}").format(emp.name))


def vacation_settings() -> dict:
	"""Accrual rate from HR Settings, with the policy defaults when a field is blank."""
	wait_days = cint(_hr_setting("vacation_accrual_wait_days", DEFAULT_WAIT_DAYS))
	minutes = flt(_hr_setting("vacation_minutes_per_hours_worked", DEFAULT_MINUTES))
	hours_per_unit = flt(_hr_setting("vacation_hours_per_accrual_unit", DEFAULT_HOURS_PER_UNIT))
	max_days = flt(_hr_setting("vacation_max_days", DEFAULT_MAX_DAYS))
	return {
		"wait_days": wait_days if wait_days >= 0 else DEFAULT_WAIT_DAYS,
		"minutes": minutes if minutes > 0 else DEFAULT_MINUTES,
		"hours_per_unit": hours_per_unit if hours_per_unit > 0 else DEFAULT_HOURS_PER_UNIT,
		"max_days": max_days if max_days > 0 else DEFAULT_MAX_DAYS,
	}


def first_anniversary(joining):
	"""First date the employee has 1 full year of continuous service."""
	joining = getdate(joining)
	return _anniversary(joining, joining.year + 1)


def assert_can_take_vacation(employee: str, leave_type: str, on_date) -> None:
	"""Block Paid Holiday before 1 year. One week at a time is enforced on the leave type."""
	if leave_type != PTO_LEAVE_TYPE or not employee:
		return
	joining = frappe.db.get_value("Employee", employee, "date_of_joining")
	if not joining or getdate(on_date) < first_anniversary(joining):
		frappe.throw(
			_("Vacation can be taken after 1 year of continuous service, and only one week at a time.")
		)


def vacation_balance(employee: str, as_of=None) -> dict:
	"""Usable days were granted on the last anniversary. Accruing days are not bookable yet."""
	as_of = getdate(as_of or getattr(frappe.flags, "current_date", None) or getdate())
	empty = {"usable_days": 0.0, "accruing_days": 0.0, "granted_days": 0.0, "eligible": 0}
	joining = frappe.db.get_value("Employee", employee, "date_of_joining") if employee else None
	if not joining:
		return empty

	joining = getdate(joining)
	settings = vacation_settings()
	accrual_start = add_days(joining, settings["wait_days"])
	eligible = as_of >= first_anniversary(joining)
	usable = 0.0
	granted = 0.0

	if eligible and frappe.db.table_exists("Leave Allocation"):
		allocation = frappe.db.get_value(
			"Leave Allocation",
			{
				"employee": employee,
				"leave_type": PTO_LEAVE_TYPE,
				"docstatus": 1,
				"from_date": ["<=", as_of],
				"to_date": [">=", as_of],
			},
			["name", "employee", "leave_type", "from_date", "to_date", "new_leaves_allocated"],
			as_dict=True,
		)
		if allocation:
			granted = flt(allocation.new_leaves_allocated)
			try:
				usable = unused_pto_days(allocation)
			except Exception:
				usable = granted
		year_start, _year_end = work_year_bounds(joining, as_of)
		accruing_from = year_start if year_start > accrual_start else accrual_start
	else:
		accruing_from = accrual_start

	accruing = 0.0
	if accruing_from <= as_of:
		accruing = accrued_vacation_days(employee, accruing_from, as_of)

	return {
		"usable_days": flt(usable, 2),
		"accruing_days": flt(accruing, 2),
		"granted_days": flt(granted, 2),
		"eligible": 1 if eligible else 0,
	}


def accrued_vacation_days(employee: str, from_date, to_date) -> float:
	"""Convert hours worked in the window into vacation days, capped at the yearly maximum."""
	settings = vacation_settings()
	hours = hours_worked(employee, from_date, to_date)
	day_hours = shift_hours(employee)
	if day_hours <= 0:
		day_hours = 8
	days = (hours / settings["hours_per_unit"]) * (settings["minutes"] / 60) / day_hours
	return min(flt(days, 2), flt(settings["max_days"], 2))


def hours_worked(employee: str, from_date, to_date) -> float:
	"""Present, half day, and work-from-home hours. Leave days do not accrue vacation."""
	if not employee or not frappe.db.table_exists("Attendance"):
		return 0.0
	from_date = getdate(from_date)
	to_date = getdate(to_date)
	if to_date < from_date:
		return 0.0

	rows = frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"docstatus": ["<", 2],
			"attendance_date": ["between", [from_date, to_date]],
			"status": ["in", ["Present", "Half Day", "Work From Home"]],
		},
		fields=["working_hours", "status"],
	)
	fallback = shift_hours(employee)
	total = 0.0
	for row in rows:
		hours = flt(row.working_hours)
		if not hours:
			hours = fallback / 2 if row.status == "Half Day" else fallback
		total += hours
	return flt(total, 2)


def ensure_paid_holiday_leave_type() -> str:
	"""Paid Holiday does not carry forward. It can be taken after 1 year, one week at a time."""
	ensure_pto_payout_component()
	settings = vacation_settings()
	max_days = flt(settings["max_days"])
	if frappe.db.exists("Leave Type", PTO_LEAVE_TYPE):
		doc = frappe.get_doc("Leave Type", PTO_LEAVE_TYPE)
		changed = False
		if cint_flag(doc.is_carry_forward):
			doc.is_carry_forward = 0
			changed = True
		if cint_flag(doc.is_lwp):
			doc.is_lwp = 0
			changed = True
		if not cint_flag(doc.allow_encashment):
			doc.allow_encashment = 1
			changed = True
		if cint(doc.applicable_after) != APPLICABLE_AFTER_DAYS:
			doc.applicable_after = APPLICABLE_AFTER_DAYS
			changed = True
		if cint(doc.max_continuous_days_allowed) != ONE_WEEK_DAYS:
			doc.max_continuous_days_allowed = ONE_WEEK_DAYS
			changed = True
		if flt(doc.max_leaves_allowed) != max_days:
			doc.max_leaves_allowed = max_days
			changed = True
		if not doc.earning_component and frappe.db.exists("Salary Component", PAYOUT_COMPONENT):
			doc.earning_component = PAYOUT_COMPONENT
			changed = True
		if changed:
			doc.flags.ignore_permissions = True
			doc.save()
		return doc.name

	doc = frappe.get_doc(
		{
			"doctype": "Leave Type",
			"leave_type_name": PTO_LEAVE_TYPE,
			"is_carry_forward": 0,
			"is_lwp": 0,
			"allow_encashment": 1,
			"include_holiday": 0,
			"applicable_after": APPLICABLE_AFTER_DAYS,
			"max_continuous_days_allowed": ONE_WEEK_DAYS,
			"max_leaves_allowed": max_days,
			"earning_component": PAYOUT_COMPONENT
			if frappe.db.exists("Salary Component", PAYOUT_COMPONENT)
			else None,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def ensure_pto_payout_component() -> str:
	if not frappe.db.table_exists("Salary Component"):
		return PAYOUT_COMPONENT
	if frappe.db.exists("Salary Component", PAYOUT_COMPONENT):
		return PAYOUT_COMPONENT

	doc = frappe.get_doc(
		{
			"doctype": "Salary Component",
			"salary_component": PAYOUT_COMPONENT,
			"salary_component_abbr": "PTOP",
			"type": "Earning",
			"is_tax_applicable": 1,
			"earning_category": "Regular",
			"depends_on_payment_days": 0,
			"do_not_include_in_total": 0,
			"remove_if_zero_valued": 0,
			"description": "Unused vacation paid on the next payroll after a work anniversary.",
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return PAYOUT_COMPONENT


def pto_money_value(employee: str, days: float | int | None) -> float:
	"""Remaining days valued at the agent's shift length times hourly rate."""
	days = flt(days)
	if days <= 0 or not employee:
		return 0.0
	return flt(days * shift_hours(employee) * hourly_rate(employee), 2)


def shift_hours(employee: str) -> float:
	shift = frappe.db.get_value("Employee", employee, "default_shift")
	if shift and frappe.db.exists("Shift Type", shift):
		start, end = frappe.db.get_value("Shift Type", shift, ["start_time", "end_time"])
		hours = _hours_between(start, end)
		if hours > 0:
			return hours

	weekly = flt(frappe.db.get_single_value("HR Settings", "standard_working_hours")) or 40
	daily = flt(weekly / 5)
	return daily if daily > 0 else 8


def hourly_rate(employee: str) -> float:
	return flt(frappe.db.get_value("Employee", employee, "ctc"))


def work_year_bounds(joining, on_date) -> tuple:
	"""Work year runs from the joining anniversary through the day before the next one."""
	joining = getdate(joining)
	on_date = getdate(on_date)
	this_anniversary = _anniversary(joining, on_date.year)
	if on_date >= this_anniversary:
		start = this_anniversary
		end = add_days(_anniversary(joining, on_date.year + 1), -1)
	else:
		start = _anniversary(joining, on_date.year - 1)
		end = add_days(this_anniversary, -1)
	if start < joining:
		start = joining
	return start, end


def lookback_window(joining, on_date) -> tuple | None:
	"""Past year of accrual that becomes usable on the anniversary currently in effect."""
	joining = getdate(joining)
	on_date = getdate(on_date)
	anniversary = _completed_anniversary(joining, on_date)
	if not anniversary:
		return None

	settings = vacation_settings()
	accrual_start = add_days(joining, settings["wait_days"])
	previous = _anniversary(joining, anniversary.year - 1)
	start = accrual_start if accrual_start > previous else previous
	if start < accrual_start:
		start = accrual_start
	end = add_days(anniversary, -1)
	if start > end:
		return None
	return start, end


def unused_pto_days(allocation) -> float:
	"""Allocated days minus days taken. Expiry entries are ignored so a prior expiry cannot zero the payout."""
	from hrms.hr.doctype.leave_application.leave_application import get_leaves_for_period

	taken = get_leaves_for_period(
		allocation.employee,
		allocation.leave_type or PTO_LEAVE_TYPE,
		allocation.from_date,
		allocation.to_date,
		skip_expired_leaves=True,
	)
	return max(flt(allocation.new_leaves_allocated) + flt(taken), 0)


def next_payroll_date(company: str | None, as_of):
	"""A date inside the next payroll period that has not been submitted yet."""
	as_of = getdate(as_of)
	if not company or not frappe.db.table_exists("Payroll Entry"):
		return as_of

	from hrms.payroll.auto_payroll import get_last_payroll_end, get_open_entries

	for entry in get_open_entries(company):
		start = getdate(entry.start_date)
		end = getdate(entry.end_date)
		if end < as_of:
			continue
		if start <= as_of <= end:
			return as_of
		if start > as_of:
			return start

	last_end = get_last_payroll_end(company)
	if last_end and getdate(last_end) >= as_of:
		return add_days(getdate(last_end), 1)
	return as_of


def cancel_premature_vacation_allocations(as_of=None) -> int:
	"""Cancel unused Paid Holiday grants for people who do not yet have 1 year of service."""
	if not frappe.db.table_exists("Leave Allocation"):
		return 0

	today = getdate(as_of or getdate())
	cancelled = 0
	allocations = frappe.get_all(
		"Leave Allocation",
		filters={"leave_type": PTO_LEAVE_TYPE, "docstatus": 1},
		fields=["name", "employee", "from_date", "to_date"],
	)
	for row in allocations:
		joining = frappe.db.get_value("Employee", row.employee, "date_of_joining")
		if not joining or today >= first_anniversary(joining):
			continue
		taken = 0
		if frappe.db.table_exists("Leave Application"):
			taken = frappe.db.count(
				"Leave Application",
				{
					"employee": row.employee,
					"leave_type": PTO_LEAVE_TYPE,
					"docstatus": 1,
					"from_date": ["<=", row.to_date],
					"to_date": [">=", row.from_date],
				},
			)
		if taken:
			continue
		try:
			doc = frappe.get_doc("Leave Allocation", row.name)
			doc.flags.ignore_permissions = True
			doc.cancel()
			cancelled += 1
		except Exception:
			frappe.log_error(title=_("Could not cancel early vacation allocation {0}").format(row.name))
	return cancelled


def _employees(employee: str | None) -> list:
	filters = {"status": "Active"}
	if employee:
		filters["name"] = employee
	return frappe.get_all(
		"Employee",
		filters=filters,
		fields=["name", "employee_name", "company", "date_of_joining", "relieving_date", "default_shift", "ctc"],
	)


def _pay_ended_allocations(emp, today) -> None:
	allocations = frappe.get_all(
		"Leave Allocation",
		filters={
			"employee": emp.name,
			"leave_type": PTO_LEAVE_TYPE,
			"docstatus": 1,
			"to_date": ["<", today],
		},
		fields=["name", "employee", "leave_type", "from_date", "to_date", "new_leaves_allocated"],
	)
	for allocation in allocations:
		_pay_allocation(emp, allocation, today)


def _pay_allocation(emp, allocation, today) -> None:
	existing = frappe.db.get_value(
		"Additional Salary",
		{
			"ref_doctype": "Leave Allocation",
			"ref_docname": allocation.name,
			"docstatus": ["!=", 2],
		},
		["name", "docstatus"],
		as_dict=True,
	)
	if existing:
		if cint(existing.docstatus) == 0:
			draft = frappe.get_doc("Additional Salary", existing.name)
			draft.flags.ignore_permissions = True
			draft.submit()
		return

	days = unused_pto_days(allocation)
	if days <= 0:
		return
	amount = pto_money_value(emp.name, days)
	if amount <= 0:
		return

	currency = frappe.db.get_value("Company", emp.company, "default_currency") or "BZD"
	payroll_date = next_payroll_date(emp.company, today)
	additional_salary = frappe.get_doc(
		{
			"doctype": "Additional Salary",
			"employee": emp.name,
			"company": emp.company,
			"salary_component": PAYOUT_COMPONENT,
			"payroll_date": payroll_date,
			"amount": amount,
			"currency": currency,
			"overwrite_salary_structure_amount": 1,
			"ref_doctype": "Leave Allocation",
			"ref_docname": allocation.name,
			"is_recurring": 0,
		}
	)
	additional_salary.flags.ignore_permissions = True
	additional_salary.insert()
	additional_salary.submit()


def _ensure_current_allocation(emp, today, joining) -> None:
	if today < first_anniversary(joining):
		return

	year_start, year_end = work_year_bounds(joining, today)
	if year_start < first_anniversary(joining) or year_start > year_end:
		return

	covering_today = frappe.db.exists(
		"Leave Allocation",
		{
			"employee": emp.name,
			"leave_type": PTO_LEAVE_TYPE,
			"docstatus": 1,
			"from_date": ["<=", today],
			"to_date": [">=", today],
		},
	)
	if covering_today:
		return

	window = lookback_window(joining, today)
	if not window:
		return
	days = accrued_vacation_days(emp.name, window[0], window[1])
	if days <= 0:
		return

	allocation = frappe.get_doc(
		{
			"doctype": "Leave Allocation",
			"employee": emp.name,
			"company": emp.company,
			"leave_type": PTO_LEAVE_TYPE,
			"from_date": year_start,
			"to_date": year_end,
			"new_leaves_allocated": days,
			"carry_forward": 0,
		}
	)
	allocation.flags.ignore_permissions = True
	allocation.insert()
	allocation.submit()


def _completed_anniversary(joining, on_date):
	"""Most recent anniversary on or before on_date, once a full year has been completed."""
	joining = getdate(joining)
	on_date = getdate(on_date)
	this_year = _anniversary(joining, on_date.year)
	if on_date >= this_year and this_year > joining:
		return this_year
	prior = _anniversary(joining, on_date.year - 1)
	if on_date >= prior and prior > joining:
		return prior
	return None


def _anniversary(joining, year: int):
	joining = getdate(joining)
	try:
		return joining.replace(year=year)
	except ValueError:
		return joining.replace(year=year, day=28)


def _hours_between(start, end) -> float:
	start_seconds = _to_seconds(start)
	end_seconds = _to_seconds(end)
	if start_seconds is None or end_seconds is None:
		return 0
	diff = end_seconds - start_seconds
	if diff <= 0:
		diff += 24 * 3600
	return flt(diff / 3600, 2)


def _to_seconds(value) -> float | None:
	if value is None or value == "":
		return None
	if hasattr(value, "total_seconds"):
		return float(value.total_seconds())
	if hasattr(value, "hour"):
		return float(value.hour * 3600 + value.minute * 60 + value.second)
	text = str(value)
	parts = text.split(":")
	if len(parts) < 2:
		return None
	seconds = int(float(parts[2])) if len(parts) > 2 else 0
	return int(parts[0]) * 3600 + int(parts[1]) * 60 + seconds


def cint_flag(value) -> int:
	return 1 if value else 0


def _hr_setting(fieldname: str, default):
	try:
		meta = frappe.get_meta("HR Settings")
	except Exception:
		return default
	if not meta.has_field(fieldname):
		return default
	value = frappe.db.get_single_value("HR Settings", fieldname)
	if value in (None, ""):
		return default
	return value
