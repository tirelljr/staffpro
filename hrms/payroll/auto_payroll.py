# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Create and run Payroll Entry on an admin-configured day interval."""

from __future__ import annotations

from datetime import date

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, getdate, nowdate

MAX_PERIODS_PER_RUN = 3

PAYROLL_TEMPLATES = (
	("Weekly", "automatic_payroll_weekly_days", 5),
	("Fortnightly", "automatic_payroll_fortnightly_days", 10),
	("Monthly", "automatic_payroll_monthly_days", 22),
)
WEEKEND_WEEKDAYS = {5, 6}  # Saturday, Sunday
FREQUENCY_ALIASES = {
	"weekly": "Weekly",
	"fortnightly": "Fortnightly",
	"2 weeks": "Fortnightly",
	"2weeks": "Fortnightly",
	"2-weeks": "Fortnightly",
	"2-week": "Fortnightly",
	"2 week": "Fortnightly",
	"monthly": "Monthly",
	"bimonthly": "Bimonthly",
	"daily": "Daily",
}
FREQUENCY_LABELS = {
	"Weekly": "Weekly",
	"Fortnightly": "2-weeks",
	"Monthly": "Monthly",
	"Bimonthly": "Twice a Month",
	"Daily": "Daily",
}


def is_working_day(on_date) -> bool:
	return getdate(on_date).weekday() not in WEEKEND_WEEKDAYS


def add_working_days(start_date, working_days: int):
	"""Nth Monday–Friday on or after start_date. Start counts when it is a weekday."""
	current = getdate(start_date)
	remaining = max(cint(working_days), 1)
	while True:
		if is_working_day(current):
			remaining -= 1
			if remaining == 0:
				return current
		current = add_days(current, 1)


def subtract_working_days(end_date, working_days: int):
	"""Start date of an N-weekday period that ends on end_date (inclusive)."""
	current = getdate(end_date)
	remaining = max(cint(working_days), 1)
	while True:
		if is_working_day(current):
			remaining -= 1
			if remaining == 0:
				return current
		current = add_days(current, -1)


@frappe.whitelist()
def get_working_period_end(start_date, working_days: int | None = None):
	"""Form helper: end date N working days from start. Default is a 2-week (10-day) period."""
	if not start_date:
		return {"end_date": None}
	days = cint(working_days) if working_days not in (None, "") else 10
	if days < 1:
		days = 10
	return {"end_date": add_working_days(getdate(start_date), days).strftime("%Y-%m-%d")}


def canonical_frequency(name: str | None) -> str:
	if not name:
		return ""
	key = " ".join(str(name).strip().lower().split())
	return FREQUENCY_ALIASES.get(key.replace(" ", ""), FREQUENCY_ALIASES.get(key, name))


def frequency_label(name: str | None) -> str:
	frequency = canonical_frequency(name)
	return FREQUENCY_LABELS.get(frequency, frequency or "")


def days_for_frequency(frequency: str | None, settings=None) -> int:
	frequency = canonical_frequency(frequency)
	if not frequency:
		return 14
	if settings is None:
		settings = frappe.get_single("Payroll Settings")
	for name, field, default in PAYROLL_TEMPLATES:
		if name != frequency:
			continue
		days = cint(settings.get(field))
		if days:
			return max(days, 1)
		if settings.get("automatic_payroll_frequency") == frequency:
			legacy = cint(settings.get("automatic_payroll_interval_days"))
			if legacy:
				return max(legacy, 1)
		return default
	if frequency == "Daily":
		return 1
	if frequency == "Bimonthly":
		return 15
	return max(cint(settings.get("automatic_payroll_interval_days")) or 14, 1)


def get_enabled_templates(settings=None) -> list[dict]:
	if settings is None:
		settings = frappe.get_single("Payroll Settings")
	templates = []
	for frequency, field, default in PAYROLL_TEMPLATES:
		raw = settings.get(field)
		if raw in (None, ""):
			days = 0
		else:
			days = cint(raw)
		if days < 1:
			continue
		templates.append({"frequency": frequency, "interval": days, "label": frequency_label(frequency)})
	return templates


