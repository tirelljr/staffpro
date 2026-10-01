# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Employment letters laid out like the Staff Pro letterhead sample."""

from __future__ import annotations

import base64
import re
from functools import lru_cache
from html import escape
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime
from frappe.utils.file_manager import save_file

from hrms.hr.doctype.agent_document.agent_document import get_session_employee
from hrms.hr.doctype.document_category.document_category import seed_document_categories
from hrms.hr.doctype.hr_request.hr_request import is_hr_user

JOB_LETTER = "Job Letter"
OFFICE_PRINT = "Office Print"
JOB_LETTER_CATEGORY = "Job Letter"
PAY_PERIODS = 26
HOURS_PER_PAY_PERIOD = 80
GENERIC_SUBJECTS = {"", "job letter", "job letter request"}
OPEN_STATUSES = {"Open", "In Progress", "Waiting on Employee"}
CLOSED_STATUSES = {"Resolved", "Rejected", "Cancelled"}

LETTERHEAD_DEFAULTS = {
	"job_letter_company_name": "Staff Pro BPO, LLC",
	"job_letter_address": "33 George Price Highway\nSanta Elena, Cayo",
	"job_letter_email": "hr@staffprobpo.com",
	"job_letter_signatory": "Myra G Chavez",
	"job_letter_signatory_title": "Vice President",
	"job_letter_signatory_department": "Human Resources Department",
}

EMPLOYEE_FIELDS = (
	"employee_name",
	"first_name",
	"last_name",
	"gender",
	"marital_status",
	"designation",
	"employment_type",
	"date_of_joining",
	"company",
	"ctc",
)


def honorific_for(gender: str | None, marital_status: str | None = None) -> str:
	"""Mr. for men, Mrs. for married women, Ms. otherwise."""
	value = (gender or "").strip().lower()
	married = (marital_status or "").strip().lower() == "married"
	if value == "male":
		return "Mr."
	if value == "female":
		return "Mrs." if married else "Ms."
	return ""


def _money_blank(value) -> bool:
	return value in (None, "") or flt(value) == 0


def salary_amounts(hourly) -> tuple[float, float]:
	"""Biweekly pay is the hourly rate times 80 hours in the pay period.

	Monthly pay spreads those 26 pay periods over 12 months.
	Yearly pay is that monthly amount times 12.
	"""
	biweekly = flt(flt(hourly) * HOURS_PER_PAY_PERIOD, 2)
	monthly = flt(biweekly) * PAY_PERIODS / 12
	annual = flt(monthly * 12, 2)
	return annual, biweekly


def format_money(amount, *, cents: bool) -> str:
	value = flt(amount, 2)
	if cents or abs(value - round(value)) >= 0.005:
		return f"${value:,.2f}"
	return f"${value:,.0f}"


def employment_label(value: str | None) -> str:
	text = (value or "").replace("_", " ").replace("-", " ").strip()
	if not text:
		return ""
	lowered = text.lower()
	if "full" in lowered and "time" in lowered:
		return "Full-Time"
	if "part" in lowered and "time" in lowered:
		return "Part-Time"
	return text


def position_label(employment_type: str | None, designation: str | None) -> str:
	kind = employment_label(employment_type)
	role = (designation or "").strip()
	if kind and role:
		return f"{kind} {role}"
	return role or kind


def strip_re_prefix(subject: str | None) -> str:
	return re.sub(r"^\s*RE:\s*", "", subject or "", flags=re.IGNORECASE).strip()


def employment_subject(honorific: str | None, employee_name: str | None) -> str:
	who = " ".join(part for part in ((honorific or "").strip(), (employee_name or "").strip()) if part)
	return strip_re_prefix(f"Employment Verification for {who}".strip())


def pronouns_for(gender: str | None) -> tuple[str, str, str]:
	value = (gender or "").strip().lower()
	if value == "male":
		return "his", "he", "is"
	if value == "female":
		return "her", "she", "is"
	return "their", "they", "are"


_MONTHS = (
	"January",
	"February",
	"March",
	"April",
	"May",
	"June",
	"July",
	"August",
	"September",
	"October",
	"November",
	"December",
)


def long_date(value) -> str:
	if not value:
		return ""
	day = getdate(value)
	return f"{_MONTHS[day.month - 1]} {day.day}, {day.year}"


def last_name_of(employee_name: str | None, last_name: str | None = None) -> str:
	if (last_name or "").strip():
		return last_name.strip()
	parts = (employee_name or "").split()
	return parts[-1] if parts else ""


