# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Daily pay, social security, and tax estimates on time tracking."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import frappe
from frappe.utils import cint, flt, get_datetime, get_first_day_of_week, getdate

from hrms.payroll.social_security import calculate_contribution, get_active_contribution_table

HOURS_PER_PERIOD = {
	"Daily": 8.0,
	"Weekly": 40.0,
	"Fortnightly": 80.0,
	"Bimonthly": 86.67,
	"Monthly": 173.33,
}

STANDARD_DAY_HOURS = 8.0

PAYROLL_FIELDS = ("hour_rate", "daily_pay", "ss_deduction", "tax_deduction", "net_daily_pay", "hours_paid")


def attendance_has_payroll_fields() -> bool:
	return frappe.db.has_column("Attendance", "daily_pay") and frappe.db.has_column("Attendance", "hour_rate")


def attendance_columns(*names) -> list[str]:
	return [name for name in names if name == "name" or frappe.db.has_column("Attendance", name)]


def pay_from_row(row) -> float:
	data = row if isinstance(row, dict) else {}
	pay = flt(data.get("daily_pay"))
	if pay:
		return pay
	hours = flt(data.get("working_hours"))
	rate = flt(data.get("hour_rate"))
	if not rate and data.get("employee") and data.get("attendance_date"):
		rate = get_hour_rate(data.get("employee"), data.get("attendance_date"))
	return flt(rate * hours, 2)


def week_bounds(day) -> tuple[date, date]:
	start = getdate(get_first_day_of_week(day))
	from frappe.utils import add_days

	return start, add_days(start, 6)


def get_assignment(employee: str, on_date):
	if not employee or not on_date:
		return None
	rows = frappe.get_all(
		"Salary Structure Assignment",
		filters={"employee": employee, "docstatus": 1, "from_date": ("<=", getdate(on_date))},
		fields=["name", "salary_structure", "base", "income_tax_slab", "company"],
		order_by="from_date desc",
		limit=1,
	)
	return rows[0] if rows else None


def get_hour_rate(employee: str, on_date) -> float:
	if not employee:
		return 0.0
	cache = frappe.flags.setdefault("hour_rate_cache", {})
	key = (employee, str(getdate(on_date) if on_date else ""))
	if key in cache:
		return cache[key]

	agent_hourly = flt(frappe.db.get_value("Employee", employee, "ctc"))
	if agent_hourly:
		cache[key] = flt(agent_hourly, 6)
		return cache[key]

	assignment = get_assignment(employee, on_date)
	hour_rate = 0.0
	frequency = "Weekly"
	base = 0.0
	if assignment:
		base = flt(assignment.base)
		if assignment.salary_structure and frappe.db.exists("Salary Structure", assignment.salary_structure):
			structure = frappe.get_cached_doc("Salary Structure", assignment.salary_structure)
			hour_rate = flt(structure.hour_rate)
			frequency = structure.payroll_frequency or frequency

	if hour_rate:
		cache[key] = flt(hour_rate, 6)
		return cache[key]

	period_hours = HOURS_PER_PERIOD.get(frequency, 40.0)
	if base and period_hours:
		cache[key] = flt(base / period_hours, 6)
		return cache[key]

	rate = (
		_hour_rate_from_salary_slip(employee)
		or _hour_rate_from_past_attendance(employee)
		or _hour_rate_from_company_structure(employee)
	)
	cache[key] = flt(rate, 6)
	return cache[key]


def _hour_rate_from_past_attendance(employee: str) -> float:
	if not employee or not attendance_has_payroll_fields():
		return 0.0
	rows = frappe.get_all(
		"Attendance",
		filters={"employee": employee, "docstatus": ("<", 2), "hour_rate": (">", 0)},
		fields=["hour_rate"],
		order_by="attendance_date desc",
		limit=1,
	)
	return flt(rows[0].hour_rate, 6) if rows else 0.0


def _hour_rate_from_company_structure(employee: str) -> float:
	company = frappe.db.get_value("Employee", employee, "company") if employee else None
	if not company or not frappe.db.table_exists("Salary Structure"):
		return 0.0
	rows = frappe.get_all(
		"Salary Structure",
		filters={"company": company, "docstatus": 1, "is_active": "Yes"},
		fields=["hour_rate", "is_default"],
		order_by="is_default desc, modified desc",
		limit=20,
	)
	for row in rows:
		if flt(row.hour_rate):
			return flt(row.hour_rate, 6)
	return 0.0