def run_scheduled_payroll():
	"""Daily scheduler entry: run payroll after each completed pay period."""
	return process_automatic_payroll(force=False)


@frappe.whitelist()
def run_automatic_payroll_now():
	if not frappe.has_permission("Payroll Entry", "create"):
		frappe.throw(_("Not permitted to run payroll"))
	return process_automatic_payroll(force=True)


@frappe.whitelist()
def set_automatic_payroll_interval(
	interval_days: int | None = None,
	enable: int | None = None,
	weekly_days: int | None = None,
	fortnightly_days: int | None = None,
	monthly_days: int | None = None,
) -> dict:
	"""List UI: save auto-run days for Weekly, 2-weeks, and Monthly templates."""
	if not frappe.has_permission("Payroll Settings", "write"):
		frappe.throw(_("Not permitted to change payroll schedule"), frappe.PermissionError)

	settings = frappe.get_single("Payroll Settings")
	if weekly_days is not None:
		settings.automatic_payroll_weekly_days = max(cint(weekly_days), 0)
	if fortnightly_days is not None:
		settings.automatic_payroll_fortnightly_days = max(cint(fortnightly_days), 0)
	if monthly_days is not None:
		settings.automatic_payroll_monthly_days = max(cint(monthly_days), 0)
	if interval_days is not None and fortnightly_days is None:
		settings.automatic_payroll_fortnightly_days = max(cint(interval_days), 0)
		settings.automatic_payroll_interval_days = max(cint(interval_days), 1)
	if enable is not None:
		settings.enable_automatic_payroll = 1 if cint(enable) else 0
	elif not cint(settings.enable_automatic_payroll):
		settings.enable_automatic_payroll = 1
	settings.save()
	return get_automatic_payroll_status()


@frappe.whitelist()
def get_automatic_payroll_status() -> dict:
	"""List/settings UI: interval, last run, and when the next period is due."""
	settings = frappe.get_single("Payroll Settings")
	enabled = cint(settings.get("enable_automatic_payroll"))
	templates = get_enabled_templates(settings)
	company = settings.get("automatic_payroll_company") or frappe.defaults.get_global_default("company")
	as_of = getdate(nowdate())
	start_date = end_date = None
	due = False
	open_entry = None
	template_status = []

	if enabled and company:
		open_docs = get_open_entries(company, settings.get("automatic_payroll_branch"))
		if open_docs:
			open_entry = open_docs[0].name
			start_date = getdate(open_docs[0].start_date)
			end_date = getdate(open_docs[0].end_date)
			due = end_date <= as_of

		for template in templates:
			last_end = get_last_payroll_end(
				company, settings.get("automatic_payroll_branch"), frequency=template["frequency"]
			)
			next_start, next_end = get_pay_period(
				interval=template["interval"],
				as_of=as_of,
				company=company,
				branch=settings.get("automatic_payroll_branch"),
				cycle_start=settings.get("automatic_payroll_cycle_start"),
				last_end=last_end if last_end is not None else "",
			)
			template_due = bool(next_end and getdate(next_end) <= as_of)
			template_status.append(
				{
					**template,
					"next_start": next_start,
					"next_end": next_end,
					"due": template_due,
				}
			)
			if open_entry:
				continue
			if not start_date or (next_end and (not end_date or getdate(next_end) < getdate(end_date))):
				start_date = next_start
				end_date = next_end
			due = due or template_due

	days_until = date_diff(end_date, as_of) if end_date else None
	if days_until is not None and days_until <= 0:
		due = True

	interval = templates[0]["interval"] if templates else max(
		cint(settings.get("automatic_payroll_interval_days")) or 14, 1
	)

	return {
		"enabled": enabled,
		"interval_days": interval,
		"weekly_days": cint(settings.get("automatic_payroll_weekly_days")),
		"fortnightly_days": cint(settings.get("automatic_payroll_fortnightly_days")),
		"monthly_days": cint(settings.get("automatic_payroll_monthly_days")),
		"templates": template_status or templates,
		"frequency": settings.get("automatic_payroll_frequency"),
		"company": company,
		"last_run": settings.get("last_automatic_payroll_run"),
		"last_entry": settings.get("last_automatic_payroll_entry"),
		"next_start": start_date,
		"next_end": end_date,
		"period_end": end_date,
		"days_until": days_until,
		"due": due,
		"open_entry": open_entry,
	}


