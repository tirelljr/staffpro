# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Sum
from frappe.utils import (
	add_days,
	add_to_date,
	flt,
	formatdate,
	get_first_day,
	get_last_day,
	getdate,
)

from erpnext.accounts.utils import build_qb_match_conditions

PERIOD_DAYS = {
	"weekly": 7,
	"monthly": 30,
	"yearly": 365,
}

FALLBACK_LIMIT = 5
PAYROLL_LIMIT = 8
RELATIVE_FILTER_OPS = {"Timespan"}
SPARKLINE_POINTS = 6


@frappe.whitelist()
def get_number_card_sparklines(card_names: str | list | None = None, points: int = SPARKLINE_POINTS) -> dict:
	"""Return period series for dashboard KPI mini-charts."""
	if isinstance(card_names, str):
		card_names = frappe.parse_json(card_names)
	if not card_names:
		return {}

	points = max(3, min(int(points or SPARKLINE_POINTS), 12))
	out = {}
	for name in card_names:
		if not name or not frappe.db.exists("Number Card", name):
			continue
		try:
			out[name] = _sparkline_for_card(name, points)
		except Exception:
			frappe.log_error(title=f"KPI sparkline failed: {name}")
			out[name] = {"values": [], "kind": "bars"}
	return out


@frappe.whitelist()
def get_upcoming_celebrations(
	period: str = "weekly", company: str | None = None, event_type: str | None = None
) -> dict:
	"""Return upcoming employee birthdays and work anniversaries for the desk dashboard."""
	company = company or frappe.defaults.get_user_default("Company")
	if not company:
		return {"events": [], "fallback": False}

	days = PERIOD_DAYS.get(period, PERIOD_DAYS["weekly"])
	today = getdate()
	end_date = add_days(today, days - 1)

	employees = _get_active_employees(company)
	all_events = _collect_employee_events(employees, today)

	if event_type and event_type != "all":
		all_events = [event for event in all_events if event["event_type"] == event_type]

	period_events = [event for event in all_events if today <= event["event_date"] <= end_date]
	if period_events:
		return {"events": period_events, "fallback": False}

	future_events = [event for event in all_events if event["event_date"] > end_date]
	return {
		"events": future_events[:FALLBACK_LIMIT],
		"fallback": bool(future_events),
	}


@frappe.whitelist()
def get_upcoming_payroll(period: str = "monthly", company: str | None = None) -> dict:
	"""Return agent payroll rows for the People dashboard panel."""
	company = company or frappe.defaults.get_user_default("Company")
	if not company:
		return {"rows": [], "period_label": "", "start_date": None, "end_date": None}

	start_date, end_date = _payroll_period_bounds(period)
	rows = _get_payroll_rows(company, start_date, end_date)
	return {
		"rows": rows[:PAYROLL_LIMIT],
		"period_label": _payroll_period_label(start_date, end_date),
		"start_date": start_date,
		"end_date": end_date,
	}


def _payroll_period_bounds(period: str):
	today = getdate()
	if period == "weekly":
		start_date = add_days(today, -today.weekday())
		end_date = add_days(start_date, 6)
		return start_date, end_date

	if period == "yearly":
		start_date = getdate(f"{today.year}-01-01")
		end_date = getdate(f"{today.year}-12-31")
		return start_date, end_date

	start_date = get_first_day(today)
	end_date = get_last_day(today)
	return start_date, end_date


def _payroll_period_label(start_date, end_date):
	if start_date.month == end_date.month and start_date.year == end_date.year:
		return start_date.strftime("%B %Y")
	return f"{formatdate(start_date)} – {formatdate(end_date)}"


