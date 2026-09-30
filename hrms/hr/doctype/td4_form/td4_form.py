# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Belize TD4 Supplementary form completed and signed in the agent portal."""

from __future__ import annotations

import base64
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, escape_html, flt, getdate, now_datetime, today
from frappe.utils.file_manager import save_file
from frappe.utils.pdf import get_pdf

from hrms.hr.agent_filesystem import upload_file
from hrms.hr.doctype.agent_document.agent_document import get_session_employee, is_hr_user
from hrms.hr.doctype.document_category.document_category import seed_document_categories

TAX_FORMS_CATEGORY = "Tax Forms"
DISMISS_LIMIT = 3
EDITABLE_FIELDS = (
	"reporting_year",
	"employee_address",
	"social_security",
	"employee_tin",
	"number_of_weeks",
	"total_income",
	"total_taxable_income",
	"non_taxable_income",
	"commissions",
	"tax_deducted",
	"date_signed",
	"signature",
)
PUBLIC_FIELDS = (
	"name",
	"employee",
	"employee_name",
	"company",
	"status",
	"reporting_year",
	"date_signed",
	"employer_name",
	"employer_address",
	"employer_tin",
	"employee_address",
	"social_security",
	"employee_tin",
	"number_of_weeks",
	"total_income",
	"total_taxable_income",
	"non_taxable_income",
	"commissions",
	"tax_deducted",
	"signature",
	"signed_pdf",
	"filled_by",
	"filled_by_name",
	"filled_on",
	"dismiss_count",
)


class TD4Form(Document):
	def validate(self):
		previous = self.get_doc_before_save()
		if previous and previous.status == "Submitted":
			frappe.throw(_("A submitted TD4 cannot be changed."))
		if not self.employee or not frappe.db.exists("Employee", self.employee):
			frappe.throw(_("Agent is required."))
		self._apply_locked_fields()
		if self.status == "Requested":
			self._assert_single_open_request()
		elif self.status == "Submitted":
			self._validate_submission()
		else:
			frappe.throw(_("Status must be Requested or Submitted."))

	def after_insert(self):
		if self.status == "Requested" and not self.flags.skip_notify:
			notify_employee(self)

	def on_update(self):
		if self.flags.td4_filing or self.status != "Submitted" or self.signed_pdf:
			return
		self.flags.td4_filing = True
		file_signed_copy(self)

	def _apply_locked_fields(self):
		identity = employee_identity(self.employee)
		self.employee_name = identity["employee_name"]
		self.company = identity["company"]
		self.employer_name = identity["employer_name"]
		self.employer_address = identity["employer_address"]
		self.employer_tin = identity["employer_tin"]
		if self.is_new() and not self.employee_address:
			self.employee_address = identity["employee_address"]
		if self.is_new() and not self.social_security:
			self.social_security = identity["social_security"]
		if self.is_new() and not self.employee_tin:
			self.employee_tin = identity["employee_tin"]

	def _assert_single_open_request(self):
		existing = frappe.db.exists(
			"TD4 Form",
			{"employee": self.employee, "status": "Requested", "name": ["!=", self.name]},
		)
		if existing:
			frappe.throw(_("This agent already has an open TD4 request."))

	def _validate_submission(self):
		year = cint(self.reporting_year)
		if year < 2000 or year > 2100:
			frappe.throw(_("Choose a reporting year."))
		self.reporting_year = year

		if not cstr(self.employee_address).strip():
			frappe.throw(_("Employee address is required."))
		if not cstr(self.social_security).strip():
			frappe.throw(_("Social security number is required."))
		if not cstr(self.employee_tin).strip():
			frappe.throw(_("Employee TIN is required."))
		self._tag_filler()

		weeks = flt(self.number_of_weeks)
		if weeks != int(weeks) or int(weeks) < 1 or int(weeks) > 53:
			frappe.throw(_("Number of weeks must be a whole number from 1 to 53."))
		self.number_of_weeks = int(weeks)

		amounts = {
			"total_income": _("Total income"),
			"total_taxable_income": _("Taxable income"),
			"non_taxable_income": _("Non-taxable income"),
			"commissions": _("Commissions"),
			"tax_deducted": _("Tax deducted"),
		}
		for fieldname, label in amounts.items():
			amount = flt(self.get(fieldname))
			if amount < 0:
				frappe.throw(_("{0} cannot be negative.").format(label))
			self.set(fieldname, flt(amount, 2))

		expected = _cents(self.total_taxable_income) + _cents(self.non_taxable_income) + _cents(self.commissions)
		if _cents(self.total_income) != expected:
			frappe.throw(
				_("Total income (C) must equal taxable income (D) + non-taxable income (E) + commissions (F).")
			)

		if not self.date_signed:
			frappe.throw(_("Date signed is required."))
		if getdate(self.date_signed) > getdate(today()):
			frappe.throw(_("Date signed cannot be in the future."))

		_decode_signature(self.signature)

	def _tag_filler(self):
		if self.filled_by:
			return
		user = frappe.session.user
		if not user or user == "Guest":
			return
		self.filled_by = user
		self.filled_by_name = frappe.db.get_value("User", user, "full_name") or user
		self.filled_on = now_datetime()