def process_automatic_payroll(force: bool = False) -> dict:
	settings = frappe.get_single("Payroll Settings")
	if not cint(settings.get("enable_automatic_payroll")):
		return _result(_("Automatic payroll is turned off in Payroll Settings."))

	company = settings.get("automatic_payroll_company") or frappe.defaults.get_global_default("company")
	if not company:
		return _result(_("Set a company in Payroll Settings or Global Defaults."))

	as_of = getdate(nowdate())
	created = []
	skipped = []

	draft_result = submit_due_drafts(settings, company, as_of, force=force)
	created.extend(draft_result["created"])
	skipped.extend(draft_result["skipped"])
	if draft_result.get("blocked"):
		return _result(draft_result["blocked"], created=created, skipped=skipped)

	templates = get_enabled_templates(settings)
	if not templates:
		return _result(_("Set auto-run days for Weekly, 2-weeks, or Monthly."))

	for template in templates:
		result = _process_template(settings, company, template, as_of, force=force)
		created.extend(result["created"])
		skipped.extend(result["skipped"])
		if result.get("blocked"):
			return _result(result["blocked"], created=created, skipped=skipped)

	if created:
		message = _("Created payroll {0}.").format(", ".join(created))
	elif skipped:
		message = skipped[0]
	else:
		message = _("No payroll was due.")

	return _result(message, created=created, skipped=skipped)


def _process_template(settings, company: str, template: dict, as_of: date, force: bool = False) -> dict:
	created = []
	skipped = []
	frequency = template["frequency"]
	interval = template["interval"]
	last_end = get_last_payroll_end(company, settings.get("automatic_payroll_branch"), frequency=frequency)
	customers = get_payroll_customers(company) or [None]

	for _ in range(MAX_PERIODS_PER_RUN):
		start_date, end_date = get_pay_period(
			interval=interval,
			as_of=as_of,
			company=company,
			branch=settings.get("automatic_payroll_branch"),
			cycle_start=settings.get("automatic_payroll_cycle_start"),
			last_end=last_end if last_end is not None else "",
		)
		if not start_date or not end_date:
			skipped.append(_("Could not determine the next {0} pay period.").format(template["label"]))
			break

		if not force and getdate(end_date) >= as_of:
			skipped.append(
				_("Next {0} pay period {1} to {2} has not ended yet.").format(
					template["label"],
					frappe.format(start_date, {"fieldtype": "Date"}),
					frappe.format(end_date, {"fieldtype": "Date"}),
				)
			)
			break

		period_created = False
		for customer in customers:
			existing = find_existing_entry(
				company,
				start_date,
				end_date,
				branch=settings.get("automatic_payroll_branch"),
				frequency=frequency,
				customer=customer,
			)
			if existing and existing.docstatus == 1:
				continue

			try:
				entry = create_or_submit_payroll_entry(
					settings,
					company,
					start_date,
					end_date,
					existing,
					frequency=frequency,
					customer=customer,
				)
			except Exception:
				frappe.log_error(title=_("Automatic payroll failed"))
				return {
					"created": created,
					"skipped": skipped,
					"blocked": _("Automatic payroll failed. Check Error Log."),
				}

			if not entry:
				continue

			created.append(entry.name)
			period_created = True
			mark_last_run(as_of, entry.name)

		if not period_created:
			skipped.append(_("No agents found for the {0} pay period.").format(template["label"]))
			break

		last_end = getdate(end_date)
		if getdate(end_date) >= add_days(as_of, -1):
			break

	return {"created": created, "skipped": skipped, "blocked": None}