def _get_payroll_rows(company, start_date, end_date):
	salary_slip = frappe.qb.DocType("Salary Slip")
	employee = frappe.qb.DocType("Employee")

	select_fields = [
		salary_slip.name,
		salary_slip.employee,
		salary_slip.employee_name,
		salary_slip.start_date,
		salary_slip.end_date,
		salary_slip.gross_pay,
		salary_slip.net_pay,
		salary_slip.currency,
		salary_slip.payroll_frequency,
		salary_slip.total_working_hours,
		salary_slip.payment_days,
		salary_slip.status,
		salary_slip.docstatus,
		salary_slip.journal_entry,
		salary_slip.company,
		employee.designation,
		employee.department,
		employee.image,
		employee.company_email,
		employee.personal_email,
	]
	if frappe.db.has_column("Salary Slip", "ss_employee_amount"):
		select_fields.append(salary_slip.ss_employee_amount)

	slips = (
		frappe.qb.from_(salary_slip)
		.left_join(employee)
		.on(salary_slip.employee == employee.name)
		.select(*select_fields)
		.where(salary_slip.company == company)
		.where(salary_slip.start_date <= end_date)
		.where(salary_slip.end_date >= start_date)
		.where(salary_slip.docstatus != 2)
		.orderby(salary_slip.end_date, order=frappe.qb.desc)
		.orderby(salary_slip.employee_name)
	).run(as_dict=True)

	rows = []
	seen_employees = set()
	attendance_ss = _ss_from_attendance(company, start_date, end_date)

	for slip in slips:
		if slip.employee in seen_employees:
			continue
		seen_employees.add(slip.employee)
		rows.append(_build_payroll_row(slip, start_date, end_date, attendance_ss))

	if rows:
		return rows

	employees = _get_active_employees(company)
	hours_by_employee = _attendance_hours_by_employee(company, start_date, end_date)
	pay_by_employee = _attendance_pay_by_employee(company, start_date, end_date)
	ss_by_employee = _ss_from_attendance(company, start_date, end_date)
	currency = frappe.db.get_value("Company", company, "default_currency")

	for emp in employees:
		pay = pay_by_employee.get(emp.name) or {}
		gross = pay.get("gross")
		net = pay.get("net")
		rows.append(
			{
				"employee": emp.name,
				"employee_name": emp.employee_name,
				"subtitle": _employee_subtitle(emp),
				"image": emp.image,
				"hours_worked": flt(hours_by_employee.get(emp.name)),
				"gross_pay": gross,
				"net_pay": net,
				"ss_contribution": flt(ss_by_employee.get(emp.name)),
				"currency": currency,
				"pay_date": end_date,
				"pay_date_label": formatdate(end_date),
				"status": "pending",
				"status_label": _("Pending"),
				"salary_slip": None,
			}
		)

	rows.sort(key=lambda row: (-row["hours_worked"], row["employee_name"].lower()))
	return rows


def _build_payroll_row(slip, start_date, end_date, attendance_ss=None):
	hours = flt(slip.total_working_hours)
	if not hours and slip.payment_days:
		hours = flt(slip.payment_days) * 8

	status, status_label = _payroll_status(slip)
	email = slip.company_email or slip.personal_email or ""
	subtitle = _employee_subtitle(slip)
	if email:
		subtitle = email

	ss_amount = _ss_amount_for_slip(slip)
	if not ss_amount and attendance_ss:
		ss_amount = flt(attendance_ss.get(slip.employee))

	return {
		"employee": slip.employee,
		"employee_name": slip.employee_name,
		"subtitle": subtitle,
		"image": slip.image,
		"hours_worked": hours,
		"gross_pay": flt(slip.gross_pay),
		"net_pay": flt(slip.net_pay),
		"ss_contribution": ss_amount,
		"currency": slip.currency,
		"pay_date": slip.end_date or end_date,
		"pay_date_label": formatdate(slip.end_date or end_date),
		"status": status,
		"status_label": status_label,
		"salary_slip": slip.name,
	}


