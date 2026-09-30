# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.naming import set_name_by_naming_series
from frappe.query_builder import Interval
from frappe.query_builder.functions import Count, CurDate, UnixTimestamp
from frappe.utils import add_years, cint, get_link_to_form, getdate

from erpnext.setup.doctype.employee.employee import Employee


class EmployeeMaster(Employee):
	def validate(self):
		apply_default_approvers(self)
		super().validate()
		from hrms.hr.floor_workers import apply_employee_floor_worker_rules

		apply_employee_floor_worker_rules(self)

	def autoname(self):
		naming_method = frappe.db.get_single_value("HR Settings", "emp_created_by")
		if not naming_method:
			frappe.throw(_("Please setup Employee Naming System in Human Resource > HR Settings"))
		else:
			if naming_method == "Naming Series":
				set_name_by_naming_series(self)
			elif naming_method == "Employee Number":
				self.name = self.employee_number
			elif naming_method == "Full Name":
				self.set_employee_name()
				self.name = self.employee_name

		self.employee = self.name

	def before_delete(self):
		self._unlink_blocking_records()
		self.flags.ignore_links = True

	def on_trash(self):
		self._unlink_blocking_records()
		parent_on_trash = getattr(super(), "on_trash", None)
		if parent_on_trash:
			parent_on_trash()

	def delete(self, ignore_permissions=False, force=False, *, delete_permanently=False):
		self._unlink_blocking_records()
		self.flags.ignore_links = True
		return super().delete(
			ignore_permissions=ignore_permissions,
			force=True,
			delete_permanently=delete_permanently,
		)

	def _unlink_blocking_records(self):
		if self.flags.get("employee_unlinked") or not self.name:
			return
		self.flags.employee_unlinked = True
		from hrms.hr.employee_cleanup import unlink_employee_records

		unlink_employee_records(self.name, skip_permission=True)


def validate_onboarding_process(doc, method=None):
	"""Validates Employee Creation for linked Employee Onboarding"""
	if not doc.job_applicant:
		return

	employee_onboarding = frappe.get_all(
		"Employee Onboarding",
		filters={
			"job_applicant": doc.job_applicant,
			"docstatus": 1,
			"boarding_status": ("!=", "Completed"),
		},
	)
	if employee_onboarding:
		onboarding = frappe.get_doc("Employee Onboarding", employee_onboarding[0].name)
		onboarding.validate_employee_creation()
		onboarding.db_set("employee", doc.name)


def publish_update(doc, method=None):
	import hrms

	hrms.refetch_resource("hrms:employee", doc.user_id)


def update_job_applicant_and_offer(doc, method=None):
	"""Updates Job Applicant and Job Offer status as 'Accepted' and submits them"""
	if not doc.job_applicant:
		return

	applicant_status_before_change = frappe.db.get_value("Job Applicant", doc.job_applicant, "status")
	if applicant_status_before_change != "Accepted":
		frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Accepted")
		frappe.msgprint(
			_("Updated the status of linked Job Applicant {0} to {1}").format(
				get_link_to_form("Job Applicant", doc.job_applicant), frappe.bold(_("Accepted"))
			)
		)
	offer_status_before_change = frappe.db.get_value(
		"Job Offer", {"job_applicant": doc.job_applicant, "docstatus": ["!=", 2]}, "status"
	)
	if offer_status_before_change and offer_status_before_change != "Accepted":
		job_offer = frappe.get_last_doc("Job Offer", filters={"job_applicant": doc.job_applicant})
		job_offer.status = "Accepted"
		job_offer.flags.ignore_mandatory = True
		job_offer.flags.ignore_permissions = True
		job_offer.save()

		msg = _("Updated the status of Job Offer {0} for the linked Job Applicant {1} to {2}").format(
			get_link_to_form("Job Offer", job_offer.name),
			frappe.bold(doc.job_applicant),
			frappe.bold(_("Accepted")),
		)
		if job_offer.docstatus == 0:
			msg += "<br>" + _("You may add additional details, if any, and submit the offer.")

		frappe.msgprint(msg)


