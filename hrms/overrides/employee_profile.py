# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Employee profile password + lifetime payroll/billing stats for the form sidebar."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

VIEWABLE_PASSWORD_FIELD = "hrms_login_password"
PASSWORD_ROLES = {"System Manager", "HR Manager", "HR User", "Administrator"}


def remember_viewable_password(user: str, password: str) -> None:
	"""Keep an encrypted copy so HR can show the password set for this login."""
	login = (user or "").strip()
	secret = (password or "").strip()
	if not login or login in {"Guest", "Administrator"} or not secret:
		return
	from frappe.utils.password import set_encrypted_password

	set_encrypted_password("User", login, secret, fieldname=VIEWABLE_PASSWORD_FIELD)


def read_viewable_password(user: str) -> str:
	login = (user or "").strip()
	if not login:
		return ""
	from frappe.utils.password import get_decrypted_password

	try:
		return get_decrypted_password(
			"User", login, VIEWABLE_PASSWORD_FIELD, raise_exception=False
		) or ""
	except Exception:
		return ""


def _can_manage_passwords() -> bool:
	return bool(set(frappe.get_roles()).intersection(PASSWORD_ROLES))


@frappe.whitelist()
def get_employee_user_password(employee: str) -> dict:
	"""Return the saved login password for HR. Empty until a password is set or the agent signs in."""
	frappe.has_permission("Employee", "read", employee, throw=True)
	if not _can_manage_passwords():
		frappe.throw(_("Not permitted to view this password."), frappe.PermissionError)
	user = (frappe.db.get_value("Employee", employee, "user_id") or "").strip()
	if not user:
		return {"password": "", "user": ""}
	return {"password": read_viewable_password(user), "user": user}


@frappe.whitelist()
def update_employee_user_password(employee: str, new_password: str, logout_all_sessions: int = 0) -> dict:
	"""Set or change the linked HRMS User password for an Employee."""
	frappe.has_permission("Employee", "write", employee, throw=True)
	emp = frappe.get_doc("Employee", employee)
	user = (emp.user_id or "").strip()
	if not user:
		frappe.throw(_("Link a Username on this employee before setting a password."))

	password = (new_password or "").strip()
	if len(password) < 8:
		frappe.throw(_("Password must be at least 8 characters."))

	if not frappe.db.exists("User", user):
		frappe.throw(_("User {0} does not exist.").format(frappe.bold(user)))

	# HR/System Manager, or the employee changing their own login.
	roles = set(frappe.get_roles())
	is_self = frappe.session.user == user
	from hrms.hr.staff_pro_roles import STAFF_PRO_HR_DESK_ROLES

	is_hr = bool(roles.intersection(STAFF_PRO_HR_DESK_ROLES))
	if not (is_self or is_hr):
		frappe.throw(_("Not permitted to change this password."), frappe.PermissionError)

	from frappe.utils.password import update_password

	update_password(user, password, logout_all_sessions=cint(logout_all_sessions))
	remember_viewable_password(user, password)
	return {"ok": True, "user": user}


MAX_PROFILE_IMAGE_BYTES = 10 * 1024 * 1024
PROFILE_IMAGE_EDGE = 1024