def _cents(value) -> int:
	return int(round(flt(value) * 100))


def _decode_signature(signature: str | None) -> bytes:
	match = re.match(r"^data:image/png;base64,([A-Za-z0-9+/=\s]+)$", cstr(signature).strip())
	if not match:
		frappe.throw(_("Sign the form before submitting."))
	try:
		raw = base64.b64decode(match.group(1), validate=True)
	except Exception:
		frappe.throw(_("Sign the form before submitting."))
	if len(raw) < 40 or len(raw) > 500_000:
		frappe.throw(_("Sign the form before submitting."))
	return raw


def employee_identity(employee: str) -> dict:
	meta = frappe.get_meta("Employee")
	fields = ["employee_name", "company", "current_address", "permanent_address"]
	if meta.has_field("pan_number") and frappe.db.has_column("Employee", "pan_number"):
		fields.append("pan_number")
	if meta.has_field("social_security_number") and frappe.db.has_column("Employee", "social_security_number"):
		fields.append("social_security_number")
	row = frappe.db.get_value("Employee", employee, fields, as_dict=True)
	if not row:
		frappe.throw(_("Agent {0} was not found.").format(employee))
	if not row.company:
		frappe.throw(_("Agent {0} has no company.").format(employee))

	company_name = row.company
	employer_tin = ""
	if frappe.db.exists("DocType", "Company"):
		company_meta = frappe.get_meta("Company")
		company_fields = ["company_name"]
		if company_meta.has_field("tax_id"):
			company_fields.append("tax_id")
		company = frappe.db.get_value("Company", row.company, company_fields, as_dict=True) or {}
		company_name = company.get("company_name") or row.company
		employer_tin = cstr(company.get("tax_id") or "")

	return {
		"employee_name": row.employee_name or employee,
		"company": row.company,
		"employer_name": company_name,
		"employer_address": company_address(row.company),
		"employer_tin": employer_tin,
		"employee_address": cstr(row.current_address or row.permanent_address or ""),
		"social_security": cstr(row.get("social_security_number") or ""),
		"employee_tin": cstr(row.get("pan_number") or ""),
	}


def company_address(company: str) -> str:
	try:
		from frappe.contacts.doctype.address.address import get_address_display, get_default_address
	except ImportError:
		return ""
	address_name = get_default_address("Company", company)
	if not address_name:
		return ""
	display = cstr(get_address_display(address_name))
	text = re.sub(r"(?i)<br\s*/?>", "\n", display)
	text = re.sub(r"<[^>]+>", "", text)
	return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def public_dict(doc) -> dict:
	payload = {field: doc.get(field) for field in PUBLIC_FIELDS}
	if payload.get("date_signed"):
		payload["date_signed"] = cstr(payload["date_signed"])
	if payload.get("filled_on"):
		payload["filled_on"] = cstr(payload["filled_on"])
	payload["dismiss_count"] = cint(payload.get("dismiss_count"))
	return payload


