# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Role access switches: what a desk user is allowed to see."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint

# A missing value stays on, so existing roles keep today's access until someone switches it off.
def _area(fieldname, label, description, **targets):
	row = {"fieldname": fieldname, "label": label, "description": description}
	row.update(targets)
	return row


ACCESS_GROUPS = (
	{
		"title": "People",
		"intro": "The team, their records, and how they join or leave.",
		"flags": (
			_area(
				"see_people_dashboard",
				"People dashboard",
				"The people home screen and headcount charts.",
				links=("Human Resource",),
				dashboards=("Human Resource",),
				workspaces=("people",),
			),
			_area(
				"see_agents",
				"Agents",
				"Agent records, the directory, birthdays, exits, and headcount.",
				labels=("Agents", "Agent Directory", "Team Birthdays", "Agent Exits", "Headcount Analytics"),
				reports=("Employee Information", "Employee Birthday", "Employee Exits", "Employee Analytics"),
				workspaces=("people",),
			),
			_area(
				"see_floor_workers",
				"Floor workers",
				"The floor worker roster.",
				labels=("Floor Workers",),
				workspaces=("floor",),
			),
			_area(
				"see_paid_time_off",
				"Paid time off",
				"PTO balances and the paid time off page.",
				labels=("Paid Time Off",),
				links=("paid-time-off",),
				pages=("paid-time-off",),
				workspaces=("people",),
			),
			_area(
				"see_onboarding",
				"Onboarding",
				"New hire onboarding.",
				labels=("New Hire Onboarding",),
				links=("Employee Onboarding",),
				doctypes=("Employee Onboarding",),
				workspaces=("people",),
			),
			_area(
				"see_offboarding",
				"Offboarding",
				"Separations and exits in progress.",
				labels=("Offboarding",),
				links=("Employee Separation",),
				doctypes=("Employee Separation",),
				workspaces=("people",),
			),
			_area(
				"see_employee_requests",
				"Employee requests",
				"Requests agents send to HR.",
				labels=("Employee Requests",),
				links=("HR Request",),
				doctypes=("HR Request",),
				workspaces=("people",),
			),
			_area(
				"see_concerns",
				"Concerns and escalations",
				"Grievances and escalations.",
				labels=("Concerns & Escalations",),
				links=("Employee Grievance",),
				doctypes=("Employee Grievance",),
				workspaces=("people",),
			),
			_area(
				"see_people_setup",
				"People setup",
				"Departments, job titles, groups, request types, and training programs.",
				labels=(
					"Department",
					"Roles",
					"Team Groups",
					"Concern Types",
					"Request Types",
					"Training Programs",
				),
				links=(
					"Department",
					"Designation",
					"Employee Group",
					"Grievance Type",
					"HR Request Type",
					"Training Program",
				),
				doctypes=(
					"Department",
					"Designation",
					"Employee Group",
					"Grievance Type",
					"HR Request Type",
					"Training Program",
				),
				workspaces=("people",),
			),
		),
	},
	{
		"title": "Time",
		"intro": "Attendance, time off, overtime, and schedules.",
		"flags": (
			_area(
				"see_attendance",
				"Attendance",
				"The time dashboard, day view, calendar, and who is in.",
				labels=("Day View", "Attendance Calendar", "Who Is In"),
				links=("Attendance", "day-view", "in-out-today"),
				pages=("day-view", "in-out-today"),
				dashboards=("Attendance",),
				urls=("attendance/view/calendar",),
				doctypes=("Attendance",),
				workspaces=("time",),
			),
			_area(
				"see_time_clock",
				"Time clock adjustments",
				"Corrections to clock-in and clock-out times.",
				labels=("Time Clock Adjustment",),
				links=("time-clock-adjustments", "Time Clock Adjustment"),
				pages=("time-clock-adjustments",),
				doctypes=("Time Clock Adjustment",),
				workspaces=("time",),
			),
			_area(
				"see_holiday_work",
				"Holiday work",
				"Who is working a holiday.",
				labels=("Holiday Work List",),
				links=("holiday-work-list", "Holiday Work Election"),
				pages=("holiday-work-list",),
				doctypes=("Holiday Work Election",),
				workspaces=("time",),
			),
			_area(
				"see_time_off",
				"Time off requests",
				"Leave requests from the team.",
				labels=("Time Off Request",),
				links=("Leave Application",),
				doctypes=("Leave Application",),
				workspaces=("time",),
			),
			_area(
				"see_time_approvals",
				"Schedule approvals",
				"Schedule corrections and shift swaps waiting for approval.",
				labels=("Schedule Correction", "Shift Swap"),
				links=("Attendance Request", "Shift Request"),
				doctypes=("Attendance Request", "Shift Request"),
				workspaces=("time",),
			),
			_area(
				"see_overtime",
				"Overtime",
				"Overtime slips.",
				labels=("Overtime",),
				links=("Overtime Slip",),
				doctypes=("Overtime Slip",),
				workspaces=("time",),
			),
			_area(
				"see_time_reports",
				"Time reports",
				"Monthly attendance, shift coverage, PTO, holidays, and utilization.",
				labels=(
					"Monthly Attendance",
					"Shift Coverage",
					"PTO Summary",
					"Holiday Coverage",
					"Agent Utilization",
				),
				reports=(
					"Monthly Attendance Sheet",
					"Shift Attendance",
					"Employee Leave Balance Summary",
					"Employees working on a holiday",
					"Employee Hours Utilization Based On Timesheet",
				),
				workspaces=("time",),
			),
			_area(
				"see_schedules",
				"Schedules and holidays",
				"Shifts, work sites, holidays, and leave types.",
				labels=(
					"Overtime Setup",
					"Shift Templates",
					"Work Site",
					"Shift Patterns",
					"Holiday List",
					"Leave Type",
				),
				links=(
					"Shift Type",
					"Shift Location",
					"Shift Schedule",
					"Holiday List",
					"Leave Type",
				),
				doctypes=(
					"Shift Type",
					"Shift Location",
					"Shift Schedule",
					"Holiday List",
					"Leave Type",
				),
				workspaces=("time",),
			),
		),
	},
	{
		"title": "Pay",
		"intro": "Hourly pay and what gets billed for this role.",
		"flags": (
			_area(
				"see_agent_salary",
				"Agent salary",
				"Hourly pay, pay stubs, bonuses, and payroll amounts.",
				labels=(
					"Run Payroll",
					"Pay Rate Setup",
					"Current Pay Stubs",
					"Past Pay Stubs",
					"Bonuses",
					"Pay Holds",
					"Bonus Types",
					"Pay Components",
					"Pay Structure",
				),
				links=(
					"Payroll",
					"Payroll Entry",
					"Salary Structure Assignment",
					"Salary Slip",
					"Additional Salary",
					"Salary Withholding",
					"Bonus Type",
					"Salary Component",
					"Salary Structure",
				),
				doctypes=(
					"Salary Slip",
					"Salary Structure",
					"Salary Structure Assignment",
					"Salary Component",
					"Payroll Entry",
					"Additional Salary",
					"Salary Withholding",
					"Employee Incentive",
					"Bonus Type",
				),
				dashboards=("Payroll",),
				urls=("salary-slip",),
				workspaces=("pay",),
			),
			_area(
				"see_td4_forms",
				"TD4 forms",
				"Request, review, and store agent TD4 tax forms.",
				labels=("TD4 Forms",),
				links=("TD4 Form",),
			),
			_area(
				"see_bill_to_client",
				"Bill to client",
				"The client an agent is billed to, and the hourly rate charged.",
			),
			_area(
				"see_bank_details",
				"Bank and payment details",
				"How the agent is paid, and their bank account.",
			),
		),
	},
	{
		"title": "Talent",
		"intro": "Hiring, reviews, and workforce planning.",
		"flags": (
			_area(
				"see_talent_dashboard",
				"Talent dashboard",
				"The hiring and performance home screen.",
				links=("Recruitment",),
				dashboards=("Recruitment",),
				workspaces=("talent",),
			),
			_area(
				"see_hiring",
				"Hiring",
				"Open positions, candidates, interviews, offers, and hire letters.",
				labels=("Open Positions", "Candidates", "Interviews", "Offer Letters", "Hire Letters"),
				links=("Job Opening", "Job Applicant", "Interview", "Job Offer", "Appointment Letter"),
				doctypes=("Job Opening", "Job Applicant", "Interview", "Job Offer", "Appointment Letter"),
				workspaces=("talent",),
			),
			_area(
				"see_performance",
				"Performance",
				"Goals, review cycles, QA feedback, and promotions.",
				labels=(
					"Performance Goals",
					"Review Cycle",
					"Performance Reviews",
					"QA Feedback",
					"Promotions",
				),
				links=("Goal", "Appraisal Cycle", "Appraisal", "Employee Performance Feedback", "Employee Promotion"),
				doctypes=("Goal", "Appraisal Cycle", "Appraisal", "Employee Performance Feedback", "Employee Promotion"),
				workspaces=("talent",),
			),
			_area(
				"see_workforce",
				"Workforce planning",
				"Headcount requests, staffing plans, and referrals.",
				labels=("Headcount Request", "Workforce Plan", "Refer a Candidate"),
				links=("Job Requisition", "Staffing Plan", "Employee Referral"),
				doctypes=("Job Requisition", "Staffing Plan", "Employee Referral"),
				workspaces=("talent",),
			),
			_area(
				"see_talent_reports",
				"Talent reports",
				"Hiring analytics and the review overview.",
				labels=("Hiring Analytics", "Review Overview"),
				reports=("Recruitment Analytics", "Appraisal Overview"),
				workspaces=("talent",),
			),
			_area(
				"see_talent_setup",
				"Talent setup",
				"Interview types, letter templates, scorecards, and document categories.",
				labels=(
					"Document Categories",
					"Interview Types",
					"Position Templates",
					"Hire Letter Templates",
					"Offer Term Templates",
					"Review Templates",
					"KRA",
					"QA Scorecard Criteria",
				),
				links=(
					"Document Category",
					"Interview Type",
					"Job Opening Template",
					"Appointment Letter Template",
					"Job Offer Term Template",
					"Appraisal Template",
					"KRA",
					"Employee Feedback Criteria",
				),
				doctypes=(
					"Document Category",
					"Interview Type",
					"Job Opening Template",
					"Appointment Letter Template",
					"Job Offer Term Template",
					"Appraisal Template",
					"KRA",
					"Employee Feedback Criteria",
				),
				workspaces=("talent",),
			),
			_area(
				"see_careers",
				"Careers portal",
				"The public jobs page.",
				labels=("Careers Portal",),
				urls=("/jobs",),
				workspaces=("talent",),
			),
		),
	},
	{
		"title": "Filesystem",
		"intro": "Files kept for each agent.",
		"flags": (
			_area(
				"see_agent_documents",
				"Agent documents",
				"The agent filesystem and uploaded documents.",
				labels=("Filesystem",),
				links=("agent-filesystem", "Agent Document"),
				pages=("agent-filesystem",),
				doctypes=("Agent Document",),
				workspaces=("filesystem",),
			),
		),
	},
	{
		"title": "Floor",
		"intro": "The office map and where people sit.",
		"flags": (
			_area(
				"see_floor",
				"Floor plan",
				"Floors, cubicles, and the floor map.",
				labels=("Floor Map", "Cubicles", "Floors"),
				links=("floor-map", "Cubicle", "Office Floor"),
				pages=("floor-map",),
				doctypes=("Cubicle", "Office Floor"),
				workspaces=("floor",),
			),
		),
	},
	{
		"title": "Social security and taxes",
		"intro": "Social security numbers, contributions, and tax filings.",
		"flags": (
			_area(
				"see_social_security",
				"Social security and taxes",
				"Social security numbers, contributions, and tax adjustments.",
				labels=(
					"Social Security",
					"Tax Exemption Declaration",
					"Tax Period Adjustments",
					"Tax Computation",
					"Tax Deductions",
					"SS Contribution Table",
					"Income Tax Slab",
					"Exemption Category",
					"Exemption Sub Category",
				),
				links=(
					"SS and Taxes",
					"Social Security Deductions",
					"Employee Tax Exemption Declaration",
					"Employee Tax Adjustment",
					"Income Tax Computation",
					"Income Tax Deductions",
					"Social Security Contribution Table",
					"Income Tax Slab",
					"Employee Tax Exemption Category",
					"Employee Tax Exemption Sub Category",
				),
				doctypes=(
					"Employee Tax Exemption Declaration",
					"Employee Tax Adjustment",
					"Income Tax Slab",
					"Social Security Contribution Table",
					"Employee Tax Exemption Category",
					"Employee Tax Exemption Sub Category",
				),
				reports=(
					"Social Security Deductions",
					"Income Tax Computation",
					"Income Tax Deductions",
				),
				dashboards=("SS and Taxes",),
				workspaces=("ss and taxes",),
			),
		),
	},
	{
		"title": "Finance",
		"intro": "Clients, invoices, and what they owe.",
		"flags": (
			_area(
				"see_clients",
				"Clients",
				"Client records.",
				labels=("Clients",),
				links=("Customer",),
				doctypes=("Customer",),
				workspaces=("finance",),
			),
			_area(
				"see_client_invoices",
				"Client invoices",
				"Client invoices, posted invoices, and outstanding balances.",
				labels=("Client Invoices", "Posted Invoices", "Outstanding Invoices"),
				links=("Client Invoice", "Sales Invoice", "Accounts Receivable"),
				doctypes=("Client Invoice", "Sales Invoice"),
				reports=("Accounts Receivable",),
				workspaces=("finance",),
			),
		),
	},
	{
		"title": "Admin",
		"intro": "Who can sign in, how the app is set up, and the audit trail.",
		"flags": (
			_area(
				"see_users_and_roles",
				"Users and roles",
				"User accounts, roles, and the permission manager.",
				labels=("User", "Role", "Role Permission Manager"),
				links=("User", "Role", "permission-manager"),
				pages=("permission-manager",),
				doctypes=("User", "Role"),
				workspaces=("admin",),
			),
			_area(
				"see_system_setup",
				"System setup",
				"System settings, backups, and the website.",
				labels=("System Settings", "Website Settings", "Backups"),
				links=("System Settings", "Website Settings", "backups"),
				pages=("backups",),
				doctypes=("System Settings", "Website Settings"),
				workspaces=("admin",),
			),
			_area(
				"see_app_settings",
				"App settings",
				"HR settings and payroll settings.",
				labels=("HR Settings", "Payroll Settings"),
				links=("HR Settings", "Payroll Settings"),
				doctypes=("HR Settings", "Payroll Settings"),
				workspaces=("admin",),
			),
			_area(
				"see_audit_logs",
				"Audit logs",
				"Activity, access, permissions, and the audit trail.",
				labels=("Activity Log", "Access Log", "Permission Log", "Audit Trail"),
				links=("Activity Log", "Access Log", "Permission Log", "Audit Trail"),
				doctypes=("Activity Log", "Access Log", "Permission Log"),
				reports=("Audit Trail",),
				workspaces=("admin",),
			),
		),
	},
)