def _hour_rate_from_salary_slip(employee: str) -> float:
	if not employee or not frappe.db.table_exists("Salary Slip"):
		return 0.0
	slips = frappe.get_all(
		"Salary Slip",
		filters={"employee": employee, "docstatus": ("<", 2)},
		fields=["hour_rate", "gross_pay", "net_pay", "total_working_hours"],
		order_by="end_date desc",
		limit=1,
	)
	if not slips:
		return 0.0
	slip = slips[0]
	if flt(slip.hour_rate):
		return flt(slip.hour_rate, 6)
	hours = flt(slip.total_working_hours)
	pay = flt(slip.gross_pay) or flt(slip.net_pay)
	if hours and pay:
		return flt(pay / hours, 6)
	return 0.0


def _weekly_ss(employee: str, company: str | None, week_pay: float, week_start, week_end) -> float:
	if week_pay <= 0:
		return 0.0

	table = get_active_contribution_table(company, week_end)
	bands = None
	injury_employee = 0.0
	injury_employer = 2.60
	if table:
		bands = table.get("bands") or None
		injury_employee = flt(table.get("injury_only_employee_amount"))
		injury_employer = flt(table.get("injury_only_employer_amount"))

	emp_fields = ["date_of_birth"]
	if frappe.get_meta("Employee").has_field("receiving_ss_benefit"):
		emp_fields.append("receiving_ss_benefit")
	emp = frappe.db.get_value("Employee", employee, emp_fields, as_dict=True) or {}
	result = calculate_contribution(
		week_pay,
		"Weekly",
		week_start,
		week_end,
		date_of_birth=emp.get("date_of_birth"),
		receiving_ss_benefit=bool(emp.get("receiving_ss_benefit")),
		bands=bands,
		injury_only_employee_amount=injury_employee,
		injury_only_employer_amount=injury_employer,
	)
	return flt(result.get("employee_amount"), 2)


def _weekly_tax(employee: str, company: str | None, on_date, week_pay: float) -> float:
	if week_pay <= 0:
		return 0.0
	assignment = get_assignment(employee, on_date)
	slab_name = assignment.income_tax_slab if assignment else None
	if not slab_name:
		return 0.0

	from hrms.payroll.doctype.income_tax_slab.income_tax_slab import calculate_tax_by_tax_slab

	tax_slab = frappe.get_cached_doc("Income Tax Slab", slab_name)
	annual = flt(week_pay) * 52.0
	annual_tax, _other = calculate_tax_by_tax_slab(annual, tax_slab)
	return flt(flt(annual_tax) / 52.0, 2)


def week_attendance_rows(employee: str, on_date) -> list[dict]:
	start, end = week_bounds(on_date)
	fields = attendance_columns(
		"name", "attendance_date", "working_hours", "daily_pay", "hour_rate", "company"
	)
	return frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"attendance_date": ["between", [start, end]],
			"docstatus": ["<", 2],
		},
		fields=fields,
		order_by="attendance_date asc",
	)


def apply_daily_pay_to_doc(doc) -> None:
	"""Set hour rate and daily pay on a single Attendance doc."""
	ensure_working_hours_from_times(doc)
	if not attendance_has_payroll_fields():
		return
	if not doc.employee or not doc.attendance_date:
		return

	doc.hour_rate = get_hour_rate(doc.employee, doc.attendance_date)
	status = doc.status or ""

	# Leave uses hours-based pay only (no holiday statutory gift).
	if status in ("On Leave", "Half Day"):
		doc.daily_pay = flt(flt(doc.hour_rate) * flt(doc.working_hours), 2)
		return

	holiday = get_public_holiday_pay_context(doc.employee, doc.attendance_date)
	if holiday:
		hours = flt(doc.working_hours)
		has_clock = bool(getattr(doc, "in_time", None) or getattr(doc, "out_time", None))
		# Premium only when the employee actually clocked; otherwise statutory 8 × rate.
		worked = status != "Absent" and hours > 0 and has_clock
		if not worked:
			if hours <= 0:
				doc.working_hours = STANDARD_DAY_HOURS
			doc.daily_pay = calculate_holiday_daily_pay(doc.hour_rate, 0, holiday["premium_multiplier"])
			return
		doc.daily_pay = calculate_holiday_daily_pay(doc.hour_rate, hours, holiday["premium_multiplier"])
		return

	if status == "Absent":
		doc.daily_pay = 0
		doc.ss_deduction = 0
		doc.tax_deduction = 0
		doc.net_daily_pay = 0
		return

	doc.daily_pay = flt(flt(doc.hour_rate) * flt(doc.working_hours), 2)