def pending_name(employee: str) -> str | None:
	return frappe.db.get_value("TD4 Form", {"employee": employee, "status": "Requested"}, "name")


def has_submitted(employee: str) -> bool:
	return bool(frappe.db.exists("TD4 Form", {"employee": employee, "status": "Submitted"}))


def create_requested(employee: str, notify: bool = True):
	doc = frappe.new_doc("TD4 Form")
	doc.employee = employee
	doc.status = "Requested"
	doc.flags.skip_notify = not notify
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def notify_employee(doc) -> None:
	user_id = frappe.db.get_value("Employee", doc.employee, "user_id")
	if not user_id or user_id == "Administrator":
		return
	from_user = frappe.session.user if frappe.session.user not in (None, "Guest") else user_id
	notification = frappe.new_doc("PWA Notification")
	notification.from_user = from_user
	notification.to_user = user_id
	notification.message = _("Please complete your TD4 tax form.")
	notification.reference_document_type = "TD4 Form"
	notification.reference_document_name = doc.name
	notification.insert(ignore_permissions=True)


def _assert_reader(doc) -> None:
	if is_hr_user():
		return
	if get_session_employee() == doc.employee:
		return
	frappe.throw(_("You can only open your own TD4."), frappe.PermissionError)


def _assert_owner(doc) -> None:
	if get_session_employee() != doc.employee:
		frappe.throw(_("You can only complete your own TD4."), frappe.PermissionError)


def file_signed_copy(doc) -> None:
	seed_document_categories()
	pdf_bytes = get_pdf(render_td4_html(doc))
	filename = pdf_filename(doc)
	saved = save_file(filename, pdf_bytes, "TD4 Form", doc.name, is_private=1, df="signed_pdf")
	doc.signed_pdf = saved.file_url
	notes = f"Signed TD4 {doc.name}"
	if frappe.db.exists("Agent Document", {"employee": doc.employee, "notes": notes}):
		return
	upload_file(
		employee=doc.employee,
		category=TAX_FORMS_CATEGORY,
		filename=filename,
		content=base64.b64encode(pdf_bytes).decode(),
		notes=notes,
	)


def pdf_filename(doc) -> str:
	year = cint(doc.reporting_year) or "form"
	safe_name = re.sub(r"[^A-Za-z0-9]+", "-", cstr(doc.employee_name)).strip("-") or cstr(doc.employee)
	return f"TD4-{year}-{safe_name}.pdf"


def render_td4_html(doc) -> str:
	return (
		"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>"
		"body { font-family: Arial, Helvetica, sans-serif; color: #1f2933; font-size: 12px; }"
		".copy { border: 1px solid #1f4e79; padding: 16px 18px 20px; margin: 0 0 18px; }"
		".copy + .copy { page-break-before: always; }"
		"header { text-align: center; border-bottom: 2px solid #1f4e79; margin-bottom: 12px; padding-bottom: 8px; }"
		"h1 { font-size: 18px; margin: 2px 0; letter-spacing: 0.04em; }"
		"h2 { font-size: 11px; margin: 0 0 4px; text-transform: uppercase; color: #1f4e79; }"
		".country { font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; }"
		".copy-label { font-weight: bold; }"
		".note { font-size: 11px; }"
		".parties { display: table; width: 100%; margin: 8px 0; }"
		".parties > div { display: table-cell; width: 50%; vertical-align: top; padding-right: 12px; }"
		".year { font-weight: bold; }"
		"table { width: 100%; border-collapse: collapse; margin-top: 8px; }"
		"th, td { border: 1px solid #c5d0dc; padding: 6px 8px; text-align: left; }"
		"th { width: 58%; background: #f4f7fb; font-weight: 600; }"
		".signoff { margin-top: 16px; display: table; width: 100%; }"
		".signoff > div { display: table-cell; width: 50%; vertical-align: bottom; }"
		".label { font-size: 11px; color: #52606d; margin-bottom: 4px; }"
		".sign { height: 64px; }"
		".date { font-size: 14px; border-bottom: 1px solid #1f2933; display: inline-block; min-width: 140px; padding-bottom: 2px; }"
		"</style></head><body>"
		+ _certificate(doc, "For Employee")
		+ _certificate(doc, "For Employer")
		+ "</body></html>"
	)