def _iter_specs():
	for group in ACCESS_GROUPS:
		yield from group["flags"]


FLAG_NAMES = tuple(spec["fieldname"] for spec in _iter_specs())

_WORKSPACE_BUCKET: dict[str, list[str]] = {}
for _spec in _iter_specs():
	for _key in _spec.get("workspaces") or ():
		_WORKSPACE_BUCKET.setdefault(_key, []).append(_spec["fieldname"])
WORKSPACE_FLAGS = {key: tuple(names) for key, names in _WORKSPACE_BUCKET.items()}

WORKSPACE_ROUTE_NAMES = {
	"people": ("People", "people"),
	"time": ("Time", "time"),
	"pay": ("Pay", "pay", "Payroll"),
	"talent": ("Talent", "talent"),
	"filesystem": ("Filesystem", "filesystem"),
	"floor": ("Floor", "floor"),
	"ss and taxes": ("SS and Taxes", "ss and taxes"),
	"finance": ("Finance", "finance"),
	"admin": ("Admin", "admin"),
}

# These screens are hidden from the desk. A permission hook on them would also
# block Frappe from reading settings while the desk boots.
SKIP_PERMISSION_HOOK = frozenset(
	{
		"System Settings",
		"Website Settings",
		"HR Settings",
		"Payroll Settings",
		"User",
		"Role",
	}
)