def _ss_amount_for_slip(slip) -> float:
	amount = flt(slip.get("ss_employee_amount"))
	if amount:
		return amount

	if slip.get("name") and frappe.db.table_exists("Salary Detail"):
		deductions = frappe.get_all(
			"Salary Detail",
			filters={
				"parent": slip.name,
				"parenttype": "Salary Slip",
				"parentfield": "deductions",
				"salary_component": "Social Security",
			},
			pluck="amount",
		)
		amount = flt(sum(flt(value) for value in deductions), 2)
		if amount:
			return amount

	gross = flt(slip.get("gross_pay") or slip.get("net_pay"))
	if gross <= 0:
		return 0.0

	from hrms.payroll.social_security import calculate_contribution, get_active_contribution_table

	table = get_active_contribution_table(slip.get("company"), slip.get("end_date") or slip.get("start_date"))
	emp_fields = ["date_of_birth"]
	if frappe.get_meta("Employee").has_field("receiving_ss_benefit"):
		emp_fields.append("receiving_ss_benefit")
	emp = frappe.db.get_value("Employee", slip.employee, emp_fields, as_dict=True) or {}
	result = calculate_contribution(
		gross,
		slip.get("payroll_frequency") or "Monthly",
		slip.get("start_date"),
		slip.get("end_date"),
		date_of_birth=emp.get("date_of_birth"),
		receiving_ss_benefit=bool(emp.get("receiving_ss_benefit")),
		bands=table.bands if table else None,
		injury_only_employee_amount=flt(table.injury_only_employee_amount) if table else 0.0,
		injury_only_employer_amount=flt(table.injury_only_employer_amount) if table else 2.60,
	)
	return flt(result.get("employee_amount"), 2)


def _payroll_status(slip):
	if slip.docstatus == 0 or slip.status == "Draft":
		return "pending", _("Pending")
	if slip.journal_entry:
		return "paid", _("Paid")
	if slip.status == "Submitted":
		return "ready", _("Ready")
	if slip.status == "Withheld":
		return "pending", _("Withheld")
	return "pending", _("Pending")


def _ss_from_attendance(company, start_date, end_date) -> dict:
	"""Weekly SSB employee contribution from time clocks in the payroll period."""
	from hrms.payroll.daily_pay import _weekly_ss, attendance_columns, pay_from_row, week_bounds

	week_from, _unused = week_bounds(start_date)
	_unused, week_to = week_bounds(end_date)
	fields = attendance_columns(
		"employee", "attendance_date", "working_hours", "hour_rate", "daily_pay", "company"
	)
	if "employee" not in fields:
		fields.insert(0, "employee")
	if "attendance_date" not in fields:
		fields.insert(1, "attendance_date")

	filters = {
		"attendance_date": ["between", [week_from, week_to]],
		"docstatus": ["<", 2],
	}
	if frappe.db.has_column("Attendance", "company"):
		filters["company"] = company

	week_pay = {}
	for rec in frappe.get_all("Attendance", filters=filters, fields=fields):
		if not rec.get("employee") or not rec.get("attendance_date"):
			continue
		week_start, week_end = week_bounds(rec.attendance_date)
		if week_end < start_date or week_start > end_date:
			continue
		key = (rec.employee, week_start)
		week_pay[key] = week_pay.get(key, 0.0) + pay_from_row(rec)

	ss_by_employee = {}
	for (employee, week_start), pay in week_pay.items():
		_unused, week_end = week_bounds(week_start)
		ss_by_employee[employee] = flt(
			ss_by_employee.get(employee, 0.0) + _weekly_ss(employee, company, pay, week_start, week_end),
			2,
		)
	return ss_by_employee


def _attendance_pay_by_employee(company, start_date, end_date):
	if not frappe.db.has_column("Attendance", "daily_pay"):
		return {}

	attendance = frappe.qb.DocType("Attendance")
	select_fields = [attendance.employee, Sum(attendance.daily_pay).as_("gross")]
	has_net = frappe.db.has_column("Attendance", "net_daily_pay")
	if has_net:
		select_fields.append(Sum(attendance.net_daily_pay).as_("net"))

	query = (
		frappe.qb.from_(attendance)
		.select(*select_fields)
		.where(attendance.company == company)
		.where(attendance.docstatus < 2)
		.where(attendance.attendance_date.between(start_date, end_date))
		.groupby(attendance.employee)
	)
	rows = query.run(as_dict=True)

	out = {}
	for row in rows:
		gross = flt(row.gross) or None
		net = flt(row.net) if has_net and row.get("net") is not None else None
		if gross is None and net is None:
			continue
		out[row.employee] = {"gross": gross, "net": net}
	return out