@frappe.whitelist()
def get_default_hr_approver() -> str | None:
	"""Enabled user who should approve leave and shift requests by default.

	Prefers an active employee whose designation is HR Manager. Otherwise uses
	the first enabled user with the HR Manager role.
	"""
	designated = frappe.get_all(
		"Employee",
		filters={"status": "Active", "designation": "HR Manager", "user_id": ["is", "set"]},
		pluck="user_id",
		order_by="creation asc",
	)
	for user in designated:
		if _is_usable_approver(user):
			return user

	candidates = frappe.get_all(
		"Has Role",
		filters={"role": "HR Manager", "parenttype": "User"},
		pluck="parent",
	)
	enabled = sorted({user for user in candidates if _is_usable_approver(user)})
	if enabled:
		return enabled[0]

	# Sites that have not created a separate HR user still grant the role to Administrator.
	if frappe.db.exists(
		"Has Role", {"parent": "Administrator", "parenttype": "User", "role": "HR Manager"}
	) and frappe.db.get_value("User", "Administrator", "enabled"):
		return "Administrator"
	return None


def _is_usable_approver(user: str) -> bool:
	if not user or user in ("Administrator", "Guest"):
		return False
	return bool(frappe.db.get_value("User", user, "enabled"))


def apply_default_approvers(doc, method=None):
	"""Fill a blank leave or shift approver with the HR manager."""
	if doc.get("leave_approver") and doc.get("shift_request_approver"):
		return
	approver = get_default_hr_approver()
	if not approver:
		return
	if not doc.get("leave_approver"):
		doc.leave_approver = approver
	if not doc.get("shift_request_approver"):
		doc.shift_request_approver = approver


def update_approver_role(doc, method=None):
	"""Adds relevant approver role for the user linked to Employee"""
	if doc.leave_approver:
		user = frappe.get_doc("User", doc.leave_approver)
		user.flags.ignore_permissions = True
		user.add_roles("Leave Approver")

	if doc.expense_approver:
		user = frappe.get_doc("User", doc.expense_approver)
		user.flags.ignore_permissions = True
		user.add_roles("Expense Approver")


def update_approver_user_roles(doc, method=None):
	approver_roles = set()
	if frappe.db.exists("Employee", {"leave_approver": doc.name}):
		approver_roles.add("Leave Approver")

	if frappe.db.exists("Employee", {"expense_approver": doc.name}):
		approver_roles.add("Expense Approver")

	if approver_roles:
		doc.append_roles(*approver_roles)


def update_employee_transfer(doc, method=None):
	"""Unsets Employee ID in Employee Transfer if doc is deleted"""
	if frappe.db.exists("Employee Transfer", {"new_employee_id": doc.name, "docstatus": 1}):
		emp_transfer = frappe.get_doc("Employee Transfer", {"new_employee_id": doc.name, "docstatus": 1})
		emp_transfer.db_set("new_employee_id", "")


@frappe.whitelist()
def get_timeline_data(doctype: str, name: str) -> dict:
	"""Return timeline for attendance"""
	from frappe.desk.notifications import get_open_count

	out = {}

	frappe.has_permission(doctype, "read", name, throw=True)
	frappe.has_permission("Attendance", "read", throw=True)

	open_count = get_open_count(doctype, name)
	out["count"] = open_count["count"]

	Attendance = frappe.qb.DocType("Attendance")

	timeline_data = dict(
		(
			frappe.qb.from_(Attendance)
			.select(
				UnixTimestamp(Attendance.attendance_date),
				Count("*"),
			)
			.where(
				(Attendance.employee == name)
				& (Attendance.docstatus == 1)
				& (Attendance.attendance_date > (CurDate() - Interval(years=1)))
				& (Attendance.status.isin(["Present", "Half Day"]))
			)
			.groupby(Attendance.attendance_date)
		).run()
	)

	out["timeline_data"] = timeline_data
	return out


@frappe.whitelist()
def get_assignable_masters(company: str) -> dict[str, bool]:
	"""Return whether a submitted master exists for each gated Employee assignment action"""
	masters = {
		"Leave Policy": {"docstatus": 1},
		"Salary Structure": {"docstatus": 1, "is_active": "Yes", "company": company},
		"Shift Schedule": {"docstatus": 1},
	}

	return {
		doctype: bool(frappe.get_list(doctype, filters=filters, limit=1, pluck="name"))
		for doctype, filters in masters.items()
	}


def suggest_username(first_name: str | None = None, last_name: str | None = None, existing: str | None = None) -> str:
	"""Build a short login username like TArzu from first + last name."""
	first = "".join(ch for ch in (first_name or "") if ch.isalnum())
	last = "".join(ch for ch in (last_name or "") if ch.isalnum())
	if first and last:
		base = f"{first[0]}{last}"
	else:
		base = first or last or (existing or "user")
	base = "".join(ch for ch in base if ch.isalnum()) or "user"
	return base[:140]