def get_public_holiday_pay_context(employee: str, on_date) -> dict | None:
	"""Return pay context when `on_date` is a public holiday (not weekly off), else None."""
	if not employee or not on_date:
		return None
	try:
		from hrms.utils.holiday_list import get_holiday_list_for_employee

		holiday_list = get_holiday_list_for_employee(employee, raise_exception=False, as_on=on_date)
	except Exception:
		holiday_list = None
	if not holiday_list:
		return None

	on_date = getdate(on_date)
	is_public = frappe.db.exists(
		"Holiday",
		{"parent": holiday_list, "holiday_date": on_date, "weekly_off": 0},
	)
	if not is_public:
		return None

	tah = 0
	dt = 0
	meta = frappe.get_meta("Holiday List")
	if meta.has_field("pay_time_and_a_half"):
		tah = cint(frappe.db.get_value("Holiday List", holiday_list, "pay_time_and_a_half"))
	if meta.has_field("pay_double_time"):
		dt = cint(frappe.db.get_value("Holiday List", holiday_list, "pay_double_time"))
	# Prefer double time if both somehow set (validate should prevent this).
	if dt:
		premium = 1.0
		tah = 0
	elif tah:
		premium = 0.5
	else:
		premium = 0.0

	return {
		"holiday_list": holiday_list,
		"premium_multiplier": premium,
		"pay_time_and_a_half": bool(tah),
		"pay_double_time": bool(dt),
	}


def calculate_holiday_daily_pay(rate: float, hours: float, premium_multiplier: float) -> float:
	"""Holiday-plus-premium: 8h regular + premium on hours worked (or 8h if unworked)."""
	rate = flt(rate)
	hours = flt(hours)
	premium_multiplier = flt(premium_multiplier)
	base = STANDARD_DAY_HOURS * rate
	if hours <= 0:
		return flt(base, 2)
	if premium_multiplier <= 0:
		return flt(max(STANDARD_DAY_HOURS, hours) * rate, 2)
	return flt(base + (hours * premium_multiplier * rate), 2)


def ensure_paid_holiday_attendance(
	from_date,
	to_date,
	employee: str | None = None,
	department: str | None = None,
) -> list[str]:
	"""Create Present / 8h attendance for public holidays with no existing row."""
	from frappe.utils import add_days

	from_date = getdate(from_date)
	to_date = getdate(to_date)
	if not from_date or not to_date or to_date < from_date:
		return []

	# Require an employee or department filter to avoid mass-creating for every Active employee.
	if not employee and not department:
		return []

	employees = _employees_for_holiday_ensure(employee, department)
	created = []
	for emp in employees:
		day = from_date
		while day <= to_date:
			ctx = get_public_holiday_pay_context(emp, day)
			if not ctx:
				day = add_days(day, 1)
				continue
			existing = frappe.db.exists(
				"Attendance",
				{"employee": emp, "attendance_date": day, "docstatus": ("<", 2)},
			)
			if existing:
				day = add_days(day, 1)
				continue
			doc = frappe.get_doc(
				{
					"doctype": "Attendance",
					"employee": emp,
					"attendance_date": day,
					"status": "Present",
					# 0 hours → apply_daily_pay treats as unworked statutory holiday (8 × rate).
					"working_hours": 0,
					"hours_paid": 0,
				}
			)
			doc.insert(ignore_permissions=True)
			created.append(doc.name)
			day = add_days(day, 1)
	return created


def _employees_for_holiday_ensure(employee: str | None, department: str | None) -> list[str]:
	if employee:
		return [employee]
	filters = {"status": "Active"}
	if department:
		filters["department"] = department
	return frappe.get_all("Employee", filters=filters, pluck="name", order_by="name asc")