def _attendance_hours_by_employee(company, start_date, end_date):
	attendance = frappe.qb.DocType("Attendance")
	rows = (
		frappe.qb.from_(attendance)
		.select(attendance.employee, Sum(attendance.working_hours).as_("hours"))
		.where(attendance.company == company)
		.where(attendance.docstatus == 1)
		.where(attendance.attendance_date.between(start_date, end_date))
		.where(attendance.status.isin(["Present", "Half Day", "Work From Home"]))
		.groupby(attendance.employee)
	).run(as_dict=True)

	return {row.employee: flt(row.hours) for row in rows}


def _employee_subtitle(employee):
	subtitle = employee.designation or ""
	if employee.designation and employee.department:
		return _("{0} in {1}").format(employee.designation, employee.department)
	if employee.department:
		return employee.department
	return subtitle


def _collect_employee_events(employees, today):
	events = []

	for employee in employees:
		if employee.date_of_birth:
			date_of_birth = getdate(employee.date_of_birth)
			event_date = _next_occurrence(date_of_birth, today)
			if event_date >= today:
				events.append(
					_build_event(
						employee,
						event_type="birthday",
						event_date=event_date,
					)
				)

		if employee.date_of_joining:
			date_of_joining = getdate(employee.date_of_joining)
			event_date = _next_occurrence(date_of_joining, today)
			if event_date >= today and event_date.year > date_of_joining.year:
				events.append(
					_build_event(
						employee,
						event_type="anniversary",
						event_date=event_date,
						years_completed=event_date.year - date_of_joining.year,
					)
				)

	events.sort(key=lambda row: (row["event_date"], row["employee_name"].lower()))
	return events


def _get_active_employees(company):
	employee = frappe.qb.DocType("Employee")
	return (
		frappe.qb.from_(employee)
		.select(
			employee.name,
			employee.employee_name,
			employee.date_of_birth,
			employee.date_of_joining,
			employee.designation,
			employee.department,
			employee.image,
		)
		.where(employee.company == company)
		.where(employee.status == "Active")
		.where(Criterion.all(build_qb_match_conditions("Employee")))
	).run(as_dict=True)


def _next_occurrence(source_date, from_date):
	for year in (from_date.year, from_date.year + 1):
		try:
			candidate = source_date.replace(year=year)
		except ValueError:
			candidate = source_date.replace(year=year, day=28)

		if candidate >= from_date:
			return candidate

	return source_date.replace(year=from_date.year + 1)


def _build_event(employee, event_type, event_date, years_completed=None):
	subtitle = employee.designation or ""
	if employee.designation and employee.department:
		subtitle = _("{0} in {1}").format(employee.designation, employee.department)
	elif employee.department:
		subtitle = employee.department

	source_date = (
		getdate(employee.date_of_joining) if event_type == "anniversary" else getdate(employee.date_of_birth)
	)
	event = {
		"employee": employee.name,
		"employee_name": employee.employee_name,
		"subtitle": subtitle,
		"image": employee.image,
		"event_type": event_type,
		"event_date": event_date,
		"source_date": source_date,
		"day": event_date.day,
		"month": event_date.strftime("%b"),
	}

	if event_type == "birthday":
		event["event_label"] = _("Birthday")
		event["event_icon"] = "birthday"
	elif event_type == "anniversary":
		event["event_label"] = _("Work Anniversary")
		event["event_icon"] = "anniversary"
		event["years_completed"] = years_completed

	return event


def _sparkline_for_card(card_name: str, points: int) -> dict:
	doc = frappe.get_cached_doc("Number Card", card_name)
	if doc.type != "Document Type" or not doc.document_type:
		return {"values": [], "kind": "bars"}

	filters, date_field, interval, periodized = _prepare_sparkline_filters(doc)
	values = []
	for offset in range(points - 1, -1, -1):
		start, end = _period_bounds(interval, offset)
		period_filters = list(filters)
		if periodized:
			period_filters.append([doc.document_type, date_field, "between", [str(start), str(end)]])
		else:
			period_filters.append([doc.document_type, date_field, "<=", str(end)])
		values.append(_aggregate_card_value(doc, period_filters))

	kind = "bars"
	return {"values": values, "kind": kind, "interval": interval}