def unique_username(base: str, ignore_user: str | None = None) -> str:
	candidate = (base or "user").strip() or "user"
	suffix = 0
	while True:
		name = candidate if not suffix else f"{candidate}{suffix}"
		if ignore_user and (
			ignore_user == name or frappe.db.get_value("User", ignore_user, "username") == name
		):
			return name
		taken_name = frappe.db.exists("User", name) and name != ignore_user
		taken_username = frappe.db.exists("User", {"username": name, "name": ("!=", ignore_user or "")})
		if not taken_name and not taken_username:
			return name
		suffix += 1


def resolve_user_from_login(login: str | None) -> str | None:
	"""Resolve a username, email, or full name to the User document name."""
	value = (login or "").strip()
	if not value:
		return None
	if frappe.db.exists("User", value):
		return value
	by_username = frappe.db.get_value("User", {"username": value}, "name")
	if by_username:
		return by_username
	by_full_name = frappe.db.get_value("User", {"full_name": value}, "name")
	if by_full_name:
		return by_full_name
	rows = frappe.db.sql(
		"""
		select name from `tabUser`
		where enabled = 1
		  and (
			lower(ifnull(username, '')) = %(login)s
			or lower(ifnull(full_name, '')) = %(login)s
		  )
		limit 1
		""",
		{"login": value.lower()},
	)
	return rows[0][0] if rows else None


LOCAL_LOGIN_DOMAIN = "users.staffpro.local"


def local_login_email(username: str) -> str:
	return f"{username.lower()}@{LOCAL_LOGIN_DOMAIN}"


def prepare_user_login(doc, method=None):
	"""New desk users are created from a username. The User id stays an internal address."""
	if not doc.is_new() or doc.name in {"Administrator", "Guest"}:
		return

	email = (doc.email or "").strip()
	username = (doc.username or "").strip()
	if email and "@" not in email:
		login = clean_username(email)
		doc.username = login
		doc.email = local_login_email(login)
		doc.send_welcome_email = 0
		return

	if not username or "@" in username:
		return
	if email and not email.lower().endswith(f"@{LOCAL_LOGIN_DOMAIN}"):
		return

	login = clean_username(username)
	doc.username = login
	doc.email = local_login_email(login)
	doc.send_welcome_email = 0


def _selected_role_names(roles) -> list[str]:
	if isinstance(roles, str):
		roles = frappe.parse_json(roles)
	names = []
	for row in roles or []:
		if isinstance(row, dict):
			role = row.get("role") or row.get("name")
		else:
			role = row
		role = (role or "").strip()
		if role and role not in names:
			names.append(role)
	return names


def _can_assign_user_roles() -> bool:
	permlevel = frappe.get_meta("User").get_field("roles").permlevel or 0
	user_roles = set(frappe.get_roles())
	for perm in frappe.get_meta("User").permissions:
		if perm.role in user_roles and cint(perm.permlevel) == permlevel and cint(perm.write):
			return True
	return False


@frappe.whitelist()
def create_user_login(
	username: str,
	first_name: str | None = None,
	roles: str | list | None = None,
	last_name: str | None = None,
	new_password: str | None = None,
) -> dict:
	"""Create a desk user from a username, password, and Role records."""
	frappe.has_permission("User", "create", throw=True)
	login = clean_username(username)
	if frappe.db.exists("User", {"username": login}) or frappe.db.exists("User", local_login_email(login)):
		frappe.throw(_("Username {0} is already taken.").format(frappe.bold(login)))

	chosen = _selected_role_names(roles)
	missing = [role for role in chosen if not frappe.db.exists("Role", role)]
	if missing:
		frappe.throw(_("Role {0} was not found.").format(frappe.bold(missing[0])))
	if chosen and not _can_assign_user_roles():
		frappe.throw(_("You do not have permission to assign roles."), frappe.PermissionError)

	password = _checked_password(new_password)
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": local_login_email(login),
			"username": login,
			"first_name": (first_name or login).strip(),
			"last_name": (last_name or "").strip(),
			"send_welcome_email": 0,
			"enabled": 1,
			"user_type": "System User",
			"roles": [{"doctype": "Has Role", "role": role} for role in chosen],
		}
	)
	user.flags.ignore_password_policy = True
	user.insert()
	_store_login_password(user.name, password)
	return user.as_dict()


@frappe.whitelist()
def get_user_password(user: str) -> dict:
	"""Return the saved login password for an admin. Empty until a password is set here or the user signs in."""
	login = _password_target(user)
	frappe.has_permission("User", "read", login, throw=True)
	_require_password_admin()
	from hrms.overrides.employee_profile import read_viewable_password

	return {"password": read_viewable_password(login), "user": login}


