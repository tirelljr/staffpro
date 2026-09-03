# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Create and submit Client Invoice from payroll, or on an admin-configured day interval."""

from __future__ import annotations

from datetime import date

import frappe
from frappe import _
from frappe.utils import add_days, cint, comma_and, date_diff, get_link_to_form, getdate, nowdate

from hrms.payroll.auto_payroll import canonical_frequency, frequency_label, get_pay_period
from hrms.payroll.doctype.client_invoice.client_invoice import CLIENT_BILLING_CURRENCY

MAX_PERIODS_PER_RUN = 1

INVOICE_TEMPLATES = (
	("Weekly", "automatic_invoice_weekly_days", 5),
	("Fortnightly", "automatic_invoice_fortnightly_days", 10),
	("Monthly", "automatic_invoice_monthly_days", 22),
)


def get_enabled_invoice_templates(settings=None) -> list[dict]:
	if settings is None:
		settings = frappe.get_single("Payroll Settings")
	templates = []
	for frequency, field, _default in INVOICE_TEMPLATES:
		raw = settings.get(field)
		if raw in (None, ""):
			days = 0
		else:
			days = cint(raw)
		if days < 1:
			continue
		templates.append({"frequency": frequency, "interval": days, "label": frequency_label(frequency)})
	return templates


def run_scheduled_invoices():
	"""Daily scheduler entry: invoice clients after each completed billing period."""
	return process_automatic_invoices(force=False)


def backfill_invoices_for_submitted_payroll(company: str | None = None) -> list[str]:
	"""Create Client Invoices for submitted payrolls that never got one."""
	filters = {"docstatus": 1}
	if company:
		filters["company"] = company
	created = []
	for name in frappe.get_all("Payroll Entry", filters=filters, pluck="name", order_by="end_date asc"):
		created.extend(create_invoices_for_payroll_entry(frappe.get_doc("Payroll Entry", name)) or [])
	if created and not frappe.flags.in_test:
		frappe.db.commit()
	return created


def create_invoices_for_payroll_entry(doc, method=None):
	"""Payroll Entry on_submit: create the Client Invoice for the same client and period."""
	if getattr(frappe.flags, "skip_client_invoice_on_payroll", False):
		return []
	if not doc or getattr(doc, "doctype", None) != "Payroll Entry":
		return []
	if cint(getattr(doc, "docstatus", 0)) == 2:
		return []
	if not frappe.db.exists("DocType", "Client Invoice"):
		return []
	if not doc.get("start_date") or not doc.get("end_date"):
		return []

	customers = _customers_for_payroll(doc)
	if not customers:
		return []

	created = []
	failed = False
	frequency = canonical_frequency(doc.get("payroll_frequency")) or None
	for customer in customers:
		existing = find_existing_invoice(
			doc.company, customer, doc.start_date, doc.end_date, frequency=frequency
		)
		if existing and existing.docstatus == 1:
			continue
		try:
			invoice = create_or_submit_client_invoice(
				doc.company,
				customer,
				doc.start_date,
				doc.end_date,
				existing,
				frequency=frequency,
				payroll_entry=doc.name,
			)
		except Exception:
			frappe.log_error(title=_("Client invoice from payroll failed"))
			failed = True
			continue
		if invoice:
			created.append(invoice.name)

	if created and not frappe.flags.in_test:
		frappe.msgprint(
			_("Created Client Invoice {0} for this payroll period.").format(
				comma_and([get_link_to_form("Client Invoice", name) for name in created])
			),
			alert=True,
			indicator="green",
		)
	elif failed and not frappe.flags.in_test:
		frappe.msgprint(
			_("Payroll was submitted, but the Client Invoice could not be created. Check Error Log."),
			alert=True,
			indicator="orange",
		)
	return created