def allocate_week_deductions(employee: str, on_date, overlay: dict | None = None) -> None:
	"""Spread this week's SS and tax across the employee's attendance rows."""
	if not attendance_has_payroll_fields() or not employee or not on_date:
		return
	if frappe.flags.in_daily_pay_alloc:
		return

	frappe.flags.in_daily_pay_alloc = True
	try:
		start, end = week_bounds(on_date)
		rows = week_attendance_rows(employee, on_date)
		overlay = overlay or {}
		company = None
		week_pay = 0.0
		for row in rows:
			if row.name in overlay:
				row.update(overlay[row.name])
			week_pay += flt(row.get("daily_pay"))
			company = company or row.get("company")

		if not company:
			company = frappe.db.get_value("Employee", employee, "company")

		week_ss = _weekly_ss(employee, company, week_pay, start, end)
		week_tax = _weekly_tax(employee, company, on_date, week_pay)

		for row in rows:
			pay = flt(row.get("daily_pay"))
			share = (pay / week_pay) if week_pay else 0.0
			ss_amount = flt(week_ss * share, 2)
			tax_amount = flt(week_tax * share, 2)
			values = {
				"ss_deduction": ss_amount,
				"tax_deduction": tax_amount,
				"net_daily_pay": flt(pay - ss_amount - tax_amount, 2),
			}
			if overlay.get(row.name):
				continue
			frappe.db.set_value("Attendance", row.name, values, update_modified=False)
	finally:
		frappe.flags.in_daily_pay_alloc = False


def refresh_attendance_payroll(doc) -> dict:
	"""Apply pay + this day's share of weekly SS/tax onto `doc`."""
	apply_daily_pay_to_doc(doc)
	if not attendance_has_payroll_fields():
		return {
			"hour_rate": flt(getattr(doc, "hour_rate", 0)),
			"daily_pay": 0.0,
			"ss_deduction": 0.0,
			"tax_deduction": 0.0,
			"net_daily_pay": 0.0,
		}

	# Unpaid absent (non-holiday) — no SS/tax share.
	if (doc.status or "") == "Absent" and not flt(doc.daily_pay):
		return {
			"hour_rate": flt(getattr(doc, "hour_rate", 0)),
			"daily_pay": 0.0,
			"ss_deduction": 0.0,
			"tax_deduction": 0.0,
			"net_daily_pay": 0.0,
		}

	start, end = week_bounds(doc.attendance_date)
	rows = week_attendance_rows(doc.employee, doc.attendance_date)
	week_pay = 0.0
	company = doc.company
	for row in rows:
		pay = flt(doc.daily_pay) if row.name == doc.name else flt(row.get("daily_pay"))
		week_pay += pay
		company = company or row.get("company")

	if not any(row.name == doc.name for row in rows):
		week_pay += flt(doc.daily_pay)

	week_ss = _weekly_ss(doc.employee, company, week_pay, start, end)
	week_tax = _weekly_tax(doc.employee, company, doc.attendance_date, week_pay)
	pay = flt(doc.daily_pay)
	share = (pay / week_pay) if week_pay else 0.0
	doc.ss_deduction = flt(week_ss * share, 2)
	doc.tax_deduction = flt(week_tax * share, 2)
	doc.net_daily_pay = flt(pay - flt(doc.ss_deduction) - flt(doc.tax_deduction), 2)
	return {
		"hour_rate": flt(doc.hour_rate),
		"daily_pay": pay,
		"ss_deduction": flt(doc.ss_deduction),
		"tax_deduction": flt(doc.tax_deduction),
		"net_daily_pay": flt(doc.net_daily_pay),
	}


def on_attendance_validate(doc, method=None):
	refresh_attendance_payroll(doc)


def on_attendance_update(doc, method=None):
	if frappe.flags.in_daily_pay_alloc:
		return
	if not attendance_has_payroll_fields():
		return
	allocate_week_deductions(
		doc.employee,
		doc.attendance_date,
		overlay={
			doc.name: {
				"daily_pay": flt(doc.daily_pay),
				"company": doc.company,
			}
		},
	)


def _log_type(log) -> str:
	value = getattr(log, "log_type", None) if not isinstance(log, dict) else log.get("log_type")
	return (value or "IN").upper()