@frappe.whitelist()
def set_user_password(user: str, new_password: str, logout_all_sessions: int = 0) -> dict:
	"""Set a desk user's login password without emailing a reset link."""
	login = _password_target(user)
	frappe.has_permission("User", "write", login, throw=True)
	_require_password_admin()
	password = _checked_password(new_password)
	_store_login_password(login, password, logout_all_sessions=cint(logout_all_sessions))
	return {"ok": True, "user": login}


def _password_target(user: str) -> str:
	login = (user or "").strip()
	if login in {"", "Administrator", "Guest"} or not frappe.db.exists("User", login):
		frappe.throw(_("User {0} was not found.").format(frappe.bold(login or _("Unknown"))))
	return login


def _require_password_admin() -> None:
	from hrms.overrides.employee_profile import PASSWORD_ROLES

	if not set(frappe.get_roles()).intersection(PASSWORD_ROLES):
		frappe.throw(_("Not permitted to change this password."), frappe.PermissionError)


def _checked_password(new_password: str | None) -> str:
	password = new_password or ""
	if len(password) < 8:
		frappe.throw(_("Password must be at least 8 characters."))
	return password


def _store_login_password(user: str, password: str, logout_all_sessions: int = 0) -> None:
	from frappe.utils import today
	from frappe.utils.password import update_password

	from hrms.overrides.employee_profile import remember_viewable_password

	update_password(user, password, logout_all_sessions=cint(logout_all_sessions))
	remember_viewable_password(user, password)
	if frappe.get_meta("User").has_field("last_password_reset_date"):
		frappe.db.set_value("User", user, "last_password_reset_date", today(), update_modified=False)


def clean_username(value: str | None) -> str:
	typed = (value or "").strip()
	if not typed:
		frappe.throw(_("Enter a username."))
	if "@" in typed:
		frappe.throw(_("Use a username, not an email address."))
	cleaned = "".join(ch for ch in typed if ch.isalnum() or ch in "._-")
	if not cleaned:
		frappe.throw(_("Enter a valid username."))
	return cleaned[:140]


def _previous_user_id(doc) -> str | None:
	before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
	if before and before.user_id:
		return before.user_id
	if doc.name and not doc.is_new() and frappe.db.exists("Employee", doc.name):
		return frappe.db.get_value("Employee", doc.name, "user_id")
	return None


def _ensure_username(user_name: str, employee) -> None:
	if frappe.db.get_value("User", user_name, "username"):
		return
	suggested = unique_username(
		suggest_username(employee.first_name, employee.last_name, user_name),
		user_name,
	)
	frappe.db.set_value("User", user_name, "username", suggested, update_modified=False)


def _create_user_for_employee(employee, login: str) -> str:
	user_email = (employee.company_email or employee.personal_email or "").strip()
	if not user_email:
		user_email = local_login_email(login)
	existing = frappe.db.get_value("User", {"email": user_email}, "name")
	if existing:
		_apply_username_to_user(existing, login)
		from hrms.hr.bpo_user_permissions import is_agent_account

		if is_agent_account(existing):
			frappe.db.set_value("User", existing, "user_type", "Website User", update_modified=False)
		return existing

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": user_email,
			"first_name": employee.first_name or employee.employee_name or login,
			"last_name": employee.last_name,
			"username": login,
			"send_welcome_email": 0,
			"enabled": 1,
			"user_type": "Website User",
		}
	)
	user.flags.ignore_permissions = True
	user.insert()
	roles = ["Employee"]
	if frappe.db.exists("Role", "Employee Self Service"):
		roles.append("Employee Self Service")
	user.add_roles(*roles)
	frappe.db.set_value("User", user.name, "user_type", "Website User", update_modified=False)
	return user.name


def _apply_username_to_user(user_name: str, login: str) -> str:
	taken = frappe.db.get_value("User", {"username": login, "name": ("!=", user_name)}, "name")
	if taken:
		frappe.throw(_("Username {0} is already taken.").format(frappe.bold(login)))

	user = frappe.get_doc("User", user_name)
	user.username = login
	user.flags.ignore_permissions = True
	user.save()
	return user.name


def _login_username(user_name: str | None) -> str:
	if not user_name:
		return ""
	username = frappe.db.get_value("User", user_name, "username") or ""
	if username and "@" not in username:
		return username
	if "@" not in user_name:
		return user_name
	return ""