def _customers_for_payroll(doc) -> list[str]:
	if doc.get("customer"):
		return [doc.customer]

	employees = [row.employee for row in doc.get("employees") or [] if row.employee]
	if not employees or not frappe.get_meta("Employee").has_field("bill_to_customer"):
		return []

	rows = frappe.get_all(
		"Employee",
		filters={"name": ("in", employees), "bill_to_customer": ("is", "set")},
		pluck="bill_to_customer",
	)
	return list(dict.fromkeys(customer for customer in rows if customer))


@frappe.whitelist()
def run_automatic_invoices_now():
	if not frappe.has_permission("Client Invoice", "create"):
		frappe.throw(_("Not permitted to run client invoices"))
	return process_automatic_invoices(force=True)


@frappe.whitelist()
def set_automatic_invoice_interval(
	enable: int | None = None,
	weekly_days: int | None = None,
	fortnightly_days: int | None = None,
	monthly_days: int | None = None,
) -> dict:
	"""List UI: save auto-run days for Weekly, 2-weeks, and Monthly client invoices."""
	if not frappe.has_permission("Payroll Settings", "write"):
		frappe.throw(_("Not permitted to change invoice schedule"), frappe.PermissionError)

	settings = frappe.get_single("Payroll Settings")
	if weekly_days is not None:
		settings.automatic_invoice_weekly_days = max(cint(weekly_days), 0)
	if fortnightly_days is not None:
		settings.automatic_invoice_fortnightly_days = max(cint(fortnightly_days), 0)
	if monthly_days is not None:
		settings.automatic_invoice_monthly_days = max(cint(monthly_days), 0)
	if enable is not None:
		settings.enable_automatic_client_invoice = 1 if cint(enable) else 0
	elif not cint(settings.enable_automatic_client_invoice):
		settings.enable_automatic_client_invoice = 1
	settings.save()
	return get_automatic_invoice_status()