def short_name(honorific: str | None, employee_name: str | None, last_name: str | None = None) -> str:
	family = last_name_of(employee_name, last_name)
	title = (honorific or "").strip()
	if title and family:
		return f"{title} {family}"
	return family or (employee_name or "").strip()


def letterhead_settings() -> dict:
	settings = dict(LETTERHEAD_DEFAULTS)
	if not frappe.db.exists("DocType", "HR Settings"):
		return settings
	meta = frappe.get_meta("HR Settings")
	for fieldname, default in LETTERHEAD_DEFAULTS.items():
		if not meta.has_field(fieldname):
			continue
		current = frappe.db.get_single_value("HR Settings", fieldname)
		if current not in (None, ""):
			settings[fieldname] = current
	return settings


def ensure_letterhead_defaults() -> None:
	sync_print_format()
	if not frappe.db.exists("DocType", "HR Settings"):
		return
	meta = frappe.get_meta("HR Settings")
	for fieldname, value in LETTERHEAD_DEFAULTS.items():
		if not meta.has_field(fieldname):
			continue
		if frappe.db.get_single_value("HR Settings", fieldname) in (None, ""):
			frappe.db.set_single_value("HR Settings", fieldname, value, update_modified=False)


def fill_letterhead_on_settings(doc) -> None:
	meta = doc.meta if getattr(doc, "meta", None) else None
	for fieldname, value in LETTERHEAD_DEFAULTS.items():
		if meta is not None and not meta.has_field(fieldname):
			continue
		if not doc.get(fieldname):
			doc.set(fieldname, value)


def employee_snapshot(employee: str) -> dict:
	if not employee or not frappe.db.exists("Employee", employee):
		return {}
	meta = frappe.get_meta("Employee")
	fields = [field for field in EMPLOYEE_FIELDS if meta.has_field(field)]
	row = frappe.db.get_value("Employee", employee, fields, as_dict=True) or {}
	return row


def close_sentence(text: str) -> str:
	text = (text or "").rstrip()
	if not text or text.endswith((".", "!", "?")):
		return text
	return f"{text}."