def _certificate(doc, copy_label: str) -> str:
	rows = (
		("(A) Social Security", doc.social_security),
		("(B) Number of Weeks", doc.number_of_weeks),
		("(C) Total Income from Employment", _money(doc.total_income)),
		("(D) Total Taxable Income", _money(doc.total_taxable_income)),
		("(E) Non-Taxable Income", _money(doc.non_taxable_income)),
		("(F) Commissions", _money(doc.commissions)),
		("(G) Tax Deducted at Source", _money(doc.tax_deducted)),
		("(H) Employer TIN", doc.employer_tin),
		("(I) Employee TIN", doc.employee_tin),
	)
	body = "".join(
		"<tr><th>"
		+ escape_html(cstr(label))
		+ "</th><td>"
		+ escape_html(cstr(value))
		+ "</td></tr>"
		for label, value in rows
	)
	signature = cstr(doc.signature).strip()
	signature_html = ""
	if re.match(r"^data:image/png;base64,[A-Za-z0-9+/=\s]+$", signature):
		signature_html = '<img class="sign" src="' + signature + '" alt="Signature">'
	return (
		'<section class="copy"><header><div class="country">Belize</div>'
		"<h1>TD4 Supplementary</h1>"
		"<p>Statement of Emoluments Paid for Income Tax Purposes</p>"
		'<p class="copy-label">' + escape_html(copy_label) + "</p></header>"
		'<p class="note">Commissions should be included in total emoluments and taxable emoluments.</p>'
		'<div class="parties"><div><h2>Employer Name and Address</h2><p>'
		+ _lines(doc.employer_name)
		+ "</p><p>"
		+ _lines(doc.employer_address)
		+ '</p></div><div><h2>Employee Name and Address</h2><p>'
		+ _lines(doc.employee_name)
		+ "</p><p>"
		+ _lines(doc.employee_address)
		+ "</p></div></div>"
		'<p class="year">Reporting year: '
		+ escape_html(cstr(doc.reporting_year))
		+ "</p><table>"
		+ body
		+ '</table><div class="signoff"><div><div class="label">Employee signature</div>'
		+ signature_html
		+ 		'</div><div><div class="label">Date signed</div><div class="date">'
		+ escape_html(cstr(doc.date_signed))
		+ '</div><div class="label">Completed by</div><div class="date">'
		+ escape_html(cstr(doc.filled_by_name or doc.filled_by))
		+ "</div></div></div></section>"
	)


def _lines(value) -> str:
	return "<br>".join(escape_html(line) for line in cstr(value).splitlines() if line.strip()) or "&nbsp;"


def _money(value) -> str:
	return f"{flt(value, 2):,.2f}"


@frappe.whitelist()
def get_td4(name: str) -> dict:
	if not name or not frappe.db.exists("TD4 Form", name):
		frappe.throw(_("TD4 form {0} was not found.").format(name or ""))
	doc = frappe.get_doc("TD4 Form", name)
	_assert_reader(doc)
	return public_dict(doc)


@frappe.whitelist()
def ensure_initial_td4() -> dict:
	employee = get_session_employee()
	if not employee:
		frappe.throw(_("No active agent is linked to your user."), frappe.PermissionError)
	pending = pending_name(employee)
	if pending:
		return _prompt_state(pending)
	if has_submitted(employee):
		return {"name": None, "dismiss_count": 0, "locked": False}
	doc = create_requested(employee, notify=False)
	return _prompt_state(doc.name)


@frappe.whitelist()
def request_td4(employee: str) -> dict:
	if not is_hr_user():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not employee or not frappe.db.exists("Employee", employee):
		frappe.throw(_("Agent {0} was not found.").format(employee or ""))
	pending = pending_name(employee)
	if pending:
		return {"name": pending, "created": False}
	doc = create_requested(employee, notify=True)
	return {"name": doc.name, "created": True}


