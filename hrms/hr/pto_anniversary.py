# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Paid holiday: 10 days after 3 months, paid out on each work anniversary, never carried forward."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, add_months, flt, getdate

PTO_LEAVE_TYPE = "Paid Holiday"
PTO_DAYS = 10
WAIT_MONTHS = 3
PAYOUT_COMPONENT = "PTO Payout"


def process_pto_anniversaries(as_of=None, employee: str | None = None) -> None:
	"""Daily job: grant the current work year and pay unused days from the year that just ended."""
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
		eligible_on = add_months(joining, WAIT_MONTHS)
		if today < eligible_on:
			continue

		frappe.db.savepoint("pto_anniversary_employee")
		try:
			_pay_ended_allocations(emp, today)
			_ensure_current_allocation(emp, today, joining, eligible_on)
		except Exception:
			frappe.db.rollback(save_point="pto_anniversary_employee")
			frappe.log_error(title=_("Paid holiday anniversary failed for {0}").format(emp.name))


def ensure_paid_holiday_leave_type() -> str:
	"""Paid Holiday does not carry into the next work year."""
	ensure_pto_payout_component()
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
		if doc.earning_component != PAYOUT_COMPONENT and frappe.db.exists("Salary Component", PAYOUT_COMPONENT):
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
			"description": "Unused paid holiday paid on the next payroll after a work anniversary.",
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
		start, end = getdate(entry.start_date), getdate(entry.end_date)
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
		if existing.docstatus == 0:
			frappe.get_doc("Additional Salary", existing.name).submit()
		return

	days = unused_pto_days(allocation)
	amount = pto_money_value(emp.name, days)
	if amount <= 0:
		return

	currency = (
		frappe.db.get_value("Company", emp.company, "default_currency") if emp.company else None
	) or "BZD"
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
			"overwrite_salary_structure_amount": 0,
			"ref_doctype": "Leave Allocation",
			"ref_docname": allocation.name,
			"is_recurring": 0,
		}
	)
	additional_salary.flags.ignore_permissions = True
	additional_salary.insert()
	additional_salary.submit()


def _ensure_current_allocation(emp, today, joining, eligible_on) -> None:
	year_start, year_end = work_year_bounds(joining, today)
	grant_from = eligible_on if eligible_on > year_start else year_start
	grant_to = year_end
	if grant_from > grant_to or grant_from > today:
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

	allocation = frappe.get_doc(
		{
			"doctype": "Leave Allocation",
			"employee": emp.name,
			"company": emp.company,
			"leave_type": PTO_LEAVE_TYPE,
			"from_date": grant_from,
			"to_date": grant_to,
			"new_leaves_allocated": PTO_DAYS,
			"carry_forward": 0,
		}
	)
	allocation.flags.ignore_permissions = True
	allocation.insert()
	allocation.submit()


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