def _log_time(log):
	return getattr(log, "time", None) if not isinstance(log, dict) else log.get("time")


def _log_name(log) -> str | None:
	return getattr(log, "name", None) if not isinstance(log, dict) else log.get("name")


def _log_shift(log) -> str | None:
	return getattr(log, "shift", None) if not isinstance(log, dict) else log.get("shift")


def _as_datetime(value) -> datetime | None:
	"""Normalize clock values from MariaDB/Frappe (datetime, time, timedelta, or string)."""
	if value is None or value == "":
		return None
	if isinstance(value, datetime):
		if value.tzinfo is not None:
			value = value.replace(tzinfo=None)
		return value.replace(microsecond=0)
	if isinstance(value, timedelta):
		return datetime.combine(date.today(), (datetime.min + value).time())
	if isinstance(value, time):
		return datetime.combine(date.today(), value)
	if isinstance(value, date):
		return datetime.combine(value, time())
	parsed = get_datetime(value)
	if parsed is None:
		return None
	if isinstance(parsed, timedelta):
		return datetime.combine(date.today(), (datetime.min + parsed).time())
	if isinstance(parsed, datetime):
		if parsed.tzinfo is not None:
			parsed = parsed.replace(tzinfo=None)
		return parsed.replace(microsecond=0)
	return None


def _hours_between(start, end) -> float:
	"""Worked hours from an IN clock to an OUT clock (out - in). Overnight shifts wrap +1 day."""
	start_dt = _as_datetime(start)
	end_dt = _as_datetime(end)
	if not start_dt or not end_dt:
		return 0.0
	if end_dt < start_dt:
		end_dt += timedelta(days=1)
	hours = (end_dt - start_dt).total_seconds() / 3600.0
	return flt(hours, 2) if hours > 0 else 0.0


def ensure_working_hours_from_times(doc) -> float:
	"""Fill working_hours from in/out when it was left at 0."""
	if (getattr(doc, "status", None) or "") in ("Absent", "On Leave"):
		return flt(getattr(doc, "working_hours", 0))
	hours = flt(getattr(doc, "working_hours", 0))
	if hours:
		return hours
	hours = _hours_between(getattr(doc, "in_time", None), getattr(doc, "out_time", None))
	if hours:
		doc.working_hours = hours
	return hours


def pair_checkin_logs(logs: list) -> dict:
	"""Pair consecutive IN/OUT punches. Break time between OUT and the next IN is unpaid.

	Returns:
	  pairs: list of {in_time, out_time, hours, in_log, out_log, open}
	  in_time / out_time: first IN and last OUT (or None while still clocked in)
	  pair_hours: sum of completed pair durations
	  working_hours: pair_hours (lunch/break gaps are excluded)
	"""
	ordered = sorted(
		[log for log in (logs or []) if _log_time(log)],
		key=lambda row: (_as_datetime(_log_time(row)) or datetime.min, _log_name(row) or ""),
	)
	pairs: list[dict] = []
	pending_in = None

	for log in ordered:
		log_type = _log_type(log)
		when = _log_time(log)
		if log_type == "IN":
			if pending_in is None:
				pending_in = log
			# Extra IN without OUT is ignored; keep earliest open IN.
			continue
		if log_type == "OUT" and pending_in is not None:
			in_when = _log_time(pending_in)
			hours = _hours_between(in_when, when)
			pairs.append(
				{
					"in_time": in_when,
					"out_time": when,
					"hours": hours,
					"in_log": _log_name(pending_in),
					"out_log": _log_name(log),
					"open": False,
				}
			)
			pending_in = None

	if pending_in is not None:
		pairs.append(
			{
				"in_time": _log_time(pending_in),
				"out_time": None,
				"hours": 0.0,
				"in_log": _log_name(pending_in),
				"out_log": None,
				"open": True,
			}
		)

	completed = [pair for pair in pairs if not pair["open"]]
	pair_hours = flt(sum(flt(pair["hours"]) for pair in completed), 2)
	working_hours = pair_hours

	ins = [row for row in ordered if _log_type(row) == "IN" and _log_time(row)]
	outs = [row for row in ordered if _log_type(row) == "OUT" and _log_time(row)]
	in_time = _log_time(ins[0]) if ins else None
	# Keep out_time blank while still clocked in (open trailing IN).
	out_time = None if any(pair["open"] for pair in pairs) else (_log_time(outs[-1]) if outs else None)

	return {
		"pairs": pairs,
		"in_time": in_time,
		"out_time": out_time,
		"pair_hours": pair_hours,
		"working_hours": working_hours,
	}