def default_paragraphs(ctx: dict) -> str:
	position = ctx.get("position") or "employee"
	article = "an" if position[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
	joining = ctx.get("joining")
	joined = f" {ctx['short_name']} has been employed with the company since {joining}." if joining else ""
	annual = ctx.get("annual_display") or format_money(0, cents=False)
	biweekly = ctx.get("biweekly_display") or format_money(0, cents=True)
	email = ctx.get("email") or "hr@staffprobpo.com"
	company = ctx.get("company") or ctx.get("letterhead_company") or "the company"
	return (
		f"This letter is to confirm that {ctx['full_title']} is currently employed with {company} "
		f"as {article} {position}.{joined}\n\n"
		f"{ctx['short_name']} currently earns an annual salary of {annual}, paid on a biweekly basis "
		f"over {PAY_PERIODS} pay periods, equivalent to {biweekly} per pay period.\n\n"
		f"We are pleased with {ctx['possessive']} contributions to the company and can confirm that "
		f"{ctx['subject_pronoun']} {ctx['verb']} an employee in good standing with {close_sentence(company)}\n\n"
		f"Should you require any additional information regarding {ctx['short_name']}'s employment, "
		f"please do not hesitate to contact our Human Resources Department at {email}."
	)


def build_context(source: dict, snapshot: dict | None = None, paragraphs: str | None = None) -> dict:
	snapshot = snapshot or {}
	gender = source.get("gender") or snapshot.get("gender")
	marital = source.get("marital_status") or snapshot.get("marital_status")
	honorific = (source.get("honorific") or "").strip() or honorific_for(gender, marital)
	employee_name = (source.get("employee_name") or snapshot.get("employee_name") or "").strip()
	family = last_name_of(employee_name, source.get("last_name") or snapshot.get("last_name"))
	annual = source.get("annual_salary")
	biweekly = source.get("biweekly_salary")
	if _money_blank(annual):
		annual, biweekly = salary_amounts(snapshot.get("ctc"))
	elif _money_blank(biweekly):
		biweekly = flt(flt(annual) / PAY_PERIODS, 2)
	head = letterhead_settings()
	company = (source.get("company") or snapshot.get("company") or head["job_letter_company_name"]).strip()
	possessive, subject_pronoun, verb = pronouns_for(gender)
	full_title = " ".join(part for part in (honorific, employee_name) if part).strip() or employee_name
	ctx = {
		"honorific": honorific,
		"employee_name": employee_name,
		"full_title": full_title,
		"short_name": short_name(honorific, employee_name, family),
		"company": company,
		"position": position_label(
			source.get("employment_type") or snapshot.get("employment_type"),
			source.get("designation") or snapshot.get("designation"),
		)
		or "employee",
		"joining": long_date(source.get("date_of_joining") or snapshot.get("date_of_joining")),
		"annual_display": format_money(annual, cents=False),
		"biweekly_display": format_money(biweekly, cents=True),
		"annual_salary": flt(annual, 2),
		"biweekly_salary": flt(biweekly, 2),
		"possessive": possessive,
		"subject_pronoun": subject_pronoun,
		"verb": verb,
		"addressed_to": (source.get("addressed_to") or "").strip(),
		"recipient_address": (source.get("recipient_address") or "").strip(),
		"letterhead_company": head["job_letter_company_name"],
		"letterhead_address": head["job_letter_address"],
		"email": head["job_letter_email"],
		"signatory": head["job_letter_signatory"],
		"signatory_title": head["job_letter_signatory_title"],
		"signatory_department": head["job_letter_signatory_department"],
		"letter_date": long_date(source.get("resolved_on") or source.get("creation") or getdate()),
		"gender": gender,
		"marital_status": marital,
	}
	ctx["subject"] = strip_re_prefix(source.get("subject") or "") or employment_subject(honorific, employee_name)
	if _is_generic_subject(ctx["subject"]):
		ctx["subject"] = employment_subject(honorific, employee_name)
	ctx["subject"] = strip_re_prefix(ctx["subject"])
	ctx["paragraphs"] = (paragraphs if paragraphs is not None else source.get("letter_paragraphs") or "").strip()
	if not ctx["paragraphs"]:
		ctx["paragraphs"] = default_paragraphs(ctx)
	return ctx


_ASSET_DIR = Path(__file__).parent / "job_letter_assets"
_ASSET_MIME = {
	"header.jpg": "image/jpeg",
	"footer.jpg": "image/jpeg",
	"logo.jpg": "image/jpeg",
	"signature.png": "image/png",
}


@lru_cache(maxsize=8)
def _asset_uri(filename: str) -> str:
	raw = (_ASSET_DIR / filename).read_bytes()
	encoded = base64.b64encode(raw).decode()
	return f"data:{_ASSET_MIME[filename]};base64,{encoded}"


def _letter_images() -> dict:
	return {name: _asset_uri(name) for name in _ASSET_MIME}


def rich_paragraphs(ctx: dict) -> str:
	"""Body copy with the same bold phrases as the Staff Pro sample."""
	position = ctx.get("position") or "employee"
	article = "an" if position[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
	joining = ctx.get("joining")
	joined = ""
	if joining:
		joined = (
			f" {escape(ctx['short_name'])} has been employed with the company since "
			f"<strong>{escape(joining)}</strong>."
		)
	annual = escape(ctx.get("annual_display") or format_money(0, cents=False))
	biweekly = escape(ctx.get("biweekly_display") or format_money(0, cents=True))
	email = escape(ctx.get("email") or "hr@staffprobpo.com")
	company_name = ctx.get("company") or ctx.get("letterhead_company") or "the company"
	company = escape(company_name)
	return (
		f"<p>This letter is to confirm that <strong>{escape(ctx['full_title'])}</strong> "
		f"is currently employed with <strong>{company}</strong> as {article} "
		f"<strong>{escape(position)}</strong>.{joined}</p>"
		f"<p>{escape(ctx['short_name'])} currently earns an annual salary of {annual}, paid on a biweekly basis "
		f"over {PAY_PERIODS} pay periods, equivalent to {biweekly} per pay period.</p>"
		f"<p>We are pleased with {escape(ctx['possessive'])} contributions to the company and can confirm that "
		f"{escape(ctx['subject_pronoun'])} {escape(ctx['verb'])} an employee in good standing with {escape(close_sentence(company_name))}</p>"
		f"<p>Should you require any additional information regarding {escape(ctx['short_name'])}\u2019s employment, "
		f"please do not hesitate to contact our Human Resources Department at <strong>{email}</strong>.</p>"
	)


def _body_html(ctx: dict) -> str:
	plain = (ctx.get("paragraphs") or "").strip()
	if plain == default_paragraphs(ctx).strip():
		return rich_paragraphs(ctx)
	return "".join(f"<p>{escape(part.strip())}</p>" for part in plain.split("\n\n") if part.strip())


def _signature_lines(ctx: dict) -> str:
	company = (ctx.get("company") or "").strip()
	letterhead = (ctx.get("letterhead_company") or "").strip()
	lines = [
		ctx.get("signatory") or "",
		ctx.get("signatory_title") or "",
		ctx.get("signatory_department") or "",
		company,
	]
	if letterhead and letterhead.casefold() != company.casefold():
		lines.append(letterhead)
	return "".join(f"<div>{escape(line)}</div>" for line in lines if line)


def render_html(ctx: dict) -> str:
	"""Full letter on the Staff Pro letterhead, matching the sample PDF."""
	images = _letter_images()
	address_lines = "".join(
		f"<div>{escape(line)}</div>" for line in (ctx.get("letterhead_address") or "").splitlines() if line.strip()
	)
	recipient = ""
	if ctx.get("addressed_to"):
		recipient += f"<div>{escape(ctx['addressed_to'])}</div>"
	for line in (ctx.get("recipient_address") or "").splitlines():
		if line.strip():
			recipient += f"<div>{escape(line.strip())}</div>"
	subject_line = strip_re_prefix(ctx.get("subject") or "")
	return f"""<style>
.sp-letter {{
	position: relative;
	width: 100%;
	max-width: 8.5in;
	min-height: 11in;
	margin: 0 auto;
	background: #fff;
	color: #0d0d0d;
	font-family: "Segoe UI", "Liberation Sans", Arial, sans-serif;
	font-size: 12pt;
	line-height: 1.35;
	box-sizing: border-box;
}}
.sp-letter__banner {{ display: block; width: 100%; height: auto; }}
.sp-letter__body {{ position: relative; padding: 0.62in 0.6in 1.2in; }}
.sp-letter__logo {{ position: absolute; top: 0.62in; right: 0.28in; width: 1.15in; height: auto; }}
.sp-letter__addr {{
	color: #607e4c;
	font-family: "Microsoft Sans Serif", "Segoe UI", "Liberation Sans", sans-serif;
	font-size: 12pt;
	line-height: 1.22;
	max-width: 4.4in;
}}
.sp-letter__date {{ font-weight: 700; margin-top: 0.36in; }}
.sp-letter__to {{ font-weight: 700; margin-top: 0.26in; line-height: 1.32; }}
.sp-letter__subject {{ font-weight: 700; margin: 0.26in 0 0.2in; }}
.sp-letter p {{ margin: 0 0 0.14in; }}
.sp-letter__sign {{
	margin-top: 0.2in;
	font-family: Arial, "Liberation Sans", sans-serif;
	line-height: 1.15;
}}
.sp-letter__sign img {{ display: block; width: 1.22in; height: 0.39in; margin: 0.06in 0 0.04in; }}
.sp-letter__foot {{ position: absolute; left: 0; right: 0; bottom: 0; width: 100%; height: auto; }}
</style>
<article class="sp-letter">
	<img class="sp-letter__banner" src="{images['header.jpg']}" alt="">
	<div class="sp-letter__body">
		<img class="sp-letter__logo" src="{images['logo.jpg']}" alt="Staff Pro BPO">
		<div class="sp-letter__addr">
			<div>{escape(ctx.get("letterhead_company") or "")}</div>
			{address_lines}
			<div>{escape(ctx.get("email") or "")}</div>
		</div>
		<div class="sp-letter__date">{escape(ctx.get("letter_date") or "")}</div>
		<div class="sp-letter__to">{recipient}</div>
		<div class="sp-letter__subject">{escape(subject_line)}</div>
		<p>Dear Sir/Madam,</p>
		{_body_html(ctx)}
		<div class="sp-letter__sign">
			<div>Sincerely,</div>
			<img src="{images['signature.png']}" alt="">
			{_signature_lines(ctx)}
		</div>
	</div>
	<img class="sp-letter__foot" src="{images['footer.jpg']}" alt="">
</article>"""


def _is_generic_subject(subject: str | None) -> bool:
	return strip_re_prefix(subject).lower() in GENERIC_SUBJECTS


def _can_edit_letter(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return is_hr_user(user)


def prepare_request(doc) -> None:
	"""Fill a new or open job letter. Approved letters stay as they were saved."""
	if doc.request_type != JOB_LETTER or not doc.employee:
		if doc.subject:
			doc.subject = strip_re_prefix(doc.subject)
		return

	previous = doc.get_doc_before_save()
	if (
		previous
		and previous.status in CLOSED_STATUSES
		and doc.status in CLOSED_STATUSES
	):
		doc.subject = strip_re_prefix(doc.subject)
		return
	if not _can_edit_letter() and not doc.is_new():
		return

	snapshot = employee_snapshot(doc.employee)
	if not doc.employee_name:
		doc.employee_name = snapshot.get("employee_name")
	if not doc.company:
		doc.company = snapshot.get("company")
	if not doc.designation:
		doc.designation = snapshot.get("designation")
	if not doc.date_of_joining:
		doc.date_of_joining = snapshot.get("date_of_joining")
	if not doc.honorific:
		doc.honorific = honorific_for(snapshot.get("gender"), snapshot.get("marital_status"))
	# Agents cannot type a salary. Staff can keep a value they entered.
	if not _can_edit_letter() or _money_blank(doc.annual_salary):
		annual, biweekly = salary_amounts(snapshot.get("ctc"))
		doc.annual_salary = annual
		doc.biweekly_salary = biweekly
	elif _money_blank(doc.biweekly_salary):
		doc.biweekly_salary = flt(flt(doc.annual_salary) / PAY_PERIODS, 2)

	source = doc.as_dict()
	source["gender"] = snapshot.get("gender")
	source["marital_status"] = snapshot.get("marital_status")
	source["employment_type"] = snapshot.get("employment_type")
	source["last_name"] = snapshot.get("last_name")
	paragraphs = doc.letter_paragraphs if cint(doc.letter_custom) else ""
	ctx = build_context(source, snapshot, paragraphs=paragraphs)
	doc.honorific = ctx["honorific"]
	doc.annual_salary = ctx["annual_salary"]
	doc.biweekly_salary = ctx["biweekly_salary"]
	doc.subject = ctx["subject"]
	if not doc.letter_custom:
		doc.letter_paragraphs = ctx["paragraphs"]
	doc.letter_html = render_html(ctx)
	if not (doc.description or "").strip():
		who = doc.addressed_to or _("the recipient")
		doc.description = _("Employment verification addressed to {0}.").format(who)
	if not doc.letter_purpose:
		doc.letter_purpose = doc.addressed_to


def _assert_open_letter(doc) -> None:
	if doc.request_type != JOB_LETTER:
		frappe.throw(_("This request is not a job letter."))
	if doc.status not in OPEN_STATUSES:
		frappe.throw(_("This job letter can no longer be edited."))


def display_letter_html(doc) -> str:
	"""Letterhead page for preview and print, including letters saved before the layout change."""
	if getattr(doc, "request_type", None) == OFFICE_PRINT and "sp-letter" in (doc.letter_html or ""):
		return doc.letter_html
	if getattr(doc, "request_type", None) not in {JOB_LETTER, OFFICE_PRINT} or not doc.employee:
		return doc.letter_html or ""
	paragraphs = doc.letter_paragraphs if cint(doc.letter_custom) else None
	return render_html(_context_for_saved(doc, paragraphs=paragraphs))


def _context_for_saved(doc, paragraphs: str | None = None) -> dict:
	snapshot = employee_snapshot(doc.employee)
	source = doc.as_dict()
	source["gender"] = snapshot.get("gender")
	source["marital_status"] = snapshot.get("marital_status")
	source["employment_type"] = snapshot.get("employment_type")
	source["last_name"] = snapshot.get("last_name")
	return build_context(source, snapshot, paragraphs=paragraphs)


@frappe.whitelist()
def preview_job_letter(
	addressed_to: str = "",
	recipient_address: str = "",
	employee: str | None = None,
	honorific: str = "",
	annual_salary: str | float | None = None,
	biweekly_salary: str | float | None = None,
	letter_paragraphs: str = "",
) -> dict:
	if not _can_edit_letter():
		employee = get_session_employee()
	elif not employee:
		employee = get_session_employee()
	if not employee:
		frappe.throw(_("No active agent is linked to your user."), frappe.PermissionError)
	snapshot = employee_snapshot(employee)
	if not _can_edit_letter():
		annual_salary = None
		biweekly_salary = None
	source = {
		"employee_name": snapshot.get("employee_name"),
		"company": snapshot.get("company"),
		"designation": snapshot.get("designation"),
		"date_of_joining": snapshot.get("date_of_joining"),
		"addressed_to": addressed_to,
		"recipient_address": recipient_address,
		"honorific": honorific,
		"annual_salary": annual_salary or None,
		"biweekly_salary": biweekly_salary or None,
		"gender": snapshot.get("gender"),
		"marital_status": snapshot.get("marital_status"),
		"employment_type": snapshot.get("employment_type"),
		"last_name": snapshot.get("last_name"),
	}
	ctx = build_context(source, snapshot, paragraphs=letter_paragraphs or None)
	return {
		"html": render_html(ctx),
		"subject": ctx["subject"],
		"honorific": ctx["honorific"],
		"annual_salary": ctx["annual_salary"],
		"biweekly_salary": ctx["biweekly_salary"],
		"paragraphs": ctx["paragraphs"],
	}


@frappe.whitelist()
def salary_for_employee(employee: str | None = None) -> dict:
	"""Yearly and biweekly pay from the agent's hourly rate."""
	if not _can_edit_letter():
		employee = get_session_employee()
	elif not employee:
		employee = get_session_employee()
	if not employee:
		frappe.throw(_("No active agent is linked to your user."), frappe.PermissionError)
	snapshot = employee_snapshot(employee)
	annual, biweekly = salary_amounts(snapshot.get("ctc"))
	return {
		"hourly_rate": flt(snapshot.get("ctc"), 2),
		"annual_salary": annual,
		"biweekly_salary": biweekly,
	}


def reject_agent_job_letter_attachment(doc, method=None) -> None:
	"""Agents cannot attach files when they request a job letter."""
	if getattr(doc, "attached_to_doctype", None) != "HR Request" or not getattr(doc, "attached_to_name", None):
		return
	if frappe.session.user == "Administrator" or is_hr_user():
		return
	request_type = frappe.db.get_value("HR Request", doc.attached_to_name, "request_type")
	if request_type == JOB_LETTER:
		frappe.throw(_("You cannot add attachments to a job letter request."))


@frappe.whitelist()
def submit_job_letter(addressed_to: str, recipient_address: str = "") -> dict:
	addressed_to = (addressed_to or "").strip()
	if not addressed_to:
		frappe.throw(_("Enter who the letter is addressed to."))
	employee = get_session_employee()
	if not employee and not _can_edit_letter():
		frappe.throw(_("No active agent is linked to your user."), frappe.PermissionError)
	if not employee:
		frappe.throw(_("Choose an agent before creating a job letter."))
	doc = frappe.new_doc("HR Request")
	doc.employee = employee
	doc.request_type = JOB_LETTER
	doc.addressed_to = addressed_to
	doc.recipient_address = (recipient_address or "").strip()
	doc.status = "Open"
	doc.priority = "Medium"
	doc.insert(ignore_permissions=True)
	return _public_letter(doc)


@frappe.whitelist()
def get_request_kind(name: str) -> dict:
	doc = frappe.get_doc("HR Request", name)
	doc.check_permission("read")
	return {"name": doc.name, "request_type": doc.request_type, "status": doc.status}


@frappe.whitelist()
def get_job_letter(name: str) -> dict:
	doc = frappe.get_doc("HR Request", name)
	doc.check_permission("read")
	if doc.request_type not in {JOB_LETTER, OFFICE_PRINT}:
		frappe.throw(_("This request is not a job letter."))
	return _public_letter(doc)


@frappe.whitelist()
def get_letter_preview(name: str) -> dict:
	"""Letterhead HTML for the desk preview and the agent preview."""
	doc = frappe.get_doc("HR Request", name)
	doc.check_permission("read")
	if doc.request_type not in {JOB_LETTER, OFFICE_PRINT}:
		frappe.throw(_("This request is not a job letter."))
	return {"name": doc.name, "html": display_letter_html(doc)}


@frappe.whitelist()
def download_letter_pdf(name: str):
	"""Open the letter as the Staff Pro letterhead PDF."""
	doc = frappe.get_doc("HR Request", name)
	doc.check_permission("read")
	if doc.request_type not in {JOB_LETTER, OFFICE_PRINT}:
		frappe.throw(_("This request is not a job letter."))
	from frappe.utils.pdf import get_pdf

	frappe.local.response.filename = _pdf_filename(doc)
	frappe.local.response.filecontent = get_pdf(
		_pdf_document(display_letter_html(doc)),
		{
			"page-size": "Letter",
			"margin-top": "0mm",
			"margin-right": "0mm",
			"margin-bottom": "0mm",
			"margin-left": "0mm",
		},
	)
	frappe.local.response.type = "pdf"


def _public_letter(doc) -> dict:
	file_url = ""
	if doc.get("letter_document"):
		file_url = frappe.db.get_value("Agent Document", doc.letter_document, "file") or ""
	return {
		"name": doc.name,
		"employee": doc.employee,
		"employee_name": doc.employee_name,
		"request_type": doc.request_type,
		"status": doc.status,
		"subject": doc.subject,
		"addressed_to": doc.addressed_to,
		"recipient_address": doc.recipient_address,
		"honorific": doc.honorific,
		"annual_salary": doc.annual_salary,
		"biweekly_salary": doc.biweekly_salary,
		"letter_html": display_letter_html(doc),
		"letter_paragraphs": doc.letter_paragraphs,
		"letter_document": doc.get("letter_document"),
		"file_url": file_url,
		"source_request": doc.get("source_request"),
		"resolved_on": doc.resolved_on,
	}


@frappe.whitelist()
def update_job_letter(
	name: str,
	addressed_to: str | None = None,
	recipient_address: str | None = None,
	honorific: str | None = None,
	annual_salary: str | float | None = None,
	biweekly_salary: str | float | None = None,
	letter_paragraphs: str | None = None,
	rebuild: int | str = 0,
) -> dict:
	if not _can_edit_letter():
		frappe.throw(_("Only staff can edit a job letter."), frappe.PermissionError)
	doc = frappe.get_doc("HR Request", name)
	doc.check_permission("write")
	_assert_open_letter(doc)
	if addressed_to is not None:
		doc.addressed_to = addressed_to.strip()
	if recipient_address is not None:
		doc.recipient_address = recipient_address.strip()
	if honorific is not None:
		doc.honorific = honorific.strip()
	if annual_salary not in (None, ""):
		doc.annual_salary = flt(annual_salary, 2)
	if biweekly_salary not in (None, ""):
		doc.biweekly_salary = flt(biweekly_salary, 2)
	previous_text = (doc.letter_paragraphs or "").strip()
	was_custom = cint(doc.letter_custom)
	generated = default_paragraphs(_context_for_saved(doc, paragraphs="")).strip()
	submitted = None if letter_paragraphs is None else letter_paragraphs.strip()
	if cint(rebuild) or submitted is None or (submitted == previous_text and not was_custom):
		doc.letter_paragraphs = generated
		doc.letter_custom = 0
	elif submitted == generated:
		doc.letter_paragraphs = generated
		doc.letter_custom = 0
	else:
		doc.letter_paragraphs = submitted
		doc.letter_custom = 1
	ctx = _context_for_saved(doc, paragraphs=doc.letter_paragraphs or "")
	doc.subject = ctx["subject"]
	doc.letter_html = render_html(ctx)
	doc.save()
	return _public_letter(doc)


@frappe.whitelist()
def review_job_letter(name: str, action: str, comment: str = "") -> dict:
	if not _can_edit_letter():
		frappe.throw(_("Only staff can review this request."), frappe.PermissionError)
	doc = frappe.get_doc("HR Request", name)
	doc.check_permission("write")
	if doc.request_type not in {JOB_LETTER, OFFICE_PRINT}:
		frappe.throw(_("This request cannot be reviewed here."))
	decision = (action or "").strip().lower()
	if decision not in {"approve", "reject"}:
		frappe.throw(_("Action must be Approve or Reject."))
	if doc.status not in OPEN_STATUSES:
		frappe.throw(_("This request is already {0}.").format(doc.status))
	doc.status = "Resolved" if decision == "approve" else "Rejected"
	doc.resolution = (comment or "").strip() or (
		_("Job letter approved.") if decision == "approve" and doc.request_type == JOB_LETTER else _("Request {0}.").format(doc.status.lower())
	)
	if not doc.assigned_to:
		doc.assigned_to = frappe.session.user
	doc.save()
	return _public_letter(doc)


def file_approved_letter(doc) -> str | None:
	"""Store the approved letter PDF in the agent's Job Letter folder."""
	if doc.request_type != JOB_LETTER or doc.status != "Resolved":
		return None
	if doc.get("letter_document") and frappe.db.exists("Agent Document", doc.letter_document):
		return doc.letter_document
	if not doc.letter_html or not doc.employee:
		return None
	agent_doc = None
	try:
		seed_document_categories()
		pdf = _pdf_bytes(doc)
		filename = _pdf_filename(doc)
		agent_doc = frappe.get_doc(
			{
				"doctype": "Agent Document",
				"employee": doc.employee,
				"category": JOB_LETTER_CATEGORY,
				"file_name": filename,
				"notes": _("Approved job letter {0}").format(doc.name),
				"hr_request": doc.name,
				"uploaded_by": frappe.session.user,
				"uploaded_on": now_datetime(),
			}
		)
		agent_doc.flags.ignore_permissions = True
		agent_doc.flags.ignore_mandatory = True
		agent_doc.insert(ignore_permissions=True)
		from hrms.hr.agent_filesystem import ensure_category_folder

		folder = ensure_category_folder(doc.employee, JOB_LETTER_CATEGORY)
		save_file(filename, pdf, "Agent Document", agent_doc.name, folder=folder, is_private=1, df="file")
		agent_doc.reload()
		frappe.db.set_value("HR Request", doc.name, "letter_document", agent_doc.name, update_modified=False)
		doc.letter_document = agent_doc.name
		return agent_doc.name
	except Exception:
		if agent_doc and agent_doc.name and not agent_doc.get("file"):
			frappe.delete_doc("Agent Document", agent_doc.name, ignore_permissions=True, force=True)
		frappe.log_error(title="Job letter PDF", message=frappe.get_traceback())
		return None


def sync_print_format() -> None:
	"""Keep the Job Letter print format on the letterhead page margins."""
	path = Path(__file__).parent / "print_format" / "job_letter" / "job_letter.html"
	if not path.exists() or not frappe.db.exists("Print Format", "Job Letter"):
		return
	html = path.read_text(encoding="utf-8")
	current = frappe.db.get_value("Print Format", "Job Letter", "html") or ""
	if current.strip() == html.strip():
		return
	frappe.db.set_value("Print Format", "Job Letter", "html", html, update_modified=False)
	frappe.clear_cache(doctype="Print Format")


def _pdf_document(letter_html: str) -> str:
	"""A self-contained page. wkhtmltopdf cannot load this site's asset host."""
	return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
.print-format {{
	margin-top: 0mm;
	margin-right: 0mm;
	margin-bottom: 0mm;
	margin-left: 0mm;
	page-size: Letter;
	padding: 0;
}}
html, body {{ margin: 0; padding: 0; background: #fff; }}
.sp-letter {{
	min-height: 0 !important;
	height: 10.92in !important;
	max-height: 10.92in !important;
	overflow: hidden !important;
}}
</style>
</head>
<body><div class="print-format">{letter_html or ""}</div></body>
</html>"""


def _pdf_bytes(doc) -> bytes:
	from frappe.utils.pdf import get_pdf

	return get_pdf(
		_pdf_document(display_letter_html(doc)),
		{
			"page-size": "Letter",
			"margin-top": "0mm",
			"margin-right": "0mm",
			"margin-bottom": "0mm",
			"margin-left": "0mm",
		},
	)


def _pdf_filename(doc) -> str:
	who = frappe.scrub(doc.employee_name or doc.employee or "agent").replace("_", " ").title()
	return f"Employment Verification - {who}.pdf"


@frappe.whitelist()
def request_office_print(name: str) -> dict:
	source = frappe.get_doc("HR Request", name)
	source.check_permission("read")
	if source.request_type != JOB_LETTER or source.status != "Resolved":
		frappe.throw(_("Only an approved job letter can be sent for office printing."))
	if not _can_edit_letter() and get_session_employee() != source.employee:
		frappe.throw(_("You can only request a print of your own letter."), frappe.PermissionError)
	existing = frappe.db.get_value(
		"HR Request",
		{
			"request_type": OFFICE_PRINT,
			"source_request": source.name,
			"status": ["not in", list(CLOSED_STATUSES)],
			"employee": source.employee,
		},
		"name",
	)
	if existing:
		return get_job_letter(existing)
	doc = frappe.new_doc("HR Request")
	doc.employee = source.employee
	doc.company = source.company
	doc.request_type = OFFICE_PRINT
	doc.source_request = source.name
	doc.subject = strip_re_prefix(f"Office print: {source.subject}")
	doc.description = _("Please print the approved job letter {0}.").format(source.name)
	doc.addressed_to = source.addressed_to
	doc.recipient_address = source.recipient_address
	doc.letter_html = source.letter_html
	doc.letter_paragraphs = source.letter_paragraphs
	doc.honorific = source.honorific
	doc.annual_salary = source.annual_salary
	doc.biweekly_salary = source.biweekly_salary
	doc.status = "Open"
	doc.priority = "Medium"
	doc.insert(ignore_permissions=True)
	return _public_letter(doc)