DOCTYPE_FLAGS = {}
for _spec in _iter_specs():
	for _doctype in _spec.get("doctypes") or ():
		if _doctype in SKIP_PERMISSION_HOOK:
			continue
		DOCTYPE_FLAGS[_doctype] = _spec["fieldname"]

EMPLOYEE_FIELDS = {
	"see_agent_salary": (
		"ctc",
		"salary_currency",
		"user_bonus",
		"user_bonus_period_months",
		"user_bonus_attendance_target",
		"user_bonus_if_below",
		"user_bonus_attendance",
		"user_bonus_missed_days",
		"user_bonus_status",
	),
	"see_bill_to_client": (
		"bill_to_customer",
		"billing_rate",
		"billing_currency",
	),
	"see_bank_details": (
		"salary_mode",
		"bank_name",
		"bank_ac_no",
	),
	"see_social_security": ("social_security_number",),
}

CUSTOMER_FIELDS = {
	"see_bill_to_client": ("default_billing_rate",),
}

_READY_CACHE = "staff_pro_role_access_ready"
_SETUP_LOCK = "staff_pro_role_access_setup"


def flag_enabled(value) -> bool:
	"""Unset access stays on. Only an explicit off hides the area."""
	if value is None or value == "":
		return True
	return bool(cint(value))