def submit_due_drafts(settings, company: str, as_of: date, force: bool = False) -> dict:
	"""Submit leftover draft Payroll Entries whose pay period has ended."""
	created = []
	skipped = []
	for draft in get_open_entries(company, settings.get("automatic_payroll_branch")):
		if not draft.end_date:
			skipped.append(_("Payroll Entry {0} has no end date.").format(draft.name))
			continue
		end_date = getdate(draft.end_date)
		if not force and end_date >= as_of:
			return {
				"created": created,
				"skipped": skipped,
				"blocked": _("Payroll Entry {0} is waiting until {1} ends.").format(
					draft.name,
					frappe.format(end_date, {"fieldtype": "Date"}),
				),
			}

		existing = frappe.get_doc("Payroll Entry", draft.name)
		try:
			entry = create_or_submit_payroll_entry(
				settings,
				company,
				existing.start_date,
				existing.end_date,
				existing,
				frequency=existing.payroll_frequency,
				customer=existing.get("customer"),
			)
		except Exception:
			frappe.log_error(title=_("Automatic payroll failed"))
			return {
				"created": created,
				"skipped": skipped,
				"blocked": _("Automatic payroll failed. Check Error Log."),
			}

		if not entry:
			skipped.append(_("No agents found for Payroll Entry {0}.").format(draft.name))
			continue

		created.append(entry.name)
		mark_last_run(as_of, entry.name)

	return {"created": created, "skipped": skipped, "blocked": None}


def get_pay_period(
	interval: int,
	as_of: date,
	company: str,
	branch: str | None = None,
	cycle_start: date | str | None = None,
	last_end: date | str | None = None,
) -> tuple[date | None, date | None]:
	interval = max(cint(interval), 1)
	as_of = getdate(as_of)

	if last_end is None:
		last_end = get_last_payroll_end(company, branch)
	elif last_end == "":
		last_end = None

	if last_end:
		start_date = add_days(getdate(last_end), 1)
		end_date = add_working_days(start_date, interval)
		return getdate(start_date), getdate(end_date)

	anchor = getdate(cycle_start) if cycle_start else None
	if not anchor:
		# First run: the most recently completed N-working-day window, ending yesterday.
		end_date = add_days(as_of, -1)
		start_date = subtract_working_days(end_date, interval)
		return getdate(start_date), getdate(end_date)

	start_date = anchor
	end_date = add_working_days(start_date, interval)
	return getdate(start_date), getdate(end_date)


def get_last_payroll_end(company: str, branch: str | None = None, frequency: str | None = None):
	filters = {"company": company, "docstatus": 1}
	if branch:
		filters["branch"] = branch
	if frequency:
		filters["payroll_frequency"] = canonical_frequency(frequency)

	last_end = frappe.db.get_value("Payroll Entry", filters, "end_date", order_by="end_date desc")
	return getdate(last_end) if last_end else None


def get_open_entries(company: str, branch: str | None = None) -> list:
	filters = {"company": company, "docstatus": 0}
	if branch:
		filters["branch"] = branch
	return frappe.get_all(
		"Payroll Entry",
		filters=filters,
		fields=["name", "start_date", "end_date"],
		order_by="end_date asc",
	)


def find_existing_entry(
	company: str,
	start_date,
	end_date,
	branch: str | None = None,
	frequency: str | None = None,
	customer: str | None = None,
):
	filters = {
		"company": company,
		"start_date": getdate(start_date),
		"end_date": getdate(end_date),
		"docstatus": ("<", 2),
	}
	if branch:
		filters["branch"] = branch
	if frequency:
		filters["payroll_frequency"] = canonical_frequency(frequency)
	if customer:
		filters["customer"] = customer

	name = frappe.db.get_value("Payroll Entry", filters, "name", order_by="docstatus desc, creation desc")
	if not name:
		return None
	return frappe.get_doc("Payroll Entry", name)


def get_payroll_customers(company: str) -> list[str]:
	"""Clients that have active agents assigned via Employee.bill_to_customer."""
	if not frappe.get_meta("Employee").has_field("bill_to_customer"):
		return []
	if not frappe.get_meta("Payroll Entry").has_field("customer"):
		return []
	rows = frappe.get_all(
		"Employee",
		filters={
			"company": company,
			"status": "Active",
			"bill_to_customer": ("is", "set"),
		},
		pluck="bill_to_customer",
	)
	return list(dict.fromkeys(customer for customer in rows if customer))