@frappe.whitelist()
def submit_td4(name: str, values: str | dict | None = None) -> dict:
	if not name or not frappe.db.exists("TD4 Form", name):
		frappe.throw(_("TD4 form {0} was not found.").format(name or ""))
	doc = frappe.get_doc("TD4 Form", name)
	_assert_owner(doc)
	if doc.status != "Requested":
		frappe.throw(_("This TD4 has already been submitted."))
	payload = frappe.parse_json(values) if values else {}
	for fieldname in EDITABLE_FIELDS:
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))
	doc.status = "Submitted"
	doc.flags.ignore_permissions = True
	doc.save()
	doc.reload()
	return public_dict(doc)


def _prompt_state(name: str) -> dict:
	count = cint(frappe.db.get_value("TD4 Form", name, "dismiss_count"))
	return {"name": name, "dismiss_count": count, "locked": count >= DISMISS_LIMIT}


@frappe.whitelist()
def dismiss_td4_prompt(name: str) -> dict:
	if not name or not frappe.db.exists("TD4 Form", name):
		frappe.throw(_("TD4 form {0} was not found.").format(name or ""))
	doc = frappe.get_doc("TD4 Form", name)
	_assert_owner(doc)
	if doc.status != "Requested":
		return _prompt_state(doc.name)
	count = min(cint(doc.dismiss_count) + 1, DISMISS_LIMIT)
	doc.db_set("dismiss_count", count, update_modified=False)
	return _prompt_state(doc.name)


@frappe.whitelist()
def get_td4_roster() -> list[dict]:
	if not is_hr_user():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "employee_name", "department", "user_id"],
		order_by="employee_name asc",
		limit_page_length=0,
	)
	forms = frappe.get_all(
		"TD4 Form",
		fields=["name", "employee", "status", "filled_by", "filled_by_name", "filled_on", "date_signed", "modified"],
		order_by="modified desc",
		limit_page_length=0,
	)
	by_employee: dict[str, list] = {}
	for form in forms:
		by_employee.setdefault(form.employee, []).append(form)
	rows = []
	for employee in employees:
		choices = by_employee.get(employee.name) or []
		submitted = next((form for form in choices if form.status == "Submitted"), None)
		pending = next((form for form in choices if form.status == "Requested"), None)
		form = submitted or pending
		rows.append(
			{
				"employee": employee.name,
				"employee_name": employee.employee_name or employee.name,
				"department": employee.department or "",
				"filled": bool(submitted),
				"form": form.name if form else "",
				"filled_by": (submitted.filled_by if submitted else "") or "",
				"filled_by_name": (submitted.filled_by_name if submitted else "") or "",
				"filled_on": cstr(submitted.filled_on) if submitted and submitted.filled_on else "",
				"date_signed": cstr(submitted.date_signed) if submitted and submitted.date_signed else "",
			}
		)
	return rows


def get_permission_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	from hrms.hr.role_access import can_see

	if not can_see("see_td4_forms", user):
		return "1=0"
	if is_hr_user(user):
		return ""
	employee = get_session_employee(user)
	if not employee:
		return "1=0"
	return f"`tabTD4 Form`.employee = {frappe.db.escape(employee)}"


def has_permission(doc, ptype=None, user=None, debug=False) -> bool:
	user = user or frappe.session.user
	from hrms.hr.role_access import can_see

	if not can_see("see_td4_forms", user):
		return False
	if is_hr_user(user):
		if ptype == "write" and doc and not doc.is_new():
			current = frappe.db.get_value("TD4 Form", doc.name, "status")
			if current == "Submitted":
				return False
		return True
	employee = get_session_employee(user)
	if not employee or getattr(doc, "employee", None) != employee:
		return False
	if ptype in ("create", "delete"):
		return False
	if ptype == "write":
		current = frappe.db.get_value("TD4 Form", doc.name, "status") if doc.name else "Requested"
		return current == "Requested"
	return True