def full_access() -> dict[str, bool]:
	return {name: True for name in FLAG_NAMES}


def no_access() -> dict[str, bool]:
	return {name: False for name in FLAG_NAMES}


def merge_access_rows(rows) -> dict[str, bool]:
	"""A person can see an area when any of their roles leaves that switch on."""
	if not rows:
		return full_access()
	access = no_access()
	for row in rows:
		for name in FLAG_NAMES:
			if flag_enabled((row or {}).get(name)):
				access[name] = True
	return access


def fields_ready() -> bool:
	if not frappe.db.exists("DocType", "Role"):
		return False
	meta = frappe.get_meta("Role")
	return all(meta.has_field(name) for name in FLAG_NAMES)


def ensure_role_access_fields():
	"""Add the hidden switches on Role and hide desk fields this app does not use."""
	if not frappe.db.exists("DocType", "Role"):
		return
	if frappe.cache.get_value(_READY_CACHE) and fields_ready():
		return

	# Boot runs this on every request. One worker does the writes; the rest skip
	# so two requests cannot deadlock on the same Property Setter or System Settings row.
	lock = frappe.cache.lock(_SETUP_LOCK, timeout=120, blocking=False)
	if not lock.acquire(blocking=False):
		return
	try:
		if frappe.cache.get_value(_READY_CACHE) and fields_ready():
			return
		had_td4 = frappe.get_meta("Role").has_field("see_td4_forms")
		previous = frappe.flags.ignore_permissions
		frappe.flags.ignore_permissions = True
		try:
			create_custom_fields(
				{
					"Role": [
						{
							"fieldname": spec["fieldname"],
							"label": spec["label"],
							"fieldtype": "Check",
							"default": "1",
							"hidden": 1,
							"insert_after": "role_name",
						}
						for group in ACCESS_GROUPS
						for spec in group["flags"]
					]
				},
				ignore_validate=True,
			)
			_hide_unused_role_fields()
			if not had_td4:
				_seed_td4_switch()
		finally:
			frappe.flags.ignore_permissions = previous
		frappe.clear_cache(doctype="Role")
		if fields_ready():
			frappe.cache.set_value(_READY_CACHE, 1)
	except (frappe.QueryDeadlockError, frappe.QueryTimeoutError, frappe.DuplicateEntryError):
		return
	finally:
		try:
			lock.release()
		except Exception:
			pass


def _hide_field(doctype: str, fieldname: str) -> None:
	if frappe.db.exists(
		"Property Setter",
		{"doc_type": doctype, "field_name": fieldname, "property": "hidden"},
	):
		return
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	try:
		make_property_setter(
			doctype,
			fieldname,
			"hidden",
			"1",
			"Check",
			validate_fields_for_doctype=False,
		)
	except frappe.DuplicateEntryError:
		return