def sync_employee_username(doc, method=None):
	"""Keep Employee.user_id as the User email and store the typed login on User.username."""
	typed = (doc.user_id or "").strip()
	if not typed:
		return

	previous = _previous_user_id(doc)
	if previous and typed == previous:
		if frappe.db.exists("User", previous):
			_ensure_username(previous, doc)
		return

	previous_username = _login_username(previous) if previous else ""
	if previous and typed == previous_username:
		doc.user_id = previous
		return

	if "@" in typed:
		if frappe.db.exists("User", typed):
			doc.user_id = typed
			_ensure_username(typed, doc)
			return
		if previous and frappe.db.exists("User", previous):
			doc.user_id = previous
			return
		frappe.throw(_("Use a username, not an email address."))

	login = clean_username(typed)
	if previous and frappe.db.exists("User", previous):
		_apply_username_to_user(previous, login)
		doc.user_id = previous
		return

	resolved = resolve_user_from_login(login)
	if resolved:
		doc.user_id = resolved
		_ensure_username(resolved, doc)
		return

	doc.user_id = _create_user_for_employee(doc, login)


@frappe.whitelist()
def get_employee_login_username(employee: str) -> dict:
	frappe.has_permission("Employee", "read", employee, throw=True)
	user = frappe.db.get_value("Employee", employee, "user_id") or ""
	return {"user": user, "username": _login_username(user)}


@frappe.whitelist()
def set_employee_username(employee: str, username: str) -> dict:
	"""Apply a typed username to the linked User. Employee.user_id stays the User email."""
	frappe.has_permission("Employee", "write", employee, throw=True)
	emp = frappe.get_doc("Employee", employee)
	emp.user_id = username
	sync_employee_username(emp)
	emp.db_set("user_id", emp.user_id)
	return {"user": emp.user_id, "username": _login_username(emp.user_id) or clean_username(username)}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def user_username_query(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: str | dict | None = None,
):
	"""Link search that prefers username over email."""
	txt = f"%{txt or ''}%"
	return frappe.db.sql(
		"""
		select name, ifnull(nullif(username, ''), name), ifnull(full_name, '')
		from `tabUser`
		where enabled = 1
			and name not in ('Guest', 'Administrator')
			and user_type in ('System User', 'Website User')
			and (
				name like %(txt)s
				or ifnull(username, '') like %(txt)s
				or ifnull(full_name, '') like %(txt)s
				or ifnull(email, '') like %(txt)s
			)
		order by
			(case when ifnull(username, '') like %(txt)s then 0 else 1 end),
			username, name
		limit %(start)s, %(page_len)s
		""",
		{"txt": txt, "start": start, "page_len": page_len},
	)


@frappe.whitelist()
def create_employee_username_user(employee: str, username: str | None = None, email: str | None = None) -> dict:
	"""Create or rename the linked User so the employee logs in with a username."""
	frappe.has_permission("Employee", "write", employee, throw=True)
	emp = frappe.get_doc("Employee", employee)
	if emp.status and emp.status != "Active":
		frappe.throw(_("Username can only be created for an Active employee."))

	if email:
		emp.company_email = emp.company_email or email
	login = unique_username(
		(username or "").strip() or suggest_username(emp.first_name, emp.last_name, emp.name),
		emp.user_id,
	)
	emp.user_id = login
	sync_employee_username(emp)
	emp.db_set("user_id", emp.user_id)
	return {"user": emp.user_id, "username": _login_username(emp.user_id) or login, "created": True}


def ensure_td4_request_for_account(doc, method=None):
	"""Open a TD4 request when an agent gets a portal login, so sign-in can prompt them."""
	if not doc or not getattr(doc, "name", None):
		return
	if getattr(doc, "status", None) != "Active":
		return
	user_id = (getattr(doc, "user_id", None) or "").strip()
	if not user_id or user_id in ("Guest", "Administrator"):
		return
	if not frappe.db.table_exists("TD4 Form"):
		return
	try:
		from hrms.hr.doctype.td4_form.td4_form import create_requested, has_submitted, pending_name

		if has_submitted(doc.name) or pending_name(doc.name):
			return
		create_requested(doc.name, notify=False)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "TD4 request for new agent")


@frappe.whitelist()
def get_retirement_date(date_of_birth: str | None = None):
	if date_of_birth:
		try:
			retirement_age = cint(frappe.db.get_single_value("HR Settings", "retirement_age") or 60)
			dt = add_years(getdate(date_of_birth), retirement_age)
			return dt.strftime("%Y-%m-%d")
		except ValueError:
			# invalid date
			return
