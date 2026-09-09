# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""BPO user bonus: admin sets amount, months, and attendance target on the agent."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_months, cint, date_diff, flt, getdate

DEFAULT_PERIOD_MONTHS = 3
DEFAULT_ATTENDANCE_TARGET = 90
DEFAULT_IF_BELOW = "No Bonus"


def evaluate_attendance_plan(attendance_pct, target_pct, target_amount, months, if_below):
	"""Return period share, eligibility, and whether payroll should deduct."""
	share = flt(flt(target_amount) / max(cint(months), 1), 2)
	meets = flt(attendance_pct, 2) >= flt(target_pct, 2)
	if meets:
		return {"eligible": 1, "amount": share, "is_deduction": 0}
	if (if_below or DEFAULT_IF_BELOW) == "Deduct":
		return {"eligible": 0, "amount": share, "is_deduction": 1}
	return {"eligible": 0, "amount": 0, "is_deduction": 0}


def plan_window(as_of_date, months, date_of_joining=None):
	end = getdate(as_of_date)
	start = add_months(end, -(cint(months) or DEFAULT_PERIOD_MONTHS))
	joining = getdate(date_of_joining) if date_of_joining else None
	if joining and start < joining:
		start = joining
	return start, end


def count_missed_days(employee, from_date, to_date) -> float:
	if not employee or not from_date or not to_date:
		return 0

	rows = frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"attendance_date": ["between", [getdate(from_date), getdate(to_date)]],
			"docstatus": ("<", 2),
			"status": ["in", ("Absent", "Half Day")],
		},
		fields=["status", "half_day_status"],
	)

	missed = 0.0
	for row in rows:
		if row.status == "Absent":
			missed += 1
		elif row.status == "Half Day" and row.half_day_status == "Absent":
			missed += 0.5
	return missed


def count_working_days(employee, from_date, to_date) -> int:
	start = getdate(from_date)
	end = getdate(to_date)
	total = date_diff(end, start) + 1
	if total <= 0:
		return 0

	holidays = set()
	try:
		from hrms.hr.utils import get_holiday_dates_for_employee

		for day in get_holiday_dates_for_employee(employee, start, end) or []:
			holidays.add(str(getdate(day)))
	except Exception:
		holidays = set()

	return max(total - len(holidays), 0)


def attendance_percent(employee, from_date, to_date) -> tuple[float, float, int]:
	working_days = count_working_days(employee, from_date, to_date)
	missed_days = count_missed_days(employee, from_date, to_date)
	if working_days <= 0:
		return 0.0, missed_days, 0
	present = max(working_days - missed_days, 0)
	return flt(present / working_days * 100, 2), missed_days, working_days


def get_auto_calculate_bonus_type(bonus_type=None):
	if bonus_type:
		if not frappe.db.exists("Bonus Type", bonus_type):
			return None
		doc = frappe.get_cached_doc("Bonus Type", bonus_type)
		return doc if cint(doc.auto_calculate) and not cint(doc.disabled) else None

	name = frappe.db.get_value(
		"Bonus Type",
		{"auto_calculate": 1, "disabled": 0},
		"name",
		order_by="modified desc",
	)
	return frappe.get_cached_doc("Bonus Type", name) if name else None


def _plan_from_employee(employee, overrides=None):
	overrides = overrides or {}
	emp = frappe.db.get_value(
		"Employee",
		employee,
		[
			"user_bonus",
			"user_bonus_period_months",
			"user_bonus_attendance_target",
			"user_bonus_if_below",
			"date_of_joining",
		],
		as_dict=True,
	) or {}

	bonus = get_auto_calculate_bonus_type()
	amount = overrides.get("user_bonus")
	if amount is None:
		amount = emp.get("user_bonus")
	months = overrides.get("period_months")
	if months in (None, ""):
		months = emp.get("user_bonus_period_months") or (bonus.period_months if bonus else None)
	target = overrides.get("attendance_target")
	if target in (None, ""):
		target = emp.get("user_bonus_attendance_target") or (bonus.attendance_target if bonus else None)
	if_below = overrides.get("if_below") or emp.get("user_bonus_if_below")
	if not if_below:
		if_below = (bonus.if_below if bonus else None) or DEFAULT_IF_BELOW

	return {
		"amount": flt(amount),
		"months": cint(months) or DEFAULT_PERIOD_MONTHS,
		"target": flt(target) or DEFAULT_ATTENDANCE_TARGET,
		"if_below": if_below,
		"date_of_joining": emp.get("date_of_joining"),
		"bonus_type": bonus.name if bonus else None,
	}