def _seed_td4_switch():
	"""Keep today's TD4 access: it was on only when salary and social security were both on."""
	if not frappe.db.has_column("Role", "see_td4_forms"):
		return
	if not frappe.db.has_column("Role", "see_agent_salary"):
		return
	if not frappe.db.has_column("Role", "see_social_security"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabRole`
		SET see_td4_forms = 0
		WHERE IFNULL(see_agent_salary, 1) = 0
			OR IFNULL(see_social_security, 1) = 0
		"""
	)


def _hide_unused_role_fields():
	meta = frappe.get_meta("Role")
	for fieldname in ("home_page", "restrict_to_domain", "two_factor_auth"):
		if not meta.has_field(fieldname):
			continue
		_hide_field("Role", fieldname)
	disable_two_factor_auth()


def disable_two_factor_auth():
	"""Staff Pro does not use two-factor login. Hide it and leave it off."""
	if frappe.db.exists("DocType", "Role") and frappe.get_meta("Role").has_field("two_factor_auth"):
		_hide_field("Role", "two_factor_auth")
		frappe.clear_cache(doctype="Role")
	if frappe.db.has_column("Role", "two_factor_auth") and frappe.db.exists("Role", {"two_factor_auth": 1}):
		frappe.db.sql("UPDATE `tabRole` SET two_factor_auth = 0 WHERE IFNULL(two_factor_auth, 0) != 0")

	if frappe.db.exists("DocType", "System Settings"):
		settings = frappe.get_meta("System Settings")
		if settings.has_field("enable_two_factor_auth") and cint(
			frappe.db.get_single_value("System Settings", "enable_two_factor_auth")
		):
			frappe.db.set_single_value(
				"System Settings", "enable_two_factor_auth", 0, update_modified=False
			)
		for fieldname in (
			"two_factor_authentication",
			"enable_two_factor_auth",
			"bypass_2fa_for_retricted_ip_users",
			"bypass_restrict_ip_check_if_2fa_enabled",
			"two_factor_method",
			"lifespan_qrcode_image",
			"otp_issuer_name",
			"otp_sms_template",
		):
			if not settings.has_field(fieldname):
				continue
			_hide_field("System Settings", fieldname)
		frappe.clear_cache(doctype="System Settings")

	if frappe.db.exists("DocType", "User"):
		user_meta = frappe.get_meta("User")
		if user_meta.has_field("bypass_restrict_ip_check_if_2fa_enabled"):
			_hide_field("User", "bypass_restrict_ip_check_if_2fa_enabled")
			frappe.clear_cache(doctype="User")


ACCESS_CHANGED_EVENT = "staff_pro_access_changed"


def clear_user_access_cache(user=None) -> None:
	cached = getattr(frappe.local, "_staff_pro_user_access", None)
	if not isinstance(cached, dict):
		return
	if user and cached.get("_user") != user:
		return
	frappe.local._staff_pro_user_access = None


def session_access_payload(user=None) -> dict:
	"""Access flags and blocked routes for one signed-in desk user."""
	user = user or frappe.session.user
	clear_user_access_cache(user)
	access = user_access(user)
	return {"access": access, "blocks": blocked_routes(access)}


@frappe.whitelist()
def get_session_access() -> dict:
	if frappe.session.user in {None, "Guest"}:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return session_access_payload()


@frappe.whitelist()
def assign_role_user(role: str, user: str, remove: int | str = 0) -> str:
	"""Attach or detach one person. Accepts a username, email, or full name."""
	role_name = (role or "").strip()
	if not role_name or not frappe.db.exists("Role", role_name):
		frappe.throw(_("Role {0} was not found.").format(role_name or _("Unknown")))

	from hrms.overrides.employee_master import resolve_user_from_login

	user_name = resolve_user_from_login(user)
	if not user_name or user_name == "Guest":
		frappe.throw(_("User {0} was not found.").format((user or "").strip() or _("Unknown")))

	frappe.has_permission("User", "write", doc=user_name, throw=True)
	if frappe.get_all(
		"User Role Profile",
		filters={"parent": user_name, "parenttype": "User"},
		limit=1,
	):
		frappe.throw(
			_("{0}'s roles come from a role profile. Change that profile to update this role.").format(
				frappe.db.get_value("User", user_name, "full_name") or user_name
			)
		)

	doc = frappe.get_doc("User", user_name)
	doc.check_permission("write")
	if cint(remove):
		doc.remove_roles(role_name)
	else:
		doc.add_roles(role_name)
	return user_name


def users_with_role(role_name: str) -> list[str]:
	if not role_name:
		return []
	return [
		name
		for name in frappe.get_all(
			"Has Role",
			filters={"role": role_name, "parenttype": "User"},
			pluck="parent",
		)
		if name and name != "Guest"
	]


def _role_access_changed(doc) -> bool:
	before = doc.get_doc_before_save()
	if not before:
		return True
	for name in FLAG_NAMES:
		if flag_enabled(doc.get(name)) != flag_enabled(before.get(name)):
			return True
	return False


def _user_roles_changed(doc) -> bool:
	before = doc.get_doc_before_save()
	if not before:
		return bool(doc.get("roles"))
	old = {row.role for row in (before.get("roles") or []) if row.role}
	new = {row.role for row in (doc.get("roles") or []) if row.role}
	return old != new


def notify_access_changed(users) -> None:
	seen = set()
	for user in users or []:
		if not user or user in seen or user == "Guest":
			continue
		seen.add(user)
		try:
			frappe.clear_cache(user=user)
		except Exception:
			pass
		payload = session_access_payload(user)
		frappe.publish_realtime(ACCESS_CHANGED_EVENT, payload, user=user, after_commit=True)


def on_role_update(doc, method=None):
	if _role_access_changed(doc):
		frappe.clear_cache(doctype="Role")
		notify_access_changed(users_with_role(doc.name))
	try:
		sync_role_switch_permissions(getattr(doc, "name", None))
	except Exception:
		frappe.log_error(title="Role access sync failed")


def on_user_update(doc, method=None):
	if not _user_roles_changed(doc):
		return
	notify_access_changed([doc.name])


def on_has_role_change(doc, method=None):
	if getattr(doc, "parenttype", None) != "User":
		return
	parent = getattr(doc, "parent", None)
	if parent:
		notify_access_changed([parent])


def user_access(user=None) -> dict[str, bool]:
	user = user or frappe.session.user
	if not user or user == "Guest":
		return no_access()
	if user == "Administrator":
		return full_access()

	cached = getattr(frappe.local, "_staff_pro_user_access", None)
	if isinstance(cached, dict) and cached.get("_user") == user:
		return cached["access"]

	if not fields_ready():
		access = full_access()
	else:
		roles = [role for role in frappe.get_roles(user) if role not in {"All", "Guest", "Desk User"}]
		if not roles:
			access = full_access()
		else:
			rows = frappe.get_all("Role", filters={"name": ["in", roles]}, fields=["name", *FLAG_NAMES])
			access = merge_access_rows(rows)
	frappe.local._staff_pro_user_access = {"_user": user, "access": access}
	return access


def can_see(flag: str, user=None) -> bool:
	return bool(user_access(user).get(flag))


def access_groups_boot():
	"""Switch copy sent to the desk. Targets stay on the server."""
	return [
		{
			"title": group["title"],
			"intro": group["intro"],
			"flags": [
				{
					"fieldname": spec["fieldname"],
					"label": spec["label"],
					"description": spec["description"],
				}
				for spec in group["flags"]
			],
		}
		for group in ACCESS_GROUPS
	]


def _unique(values) -> list[str]:
	seen = []
	for value in values:
		if value and value not in seen:
			seen.append(value)
	return seen


def blocked_routes(access=None) -> dict[str, list[str]]:
	access = access or user_access()
	doctypes: list[str] = []
	reports: list[str] = []
	pages: list[str] = []
	dashboards: list[str] = []
	urls: list[str] = []
	for spec in _iter_specs():
		if access.get(spec["fieldname"], True):
			continue
		doctypes.extend(spec.get("doctypes") or ())
		reports.extend(spec.get("reports") or ())
		pages.extend(spec.get("pages") or ())
		dashboards.extend(spec.get("dashboards") or ())
		urls.extend(spec.get("urls") or ())
	if not access.get("see_td4_forms", True):
		doctypes.append("TD4 Form")
	if not access.get("see_agents", True) and not access.get("see_floor_workers", True):
		doctypes.append("Employee")
	workspaces: list[str] = []
	for key, names in WORKSPACE_ROUTE_NAMES.items():
		if not workspace_allowed(key, access):
			workspaces.extend(names)
	return {
		"doctypes": _unique(doctypes),
		"reports": _unique(reports),
		"pages": _unique(pages),
		"dashboards": _unique(dashboards),
		"workspaces": _unique(workspaces),
		"urls": _unique(urls),
	}


def workspace_allowed(name, access=None) -> bool:
	from hrms.hr.bpo_user_permissions import canonical_sidebar_key

	if isinstance(name, dict):
		name = name.get("name") or name.get("title") or name.get("label")
	access = access if access is not None else user_access()
	key = canonical_sidebar_key(name)
	if key == "filesystem":
		if access.get("see_agent_documents", True):
			return True
		return access.get("see_td4_forms", True)
	flags = WORKSPACE_FLAGS.get(key)
	if not flags:
		return True
	return any(access.get(flag, True) for flag in flags)


def _session_is_system_manager() -> bool:
	user = getattr(getattr(frappe, "session", None), "user", None)
	if not user or user == "Guest":
		return False
	if user == "Administrator":
		return True
	try:
		roles = frappe.get_roles(user)
	except Exception:
		return False
	return "System Manager" in set(roles or [])


def _matched_flags(item) -> list[str]:
	label = str(item.get("label") or "")
	link = str(item.get("link_to") or "")
	url = str(item.get("url") or "")
	label_hits: list[str] = []
	link_hits: list[str] = []
	url_hits: list[str] = []
	for spec in _iter_specs():
		name = spec["fieldname"]
		if label and label in (spec.get("labels") or ()):
			label_hits.append(name)
		if link and link in (spec.get("links") or ()):
			link_hits.append(name)
		if url and any(part and part in url for part in (spec.get("urls") or ())):
			url_hits.append(name)
	if label_hits:
		hits = label_hits
	elif link_hits:
		hits = link_hits
	else:
		hits = url_hits
	return hits


def sidebar_item_has_switch(item) -> bool:
	"""True when a sidebar row is tied to a Role form switch."""
	if not isinstance(item, dict):
		return False
	if str(item.get("type") or "") in {"Section Break", "section"}:
		return False
	return bool(_matched_flags(item))


def sidebar_item_allowed(item, access=None, is_system_manager=None) -> bool:
	if not isinstance(item, dict):
		return True
	if str(item.get("type") or "") in {"Section Break", "section"}:
		return True
	from hrms.hr.master_key import is_master_key_sidebar_item

	if is_master_key_sidebar_item(item):
		if is_system_manager is None:
			is_system_manager = _session_is_system_manager()
		return bool(is_system_manager)
	access = access if access is not None else user_access()
	hits = _matched_flags(item)
	if not hits:
		return True
	return any(bool(access.get(flag, True)) for flag in hits)


def drop_empty_sections(rows):
	"""Hide a sidebar heading once every link under it is gone."""
	if not isinstance(rows, list):
		return rows
	cleaned = []
	index = 0
	while index < len(rows):
		row = rows[index]
		if str((row or {}).get("type") or "") in {"Section Break", "section"}:
			nxt = index + 1
			has_link = False
			while nxt < len(rows) and str((rows[nxt] or {}).get("type") or "") not in {"Section Break", "section"}:
				has_link = True
				nxt += 1
			if has_link:
				cleaned.append(row)
			index = nxt
			continue
		cleaned.append(row)
		index += 1
	return cleaned


def has_listed_permission(doc=None, ptype=None, user=None, debug=False):
	doctype = getattr(doc, "doctype", None)
	flag = DOCTYPE_FLAGS.get(doctype)
	if not flag:
		return True
	return can_see(flag, user)


def has_employee_permission(doc=None, ptype=None, user=None, debug=False):
	if doc is None or not getattr(doc, "doctype", None):
		return True
	agents = can_see("see_agents", user)
	floor = can_see("see_floor_workers", user)
	if agents and floor:
		return True
	is_floor = cint(getattr(doc, "is_floor_worker", 0))
	if is_floor:
		return floor
	return agents


def employee_permission_query(user=None):
	agents = can_see("see_agents", user)
	floor = can_see("see_floor_workers", user)
	if agents and floor:
		return ""
	if not agents and not floor:
		return "1=0"
	try:
		if not frappe.get_meta("Employee").has_field("is_floor_worker"):
			return ""
	except Exception:
		return ""
	if floor and not agents:
		return "ifnull(`tabEmployee`.`is_floor_worker`, 0) = 1"
	return "ifnull(`tabEmployee`.`is_floor_worker`, 0) = 0"


def has_salary_permission(doc=None, ptype=None, user=None, debug=False):
	return can_see("see_agent_salary", user)


def has_invoice_permission(doc=None, ptype=None, user=None, debug=False):
	return can_see("see_client_invoices", user)


def has_tax_permission(doc=None, ptype=None, user=None, debug=False):
	return can_see("see_social_security", user)


def hidden_employee_fields(user=None) -> list[str]:
	access = user_access(user)
	fields: list[str] = []
	for flag, names in EMPLOYEE_FIELDS.items():
		if access.get(flag, True):
			continue
		fields.extend(names)
	return fields


def redact_employee(doc, method=None):
	if frappe.session.user == "Administrator":
		return
	for field in hidden_employee_fields():
		if doc.meta.has_field(field):
			doc.set(field, None)


def restore_employee_fields(doc, method=None):
	"""Keep switched-off values unchanged when this user saves the agent."""
	if frappe.session.user == "Administrator":
		return
	fields = [field for field in hidden_employee_fields() if doc.meta.has_field(field)]
	if not fields:
		return
	if doc.is_new() or not doc.name or not frappe.db.exists("Employee", doc.name):
		for field in fields:
			doc.set(field, None)
		return
	stored = frappe.db.get_value("Employee", doc.name, fields, as_dict=True) or {}
	for field in fields:
		doc.set(field, stored.get(field))


def redact_customer(doc, method=None):
	if frappe.session.user == "Administrator" or can_see("see_bill_to_client"):
		return
	if doc.meta.has_field("default_billing_rate"):
		doc.set("default_billing_rate", None)


def restore_customer_fields(doc, method=None):
	if frappe.session.user == "Administrator" or can_see("see_bill_to_client"):
		return
	if not doc.meta.has_field("default_billing_rate"):
		return
	if doc.is_new() or not doc.name or not frappe.db.exists("Customer", doc.name):
		doc.default_billing_rate = None
		return
	doc.default_billing_rate = frappe.db.get_value("Customer", doc.name, "default_billing_rate")


def redact_profile_stats(stats: dict, access=None) -> dict:
	access = access or user_access()
	if not access.get("see_agent_salary", True):
		stats["total_income"] = None
		stats["leave_money_remaining"] = None
		stats["agent_profit"] = None
	if not access.get("see_social_security", True):
		stats["total_ss"] = None
		stats["total_tax"] = None
	sees_billing = access.get("see_bill_to_client", True) or access.get("see_client_invoices", True)
	if not sees_billing:
		stats["total_billed"] = None
		stats["agent_profit"] = None
	if not access.get("see_agent_salary", True) or not sees_billing:
		stats["agent_profit"] = None
	return stats


def redact_query_rows(doctype, rows):
	if frappe.session.user in {"Administrator", "Guest"} or not doctype or not isinstance(rows, list):
		return rows
	if not rows or not isinstance(rows[0], dict):
		return rows
	fields = _query_fields_to_blank(doctype)
	if not fields:
		return rows
	for row in rows:
		for field in fields:
			if field in row:
				row[field] = None
	return rows


HOURS_SALARY_FIELDS = ("hour_rate", "daily_pay", "net_daily_pay")
HOURS_SS_FIELDS = ("ss_deduction", "tax_deduction", "week_ss", "week_tax")

SKIP_SWITCH_GRANT_ROLES = frozenset(
	{
		"Administrator",
		"System Manager",
		"Guest",
		"All",
		"Desk User",
		"Employee",
		"Employee Self Service",
	}
)


def redact_hours_payload(payload, access=None):
	"""Drop salary and SS amounts the signed-in role is not allowed to see."""
	access = access or user_access()
	see_salary = access.get("see_agent_salary", True)
	see_ss = access.get("see_social_security", True)
	if see_salary and see_ss:
		return payload

	def strip(row):
		if not isinstance(row, dict):
			return row
		out = dict(row)
		if not see_salary:
			for field in HOURS_SALARY_FIELDS:
				out.pop(field, None)
		if not see_ss:
			for field in HOURS_SS_FIELDS:
				out.pop(field, None)
		return out

	if isinstance(payload, list):
		return [strip(row) for row in payload]
	if not isinstance(payload, dict):
		return payload
	if "rows" in payload or "totals" in payload:
		out = dict(payload)
		if isinstance(payload.get("rows"), list):
			out["rows"] = [strip(row) for row in payload["rows"]]
		if isinstance(payload.get("totals"), dict):
			out["totals"] = strip(payload["totals"])
		return out
	return strip(payload)


def switch_grant_targets(access=None) -> dict[str, list[str]]:
	"""DocTypes, reports, and pages a role should be able to open for its on switches."""
	access = access or full_access()
	doctypes: list[str] = []
	reports: list[str] = []
	pages: list[str] = []
	for spec in _iter_specs():
		if not access.get(spec["fieldname"], True):
			continue
		doctypes.extend(spec.get("doctypes") or ())
		reports.extend(spec.get("reports") or ())
		pages.extend(spec.get("pages") or ())
		for link in spec.get("links") or ():
			if link and link not in doctypes and link not in pages:
				doctypes.append(link)
	if access.get("see_agents", True) or access.get("see_floor_workers", True):
		doctypes.append("Employee")
	if access.get("see_td4_forms", True):
		doctypes.append("TD4 Form")
	return {
		"doctypes": _unique(doctypes),
		"reports": _unique(reports),
		"pages": _unique(pages),
	}


def _role_switch_access(role_name: str) -> dict[str, bool] | None:
	if not role_name or role_name in SKIP_SWITCH_GRANT_ROLES:
		return None
	if not frappe.db.exists("Role", role_name):
		return None
	if not frappe.db.get_value("Role", role_name, "desk_access"):
		return None
	if not fields_ready():
		return full_access()
	row = frappe.db.get_value("Role", role_name, FLAG_NAMES, as_dict=True) or {}
	return {name: flag_enabled(row.get(name)) for name in FLAG_NAMES}


def _ensure_doctype_read(doctype: str, role: str) -> None:
	if not doctype or not frappe.db.exists("DocType", doctype):
		return
	from frappe.permissions import add_permission, update_permission_property

	try:
		add_permission(doctype, role, permlevel=0)
	except Exception:
		return
	for ptype in ("read", "select", "report", "export"):
		try:
			update_permission_property(doctype, role, permlevel=0, ptype=ptype, value=1)
		except Exception:
			continue


def _ensure_child_role(parenttype: str, parent: str, role: str) -> None:
	if not parent or not frappe.db.exists(parenttype, parent):
		return
	if frappe.db.exists("Has Role", {"parent": parent, "parenttype": parenttype, "role": role}):
		return
	try:
		frappe.get_doc(
			{
				"doctype": "Has Role",
				"parent": parent,
				"parenttype": parenttype,
				"parentfield": "roles",
				"role": role,
			}
		).insert(ignore_permissions=True)
	except Exception:
		return


def sync_role_switch_permissions(role_name: str | None) -> None:
	"""Give a desk role read access to every screen its switches leave on."""
	access = _role_switch_access(role_name)
	if not access:
		return
	targets = switch_grant_targets(access)
	for doctype in targets["doctypes"]:
		_ensure_doctype_read(doctype, role_name)
	for report in targets["reports"]:
		_ensure_doctype_read(report, role_name)
		_ensure_child_role("Report", report, role_name)
	for page in targets["pages"]:
		_ensure_child_role("Page", page, role_name)


def sync_all_role_switch_permissions() -> None:
	if not frappe.db.exists("DocType", "Role"):
		return
	ensure_role_access_fields()
	roles = frappe.get_all("Role", filters={"desk_access": 1}, pluck="name")
	for role in roles:
		if role in SKIP_SWITCH_GRANT_ROLES:
			continue
		sync_role_switch_permissions(role)
	frappe.clear_cache()


def _query_fields_to_blank(doctype) -> tuple[str, ...]:
	if doctype == "Employee":
		return tuple(hidden_employee_fields())
	if doctype == "Customer" and not can_see("see_bill_to_client"):
		return CUSTOMER_FIELDS["see_bill_to_client"]
	if doctype in {"Client Invoice Item", "Sales Invoice Item"} and not can_see("see_bill_to_client"):
		return ("billing_rate",)
	if doctype == "Attendance":
		fields: list[str] = []
		if not can_see("see_agent_salary"):
			fields.extend(HOURS_SALARY_FIELDS)
		if not can_see("see_social_security"):
			fields.extend(HOURS_SS_FIELDS)
		return tuple(fields)
	return ()


def install_list_redaction():
	if getattr(frappe.flags, "staff_pro_list_redaction", False):
		return
	try:
		from frappe.model.db_query import DatabaseQuery
	except ImportError:
		return
	if getattr(DatabaseQuery, "_staff_pro_redaction", False):
		return
	if not callable(getattr(DatabaseQuery, "execute", None)):
		return

	original = DatabaseQuery.execute

	def execute(self, *args, **kwargs):
		result = original(self, *args, **kwargs)
		try:
			return redact_query_rows(getattr(self, "doctype", None), result)
		except Exception:
			return result

	DatabaseQuery.execute = execute
	DatabaseQuery._staff_pro_redaction = True
	frappe.flags.staff_pro_list_redaction = True


def require_salary_access():
	if not can_see("see_agent_salary"):
		frappe.throw(_("You cannot view or change agent salary."), frappe.PermissionError)


def _deny_unless(flag):
	def conditions(user=None, _flag=flag):
		if can_see(_flag, user):
			return ""
		return "1=0"

	return conditions


HOOK_HAS_PERMISSION = {
	doctype: "hrms.hr.role_access.has_listed_permission" for doctype in DOCTYPE_FLAGS
}
HOOK_HAS_PERMISSION["Employee"] = "hrms.hr.role_access.has_employee_permission"

HOOK_QUERY_CONDITIONS = {"Employee": "hrms.hr.role_access.employee_permission_query"}
for _doctype, _flag in DOCTYPE_FLAGS.items():
	_fn_name = f"query_{_flag}"
	if _fn_name not in globals():
		globals()[_fn_name] = _deny_unless(_flag)
	HOOK_QUERY_CONDITIONS[_doctype] = f"hrms.hr.role_access.{_fn_name}"