@frappe.whitelist()
def update_my_profile_image(filename: str, content: str) -> dict:
	"""Save the signed-in agent's profile photo on their Employee and User records."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not (filename or "").strip() or not (content or "").strip():
		frappe.throw(_("A photo is required."))

	employee = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		"name",
	)
	if not employee:
		frappe.throw(_("No active agent is linked to your user."), frappe.PermissionError)
	if not frappe.get_meta("Employee").has_field("image"):
		frappe.throw(_("Profile photos are not available on this site."))

	safe_name, file_bytes = _prepare_profile_image(content)
	previous_employee = frappe.db.get_value("Employee", employee, "image")
	previous_user = frappe.db.get_value("User", user, "user_image")

	from frappe.utils.file_manager import save_file

	file_doc = save_file(
		safe_name,
		file_bytes,
		"Employee",
		employee,
		folder="Home",
		is_private=0,
		df="image",
	)
	file_url = file_doc.file_url
	if not file_url:
		frappe.throw(_("The photo could not be saved."))

	frappe.db.set_value("Employee", employee, "image", file_url)
	frappe.db.set_value("User", user, "user_image", file_url)
	_drop_replaced_image(previous_employee, file_url, employee, user)
	if previous_user != previous_employee:
		_drop_replaced_image(previous_user, file_url, employee, user)

	return {"image": file_url, "user_image": file_url, "employee": employee}


def _prepare_profile_image(content: str) -> tuple[str, bytes]:
	import base64
	import io

	from PIL import Image, ImageOps

	raw_content = (content or "").strip()
	if raw_content.startswith("data:") and "," in raw_content:
		raw_content = raw_content.split(",", 1)[1]
	try:
		decoded = base64.b64decode(raw_content, validate=False)
	except Exception:
		frappe.throw(_("The photo could not be read."))
	if not decoded:
		frappe.throw(_("A photo is required."))
	if len(decoded) > MAX_PROFILE_IMAGE_BYTES:
		frappe.throw(_("Photo must be 10 MB or smaller."))

	try:
		with Image.open(io.BytesIO(decoded)) as image:
			image.seek(0)
			image = ImageOps.exif_transpose(image)
			image.load()
			resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
			image.thumbnail((PROFILE_IMAGE_EDGE, PROFILE_IMAGE_EDGE), resample)
			has_alpha = image.mode in ("RGBA", "LA") or (
				image.mode == "P" and "transparency" in image.info
			)
			if has_alpha:
				image = image.convert("RGBA")
				buffer = io.BytesIO()
				image.save(buffer, format="PNG", optimize=True)
				return "profile.png", buffer.getvalue()
			image = image.convert("RGB")
			buffer = io.BytesIO()
			image.save(buffer, format="JPEG", quality=85, optimize=True)
			return "profile.jpg", buffer.getvalue()
	except Exception:
		frappe.throw(_("Upload a JPG, PNG, WEBP, or GIF photo."))


def _drop_replaced_image(old_url: str | None, new_url: str, employee: str, user: str) -> None:
	if not old_url or old_url == new_url:
		return
	if not (old_url.startswith("/files/") or old_url.startswith("/private/files/")):
		return
	for name in frappe.get_all("File", filters={"file_url": old_url}, pluck="name"):
		attached_to_doctype, attached_to_name = frappe.db.get_value(
			"File", name, ["attached_to_doctype", "attached_to_name"]
		)
		owned = (attached_to_doctype == "Employee" and attached_to_name == employee) or (
			attached_to_doctype == "User" and attached_to_name == user
		)
		if owned:
			frappe.delete_doc("File", name, ignore_permissions=True, force=True)


@frappe.whitelist()
def get_employee_profile_stats(employee: str) -> dict:
	"""Lifetime payroll / billing totals for the Employee form sidebar."""
	frappe.has_permission("Employee", "read", employee, throw=True)
	emp = frappe.db.get_value(
		"Employee",
		employee,
		["name", "employee_name", "company", "user_id"],
		as_dict=True,
	)
	if not emp:
		frappe.throw(_("Employee not found"))

	company_currency = (
		frappe.db.get_value("Company", emp.company, "default_currency") if emp.company else "BZD"
	) or "BZD"

	from hrms.hr.staff_pro_roles import employee_is_client_billable

	hours = _total_hours(employee)
	income = _salary_totals(employee)
	has_client_billing = employee_is_client_billable(employee, user_id=emp.user_id)
	billed = _billed_totals(employee) if has_client_billing else {"amount": 0.0, "currency": "USD"}
	leave_remaining = _leave_remaining(employee)
	leave_money_remaining = _leave_money_remaining(employee)
	vacation = _vacation_balance(employee)
	billed_company = _convert_amount(billed["amount"], billed["currency"], company_currency)
	agent_profit = flt(billed_company) - flt(income["gross_pay"]) if has_client_billing else 0.0

	from hrms.hr.staff_pro_desk_permissions import filter_profile_stats_payload
	from hrms.hr.role_access import redact_profile_stats

	payload = {
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"user_id": emp.user_id or "",
		"company_currency": company_currency,
		"billing_currency": billed["currency"],
		"has_client_billing": has_client_billing,
		"total_hours": hours,
		"total_income": flt(income["gross_pay"], 2),
		"total_ss": flt(income["ss"], 2),
		"total_tax": flt(income["tax"], 2),
		"total_billed": flt(billed["amount"], 2),
		"agent_profit": flt(agent_profit, 2),
		"leave_remaining": leave_remaining,
		"leave_money_remaining": leave_money_remaining,
		"vacation_usable": vacation["usable_days"],
		"vacation_accruing": vacation["accruing_days"],
	}
	return filter_profile_stats_payload(redact_profile_stats(payload))


def _vacation_balance(employee: str) -> dict:
	empty = {"usable_days": 0.0, "accruing_days": 0.0, "granted_days": 0.0, "eligible": 0}
	try:
		from hrms.hr.pto_anniversary import vacation_balance

		return vacation_balance(employee) or empty
	except Exception:
		return empty


def _leave_remaining(employee: str) -> float:
	try:
		from hrms.hr.doctype.leave_application.leave_application import get_leave_details

		details = get_leave_details(employee, getdate())
	except Exception:
		return 0.0

	total = 0.0
	for values in (details.get("leave_allocation") or {}).values():
		total += flt(values.get("remaining_leaves"))
	return flt(total, 2)


def _leave_money_remaining(employee: str) -> float:
	try:
		from hrms.hr.doctype.leave_application.leave_application import get_leave_details
		from hrms.hr.pto_anniversary import PTO_LEAVE_TYPE, pto_money_value

		details = get_leave_details(employee, getdate())
		remaining = flt((details.get("leave_allocation") or {}).get(PTO_LEAVE_TYPE, {}).get("remaining_leaves"))
		return pto_money_value(employee, remaining)
	except Exception:
		return 0.0


def _total_hours(employee: str) -> float:
	if not frappe.db.table_exists("Attendance"):
		return 0.0
	rows = frappe.get_all(
		"Attendance",
		filters={"employee": employee, "docstatus": ["<", 2], "status": ["in", ["Present", "Half Day", "Work From Home"]]},
		fields=["working_hours", "status"],
	)
	standard = flt(frappe.db.get_single_value("HR Settings", "standard_working_hours")) or 8.0
	total = 0.0
	for row in rows:
		hours = flt(row.working_hours)
		if not hours:
			hours = standard / 2.0 if row.status == "Half Day" else standard
		total += hours
	return flt(total, 2)


def _salary_totals(employee: str) -> dict:
	gross = ss = tax = 0.0
	if frappe.db.table_exists("Salary Slip"):
		fields = ["name", "gross_pay", "net_pay", "total_working_hours"]
		meta_fields = {df.fieldname for df in frappe.get_meta("Salary Slip").fields}
		if "ss_employee_amount" in meta_fields:
			fields.append("ss_employee_amount")
		if "current_month_income_tax" in meta_fields:
			fields.append("current_month_income_tax")
		if "total_income_tax" in meta_fields:
			fields.append("total_income_tax")

		slips = frappe.get_all(
			"Salary Slip",
			filters={"employee": employee, "docstatus": 1},
			fields=fields,
		)
		for slip in slips:
			gross += flt(slip.gross_pay)
			ss += flt(slip.get("ss_employee_amount"))
			tax += flt(slip.get("current_month_income_tax") or 0)
			if not slip.get("current_month_income_tax"):
				tax += _tax_from_deductions(slip.name)

	if not ss and frappe.db.table_exists("Attendance"):
		att_fields = ["ss_deduction"] if frappe.db.has_column("Attendance", "ss_deduction") else []
		if att_fields:
			for amount in frappe.get_all(
				"Attendance",
				filters={"employee": employee, "docstatus": ["<", 2]},
				pluck="ss_deduction",
			):
				ss += flt(amount)

	if not tax and frappe.db.has_column("Attendance", "tax_deduction"):
		for amount in frappe.get_all(
			"Attendance",
			filters={"employee": employee, "docstatus": ["<", 2]},
			pluck="tax_deduction",
		):
			tax += flt(amount)

	if not gross and frappe.db.has_column("Attendance", "net_daily_pay"):
		for amount in frappe.get_all(
			"Attendance",
			filters={"employee": employee, "docstatus": ["<", 2]},
			pluck="net_daily_pay",
		):
			gross += flt(amount)

	return {"gross_pay": gross, "ss": ss, "tax": tax}


def _tax_from_deductions(salary_slip: str) -> float:
	if not salary_slip or not frappe.db.table_exists("Salary Detail"):
		return 0.0
	rows = frappe.get_all(
		"Salary Detail",
		filters={
			"parent": salary_slip,
			"parenttype": "Salary Slip",
			"parentfield": "deductions",
		},
		fields=["salary_component", "amount"],
	)
	total = 0.0
	for row in rows:
		name = (row.salary_component or "").lower()
		if "tax" in name or name in {"paye", "income tax"}:
			total += flt(row.amount)
	return total


def _billed_totals(employee: str) -> dict:
	currency = "USD"
	amount = 0.0
	if not frappe.db.table_exists("Client Invoice Item"):
		return {"amount": amount, "currency": currency}

	Item = frappe.qb.DocType("Client Invoice Item")
	Invoice = frappe.qb.DocType("Client Invoice")
	rows = (
		frappe.qb.from_(Item)
		.inner_join(Invoice)
		.on(Item.parent == Invoice.name)
		.select(Item.amount, Invoice.currency)
		.where(Item.employee == employee)
		.where(Invoice.docstatus == 1)
	).run(as_dict=True)
	for row in rows:
		amount += flt(row.amount)
		if row.currency:
			currency = row.currency
	return {"amount": amount, "currency": currency or "USD"}


def _convert_amount(amount: float, from_currency: str, to_currency: str) -> float:
	amount = flt(amount)
	if not amount or not from_currency or not to_currency or from_currency == to_currency:
		return amount
	try:
		from erpnext.setup.utils import get_exchange_rate

		rate = flt(get_exchange_rate(from_currency, to_currency, getdate())) or 1.0
	except Exception:
		rate = 1.0
	return flt(amount) * flt(rate)