@frappe.whitelist()
def get_automatic_invoice_status() -> dict:
	"""List UI: interval, last run, and when the next billing period is due."""
	settings = frappe.get_single("Payroll Settings")
	enabled = cint(settings.get("enable_automatic_client_invoice"))
	templates = get_enabled_invoice_templates(settings)
	company = settings.get("automatic_payroll_company") or frappe.defaults.get_global_default("company")
	as_of = getdate(nowdate())
	start_date = end_date = None
	due = False
	open_invoice = None
	template_status = []

	if enabled and company:
		open_docs = get_open_invoices(company)
		if open_docs:
			open_invoice = open_docs[0].name
			start_date = getdate(open_docs[0].from_date)
			end_date = getdate(open_docs[0].to_date)
			due = end_date <= as_of

		for template in templates:
			last_end = get_last_invoice_end(company, frequency=template["frequency"])
			next_start, next_end = get_pay_period(
				interval=template["interval"],
				as_of=as_of,
				company=company,
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
			if open_invoice:
				continue
			if not start_date or (next_end and (not end_date or getdate(next_end) < getdate(end_date))):
				start_date = next_start
				end_date = next_end
			due = due or template_due

	days_until = date_diff(end_date, as_of) if end_date else None
	if days_until is not None and days_until <= 0:
		due = True

	interval = templates[0]["interval"] if templates else 0

	return {
		"enabled": enabled,
		"interval_days": interval,
		"weekly_days": cint(settings.get("automatic_invoice_weekly_days")),
		"fortnightly_days": cint(settings.get("automatic_invoice_fortnightly_days")),
		"monthly_days": cint(settings.get("automatic_invoice_monthly_days")),
		"templates": template_status or templates,
		"company": company,
		"last_run": settings.get("last_automatic_invoice_run"),
		"last_entry": settings.get("last_automatic_client_invoice"),
		"next_start": start_date,
		"next_end": end_date,
		"period_end": end_date,
		"days_until": days_until,
		"due": due,
		"open_entry": open_invoice,
	}


def process_automatic_invoices(force: bool = False) -> dict:
	settings = frappe.get_single("Payroll Settings")
	if not cint(settings.get("enable_automatic_client_invoice")):
		return _result(_("Automatic client invoices are turned off."))

	company = settings.get("automatic_payroll_company") or frappe.defaults.get_global_default("company")
	if not company:
		return _result(_("Set a company in Payroll Settings or Global Defaults."))

	if not settings.get("client_invoice_item"):
		return _result(_("Set Client Invoice Item in Payroll Settings."))

	as_of = getdate(nowdate())
	created = []
	skipped = []

	draft_result = submit_due_drafts(company, as_of, force=force)
	created.extend(draft_result["created"])
	skipped.extend(draft_result["skipped"])
	if draft_result.get("blocked"):
		return _result(draft_result["blocked"], created=created, skipped=skipped)

	templates = get_enabled_invoice_templates(settings)
	if not templates:
		return _result(_("Set invoice days for Weekly, 2-weeks, or Monthly."))

	customers = get_billable_customers(company)
	if not customers:
		return _result(_("No clients have agents assigned."), created=created, skipped=skipped)

	for template in templates:
		result = _process_template(settings, company, template, customers, as_of, force=force)
		created.extend(result["created"])
		skipped.extend(result["skipped"])
		if result.get("blocked"):
			return _result(result["blocked"], created=created, skipped=skipped)

	if created:
		message = _("Created client invoice {0}.").format(", ".join(created))
	elif skipped:
		message = skipped[0]
	else:
		message = _("No client invoice was due.")

	return _result(message, created=created, skipped=skipped)


def _process_template(
	settings, company: str, template: dict, customers: list[str], as_of: date, force: bool = False
) -> dict:
	created = []
	skipped = []
	frequency = template["frequency"]
	interval = template["interval"]
	last_end = get_last_invoice_end(company, frequency=frequency)

	for _ in range(MAX_PERIODS_PER_RUN):
		start_date, end_date = get_pay_period(
			interval=interval,
			as_of=as_of,
			company=company,
			cycle_start=settings.get("automatic_payroll_cycle_start"),
			last_end=last_end if last_end is not None else "",
		)
		if not start_date or not end_date:
			skipped.append(_("Could not determine the next {0} invoice period.").format(template["label"]))
			break

		if not force and getdate(end_date) >= as_of:
			skipped.append(
				_("Next {0} invoice period {1} to {2} has not ended yet.").format(
					template["label"],
					frappe.format(start_date, {"fieldtype": "Date"}),
					frappe.format(end_date, {"fieldtype": "Date"}),
				)
			)
			break

		period_created = False
		for customer in customers:
			existing = find_existing_invoice(
				company, customer, start_date, end_date, frequency=frequency
			)
			if existing and existing.docstatus == 1:
				continue

			try:
				invoice = create_or_submit_client_invoice(
					company, customer, start_date, end_date, existing, frequency=frequency
				)
			except Exception:
				frappe.log_error(title=_("Automatic client invoice failed"))
				return {
					"created": created,
					"skipped": skipped,
					"blocked": _("Automatic client invoices failed. Check Error Log."),
				}

			if not invoice:
				continue

			created.append(invoice.name)
			period_created = True
			mark_last_run(as_of, invoice.name)

		if not period_created:
			skipped.append(
				_("No billable attendance for the {0} period {1} to {2}.").format(
					template["label"],
					frappe.format(start_date, {"fieldtype": "Date"}),
					frappe.format(end_date, {"fieldtype": "Date"}),
				)
			)

		last_end = getdate(end_date)
		if getdate(end_date) >= add_days(as_of, -1):
			break

	return {"created": created, "skipped": skipped, "blocked": None}


def submit_due_drafts(company: str, as_of: date, force: bool = False) -> dict:
	"""Submit leftover draft Client Invoices whose billing period has ended."""
	created = []
	skipped = []
	for draft in get_open_invoices(company):
		if not draft.to_date:
			skipped.append(_("Client Invoice {0} has no end date.").format(draft.name))
			continue
		end_date = getdate(draft.to_date)
		if not force and end_date >= as_of:
			return {
				"created": created,
				"skipped": skipped,
				"blocked": _("Client Invoice {0} is waiting until {1} ends.").format(
					draft.name,
					frappe.format(end_date, {"fieldtype": "Date"}),
				),
			}

		existing = frappe.get_doc("Client Invoice", draft.name)
		try:
			invoice = create_or_submit_client_invoice(
				company, existing.customer, existing.from_date, existing.to_date, existing
			)
		except Exception:
			frappe.log_error(title=_("Automatic client invoice failed"))
			return {
				"created": created,
				"skipped": skipped,
				"blocked": _("Automatic client invoices failed. Check Error Log."),
			}

		if not invoice:
			skipped.append(_("No billable attendance for Client Invoice {0}.").format(draft.name))
			continue

		created.append(invoice.name)
		mark_last_run(as_of, invoice.name)

	return {"created": created, "skipped": skipped, "blocked": None}


def get_billable_customers(company: str) -> list[str]:
	if not frappe.get_meta("Employee").has_field("bill_to_customer"):
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


def get_last_invoice_end(company: str, frequency: str | None = None):
	filters = {"company": company, "docstatus": 1}
	if frequency and frappe.get_meta("Client Invoice").has_field("billing_frequency"):
		filters["billing_frequency"] = frequency

	last_end = frappe.db.get_value("Client Invoice", filters, "to_date", order_by="to_date desc")
	return getdate(last_end) if last_end else None


def get_open_invoices(company: str) -> list:
	return frappe.get_all(
		"Client Invoice",
		filters={"company": company, "docstatus": 0},
		fields=["name", "from_date", "to_date", "customer"],
		order_by="to_date asc",
	)


def find_existing_invoice(
	company: str, customer: str, start_date, end_date, frequency: str | None = None
):
	filters = {
		"company": company,
		"customer": customer,
		"from_date": getdate(start_date),
		"to_date": getdate(end_date),
		"docstatus": ("<", 2),
	}
	if frequency and frappe.get_meta("Client Invoice").has_field("billing_frequency"):
		filters["billing_frequency"] = frequency

	name = frappe.db.get_value(
		"Client Invoice", filters, "name", order_by="docstatus desc, creation desc"
	)
	if not name:
		return None
	return frappe.get_doc("Client Invoice", name)


def create_or_submit_client_invoice(
	company,
	customer,
	start_date,
	end_date,
	existing=None,
	frequency: str | None = None,
	payroll_entry: str | None = None,
):
	if existing and existing.docstatus == 1:
		return existing

	invoice = existing
	if not invoice:
		invoice = frappe.new_doc("Client Invoice")
		invoice.customer = customer
		invoice.company = company
		invoice.from_date = getdate(start_date)
		invoice.to_date = getdate(end_date)
		invoice.posting_date = getdate(end_date) or nowdate()
		invoice.currency = CLIENT_BILLING_CURRENCY
		if frequency and invoice.meta.has_field("billing_frequency"):
			invoice.billing_frequency = frequency
	if payroll_entry and invoice.meta.has_field("payroll_entry") and not invoice.get("payroll_entry"):
		invoice.payroll_entry = payroll_entry

	try:
		invoice.get_agents(include_zero_hours=True)
	except frappe.ValidationError:
		frappe.clear_messages()
		if existing and existing.docstatus == 0:
			return None
		return None

	invoice.flags.ignore_permissions = True
	if invoice.is_new():
		invoice.insert()
	else:
		invoice.save()

	if invoice.docstatus == 0:
		invoice.flags.ignore_permissions = True
		invoice.submit()
		invoice.reload()

	return invoice


def mark_last_run(as_of, invoice_name: str):
	frappe.db.set_single_value(
		"Payroll Settings",
		{
			"last_automatic_invoice_run": as_of,
			"last_automatic_client_invoice": invoice_name,
		},
		update_modified=False,
	)


def _result(message: str, created: list | None = None, skipped: list | None = None) -> dict:
	return {"message": message, "created": created or [], "skipped": skipped or []}