def _prepare_sparkline_filters(doc):
	raw_filters = frappe.parse_json(doc.filters_json or "[]") or []
	dynamic_filters = _resolve_dynamic_filters(doc.dynamic_filters_json)
	filters = []
	date_field = "creation"
	timespan_value = None
	periodized = False

	for row in list(raw_filters) + list(dynamic_filters):
		if not isinstance(row, (list, tuple)) or len(row) < 4:
			continue
		doctype, field, op, value = row[0], row[1], row[2], row[3]
		if op in RELATIVE_FILTER_OPS or _looks_like_timespan(value):
			date_field = field or date_field
			timespan_value = value if isinstance(value, str) else timespan_value
			periodized = True
			continue
		filters.append([doctype, field, op, value])

	if not periodized:
		# Cumulative headcount-style cards: grow by creation over time.
		date_field = "creation"

	interval = _infer_interval(timespan_value, doc.stats_time_interval)
	return filters, date_field, interval, periodized


def _resolve_dynamic_filters(dynamic_filters_json):
	rows = frappe.parse_json(dynamic_filters_json or "[]") or []
	resolved = []
	for row in rows:
		if not isinstance(row, (list, tuple)) or len(row) < 4:
			continue
		item = list(row)
		expr = item[3]
		if isinstance(expr, str):
			try:
				item[3] = frappe.safe_eval(
					expr,
					eval_globals={"frappe": frappe},
					eval_locals={"frappe": frappe},
				)
			except Exception:
				if "Company" in expr:
					item[3] = frappe.defaults.get_user_default("Company")
				else:
					continue
		resolved.append(item)
	return resolved


def _looks_like_timespan(value) -> bool:
	if not isinstance(value, str):
		return False
	text = value.strip().lower()
	return text.startswith(("this ", "last ", "next ")) or text in {
		"today",
		"yesterday",
		"tomorrow",
	}


def _infer_interval(timespan_value, stats_interval: str | None) -> str:
	text = (timespan_value or "").strip().lower()
	if "day" in text or text in {"today", "yesterday", "tomorrow"}:
		return "Daily"
	if "week" in text:
		return "Weekly"
	if "year" in text:
		return "Yearly"
	if "quarter" in text:
		return "Monthly"
	if "month" in text:
		return "Monthly"
	if stats_interval in {"Daily", "Weekly", "Monthly", "Yearly"}:
		return stats_interval
	return "Monthly"


def _period_bounds(interval: str, offset: int):
	today = getdate()
	if interval == "Daily":
		day = getdate(add_to_date(today, days=-offset))
		return day, day
	if interval == "Weekly":
		week_start = getdate(add_to_date(today, days=-today.weekday()))
		start = getdate(add_to_date(week_start, days=-7 * offset))
		end = getdate(add_to_date(start, days=6))
		return start, end
	if interval == "Yearly":
		year = today.year - offset
		return getdate(f"{year}-01-01"), getdate(f"{year}-12-31")

	month_anchor = getdate(add_to_date(today, months=-offset))
	start = get_first_day(month_anchor)
	end = get_last_day(month_anchor)
	return getdate(start), getdate(end)


def _aggregate_card_value(doc, filters) -> float:
	function_map = {
		"Count": "COUNT",
		"Sum": "SUM",
		"Average": "AVG",
		"Minimum": "MIN",
		"Maximum": "MAX",
	}
	function = function_map.get(doc.function or "Count", "COUNT")
	if function == "COUNT":
		fields = [{"COUNT": "*", "as": "result"}]
	else:
		if not doc.aggregate_function_based_on:
			return 0.0
		fields = [{function: doc.aggregate_function_based_on, "as": "result"}]

	rows = frappe.get_list(
		doc.document_type,
		fields=fields,
		filters=filters,
		parent_doctype=doc.parent_document_type,
		order_by=None,
	)
	if not rows:
		return 0.0
	return flt(rows[0].get("result") or 0)