def calculate_user_bonus(
	employee,
	bonus_type=None,
	as_of_date=None,
	user_bonus=None,
	period_months=None,
	attendance_target=None,
	if_below=None,
) -> dict:
	as_of = getdate(as_of_date) if as_of_date else getdate()
	empty = {
		"auto_calculate": 0,
		"eligible": 0,
		"amount": 0,
		"is_deduction": 0,
		"attendance_pct": 0,
		"missed_days": 0,
		"working_days": 0,
		"target_amount": 0,
		"period_months": DEFAULT_PERIOD_MONTHS,
		"attendance_target": DEFAULT_ATTENDANCE_TARGET,
		"if_below": DEFAULT_IF_BELOW,
		"bonus_type": bonus_type,
		"salary_component": None,
		"status": _("Set a user bonus on the employee to enable attendance bonus."),
		"from_date": None,
		"to_date": str(as_of),
	}

	if not employee or not frappe.db.exists("Employee", employee):
		empty["status"] = _("Select an employee to calculate the user bonus.")
		return empty

	bonus = get_auto_calculate_bonus_type(bonus_type)
	if bonus_type and not bonus:
		empty["bonus_type"] = bonus_type
		empty["status"] = _("This bonus type is entered manually.")
		return empty

	plan = _plan_from_employee(
		employee,
		{
			"user_bonus": user_bonus,
			"period_months": period_months,
			"attendance_target": attendance_target,
			"if_below": if_below,
		},
	)
	if bonus:
		plan["bonus_type"] = bonus.name

	from_date, to_date = plan_window(as_of, plan["months"], plan["date_of_joining"])
	attendance_pct, missed_days, working_days = attendance_percent(employee, from_date, to_date)
	outcome = evaluate_attendance_plan(
		attendance_pct, plan["target"], plan["amount"], plan["months"], plan["if_below"]
	)

	if not plan["amount"]:
		status = _("Set the user bonus this agent should earn, then the months and attendance target.")
		outcome = {"eligible": 0, "amount": 0, "is_deduction": 0}
	elif outcome["eligible"]:
		status = _(
			"On track: {0}% attendance (target {1}%). Pays {2} this period toward {3} over {4} months."
		).format(
			flt(attendance_pct, 1),
			flt(plan["target"], 1),
			frappe.format_value(outcome["amount"], {"fieldtype": "Currency"}),
			frappe.format_value(plan["amount"], {"fieldtype": "Currency"}),
			plan["months"],
		)
	elif outcome["is_deduction"]:
		status = _(
			"Below target: {0}% attendance (target {1}%). Deduct {2} this period."
		).format(
			flt(attendance_pct, 1),
			flt(plan["target"], 1),
			frappe.format_value(outcome["amount"], {"fieldtype": "Currency"}),
		)
	else:
		status = _("Below target: {0}% attendance (target {1}%). No bonus this period.").format(
			flt(attendance_pct, 1),
			flt(plan["target"], 1),
		)

	return {
		"auto_calculate": 1,
		"eligible": outcome["eligible"],
		"amount": outcome["amount"],
		"is_deduction": outcome["is_deduction"],
		"attendance_pct": attendance_pct,
		"missed_days": missed_days,
		"working_days": working_days,
		"target_amount": plan["amount"],
		"period_months": plan["months"],
		"attendance_target": plan["target"],
		"if_below": plan["if_below"],
		"bonus_type": plan["bonus_type"] or bonus_type,
		"salary_component": "Attendance Deduction" if outcome["is_deduction"] else "Bonus",
		"status": status,
		"from_date": str(from_date),
		"to_date": str(to_date),
	}


@frappe.whitelist()
def get_user_bonus(
	employee: str,
	bonus_type: str | None = None,
	as_of_date: str | None = None,
	user_bonus: float | str | None = None,
	period_months: int | str | None = None,
	attendance_target: float | str | None = None,
	if_below: str | None = None,
):
	if not employee:
		frappe.throw(_("Employee is required"))
	if not frappe.has_permission("Employee", "read", employee):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return calculate_user_bonus(
		employee,
		bonus_type=bonus_type,
		as_of_date=as_of_date,
		user_bonus=user_bonus,
		period_months=period_months,
		attendance_target=attendance_target,
		if_below=if_below,
	)