def create_or_submit_payroll_entry(
	settings,
	company,
	start_date,
	end_date,
	existing=None,
	frequency: str | None = None,
	customer: str | None = None,
):
	frappe.flags.skip_payroll_enqueue = True

	to_submit = []
	if existing and existing.docstatus == 0:
		entry = existing
		if customer and not entry.get("customer"):
			entry.customer = customer
		if not entry.employees:
			try:
				entry.fill_employee_details()
			except frappe.ValidationError:
				return None
			entry.save(ignore_permissions=True)
		to_submit = [entry]
	else:
		frequencies = [frequency] if frequency else get_payroll_frequencies(company, settings)
		for freq in frequencies:
			entry = build_payroll_entry(settings, company, start_date, end_date, freq, customer=customer)
			try:
				entry.fill_employee_details()
			except frappe.ValidationError:
				continue
			entry.flags.ignore_permissions = True
			entry.insert()
			to_submit.append(entry)

	if not to_submit:
		return None

	last = None
	for entry in to_submit:
		if entry.docstatus == 0:
			entry.flags.ignore_permissions = True
			entry.submit()
		entry.reload()
		if cint(settings.get("automatic_payroll_submit_slips")) and entry.docstatus == 1:
			if not cint(entry.salary_slips_submitted):
				entry.submit_salary_slips()
				entry.reload()
		last = entry

	return last


def get_payroll_frequencies(company: str, settings=None) -> list[str]:
	"""Return enabled templates that match live salary structures."""
	configured = None
	if isinstance(settings, str):
		configured = settings
		settings = frappe.get_single("Payroll Settings")
	elif settings is None:
		settings = frappe.get_single("Payroll Settings")

	enabled = [template["frequency"] for template in get_enabled_templates(settings)]
	active = list(
		dict.fromkeys(
			canonical_frequency(freq)
			for freq in frappe.get_all(
				"Salary Structure",
				filters={
					"company": company,
					"docstatus": 1,
					"is_active": "Yes",
				},
				pluck="payroll_frequency",
			)
			if freq
		)
	)
	matched = [freq for freq in enabled if freq in active]
	if matched:
		return matched
	if enabled:
		return enabled
	return [configured or "Fortnightly"]


def build_payroll_entry(
	settings, company, start_date, end_date, frequency: str | None = None, customer: str | None = None
):
	company_doc = frappe.get_cached_doc("Company", company)
	currency = company_doc.default_currency
	cost_center = company_doc.cost_center
	if not cost_center:
		cost_center = frappe.db.get_value(
			"Cost Center", {"company": company, "is_group": 0}, "name", order_by="creation"
		)

	if not cost_center:
		frappe.throw(_("Set a Cost Center on Company {0}.").format(company))

	entry = frappe.new_doc("Payroll Entry")
	entry.company = company
	entry.customer = customer
	entry.posting_date = nowdate()
	entry.start_date = getdate(start_date)
	entry.end_date = getdate(end_date)
	entry.payroll_frequency = canonical_frequency(frequency) or "Fortnightly"
	# Floor time lives on Attendance / check-ins, not Timesheets.
	entry.salary_slip_based_on_timesheet = 0
	entry.deduct_social_security = 1
	entry.currency = currency
	entry.exchange_rate = 1
	entry.cost_center = cost_center
	entry.branch = settings.get("automatic_payroll_branch") or None
	entry.validate_attendance = 0
	from hrms.hr.belize_banks import get_default_payroll_bank_account

	entry.bank_account = get_default_payroll_bank_account(company)
	return entry


def mark_last_run(as_of, entry_name: str):
	frappe.db.set_single_value(
		"Payroll Settings",
		{
			"last_automatic_payroll_run": as_of,
			"last_automatic_payroll_entry": entry_name,
		},
		update_modified=False,
	)


def _result(message: str, created: list | None = None, skipped: list | None = None) -> dict:
	return {"message": message, "created": created or [], "skipped": skipped or []}