def _hours_from_logs(logs: list[dict]) -> tuple:
	"""Compatibility wrapper: first IN, last OUT (blank if open), pair-sum hours."""
	result = pair_checkin_logs(logs)
	return result["in_time"], result["out_time"], result["working_hours"]


def get_day_checkins(employee: str, day) -> list[dict]:
	day = getdate(day)
	return frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]]},
		fields=["name", "log_type", "time", "shift", "attendance"],
		order_by="time asc",
	)


def resync_attendance_from_day_logs(employee: str, day, attendance_name: str | None = None) -> str | None:
	"""Recompute Attendance times/hours from the day's checkins (completed pair sum)."""
	day = getdate(day)
	logs = get_day_checkins(employee, day)
	result = pair_checkin_logs(logs)
	existing = attendance_name or frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": day, "docstatus": ("<", 2)},
		"name",
	)
	shift = next((_log_shift(log) for log in logs if _log_shift(log)), None)

	frappe.flags.in_daily_pay_sync = True
	try:
		if not logs:
			if existing:
				doc = frappe.get_doc("Attendance", existing)
				if doc.docstatus == 1:
					doc.cancel()
				elif doc.docstatus == 0:
					doc.delete()
			return None

		if existing:
			doc = frappe.get_doc("Attendance", existing)
			if doc.docstatus == 2:
				return existing
			updates = {
				"in_time": result["in_time"],
				"out_time": result["out_time"],
				"working_hours": result["working_hours"],
				"status": "Present" if doc.status not in ("On Leave", "Half Day") else doc.status,
			}
			if shift and not doc.shift:
				updates["shift"] = shift
			if doc.docstatus == 1:
				frappe.db.set_value("Attendance", existing, updates, update_modified=False)
				doc.reload()
				refresh_attendance_payroll(doc)
				frappe.db.set_value(
					"Attendance",
					existing,
					{
						"hour_rate": doc.hour_rate,
						"daily_pay": doc.daily_pay,
						"ss_deduction": doc.ss_deduction,
						"tax_deduction": doc.tax_deduction,
						"net_daily_pay": doc.net_daily_pay,
					},
					update_modified=False,
				)
				allocate_week_deductions(doc.employee, doc.attendance_date)
			else:
				doc.update(updates)
				doc.save(ignore_permissions=True)
			for log in logs:
				if not log.get("attendance"):
					frappe.db.set_value(
						"Employee Checkin", log.name, "attendance", existing, update_modified=False
					)
			return existing

		doc = frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": day,
				"status": "Present",
				"in_time": result["in_time"],
				"out_time": result["out_time"],
				"working_hours": result["working_hours"],
				"shift": shift,
				"hours_paid": 0,
			}
		)
		doc.insert(ignore_permissions=True)
		for log in logs:
			frappe.db.set_value("Employee Checkin", log.name, "attendance", doc.name, update_modified=False)
		return doc.name
	finally:
		frappe.flags.in_daily_pay_sync = False


def sync_attendance_from_checkin(checkin) -> str | None:
	"""Create or update today's attendance when an agent punches, then recalc pay."""
	if not checkin or not checkin.employee or not checkin.time:
		return None
	if frappe.flags.in_daily_pay_sync:
		return getattr(checkin, "attendance", None)

	day = getdate(checkin.time)
	existing = checkin.attendance or frappe.db.get_value(
		"Attendance",
		{"employee": checkin.employee, "attendance_date": day, "docstatus": ("<", 2)},
		"name",
	)
	return resync_attendance_from_day_logs(checkin.employee, day, attendance_name=existing)


def on_employee_checkin(doc, method=None):
	if frappe.flags.in_test and not frappe.flags.get("apply_daily_pay"):
		return
	try:
		sync_attendance_from_checkin(doc)
	except Exception:
		frappe.log_error(title="Daily pay punch sync failed")
