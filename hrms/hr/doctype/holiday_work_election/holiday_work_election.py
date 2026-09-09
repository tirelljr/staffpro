# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate, strip_html

from hrms.utils.holiday_list import get_holiday_list_for_employee

HR_ROLES = frozenset({"HR User", "HR Manager", "System Manager", "Administrator"})


class HolidayWorkElection(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		employee: DF.Link
		employee_name: DF.Data | None
		holiday_date: DF.Date
		holiday_description: DF.Data | None
		will_work: DF.Check
	# end: auto-generated types

	def validate(self):
		self.holiday_date = getdate(self.holiday_date)
		if not self.employee_name:
			self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")
		assert_can_set_election(self.employee)
		context = get_holiday_work_context(self.employee, self.holiday_date)
		if not context["is_public"]:
			frappe.throw(_("This date is not a public holiday."))
		if not context["is_work_day"]:
			frappe.throw(_("You can only elect to work when the holiday falls on a work day."))
		if context["is_past"]:
			frappe.throw(_("You cannot change an election for a past holiday."))
		if not self.holiday_description:
			self.holiday_description = context["description"]
		self._ensure_unique()

	def _ensure_unique(self):
		filters = {"employee": self.employee, "holiday_date": self.holiday_date}
		if not self.is_new():
			filters["name"] = ["!=", self.name]
		if frappe.db.exists("Holiday Work Election", filters):
			frappe.throw(_("An election already exists for this holiday."))


def is_hr_user(user: str | None = None) -> bool:
	return bool(HR_ROLES.intersection(frappe.get_roles(user or frappe.session.user)))


def get_session_employee() -> str | None:
	from hrms.api import get_current_employee_info

	info = get_current_employee_info()
	return info.get("name") if info else None


def assert_can_access_employee_holidays(employee: str) -> None:
	if is_hr_user():
		return
	if get_session_employee() == employee:
		return
	frappe.throw(_("Not permitted"), frappe.PermissionError)


def assert_can_set_election(employee: str) -> None:
	assert_can_access_employee_holidays(employee)


def get_permission_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_hr_user(user):
		return ""
	employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	if not employee:
		return "1=0"
	return f"`tabHoliday Work Election`.employee = {frappe.db.escape(employee)}"


def has_permission(doc, ptype=None, user=None, debug=False) -> bool:
	user = user or frappe.session.user
	if is_hr_user(user):
		return True
	employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	return bool(employee and doc.employee == employee)


def get_holiday_work_context(employee: str, holiday_date) -> dict:
	holiday_date = getdate(holiday_date)
	today = getdate()
	holiday_list = get_holiday_list_for_employee(employee, raise_exception=False, as_on=holiday_date)
	if not holiday_list:
		return {
			"holiday_list": None,
			"is_public": False,
			"is_weekly_off": False,
			"is_work_day": False,
			"is_past": holiday_date < today,
			"description": "",
		}

	rows = frappe.get_all(
		"Holiday",
		filters={"parent": holiday_list, "holiday_date": holiday_date},
		fields=["description", "weekly_off"],
		ignore_permissions=True,
	)
	is_public = False
	is_weekly_off = False
	description = ""
	for row in rows:
		if cint(row.weekly_off):
			is_weekly_off = True
		else:
			is_public = True
			description = strip_html(row.description or "").strip()

	return {
		"holiday_list": holiday_list,
		"is_public": is_public,
		"is_weekly_off": is_weekly_off,
		"is_work_day": is_public and not is_weekly_off,
		"is_past": holiday_date < today,
		"description": description,
	}


def get_elections_map(employee: str, dates: list) -> dict:
	if not dates:
		return {}
	rows = frappe.get_all(
		"Holiday Work Election",
		filters={"employee": employee, "holiday_date": ["in", dates]},
		fields=["holiday_date", "will_work"],
		ignore_permissions=True,
	)
	return {getdate(row.holiday_date): cint(row.will_work) for row in rows}


def get_upcoming_holidays_for_employee(employee: str) -> list[dict]:
	today = getdate()
	holiday_list = get_holiday_list_for_employee(employee, raise_exception=False, as_on=today)
	if not holiday_list:
		return []

	Holiday = frappe.qb.DocType("Holiday")
	public = (
		frappe.qb.from_(Holiday)
		.select(Holiday.name, Holiday.holiday_date, Holiday.description)
		.where(
			(Holiday.parent == holiday_list)
			& (Holiday.weekly_off == 0)
			& (Holiday.holiday_date >= today)
		)
		.orderby(Holiday.holiday_date)
	).run(as_dict=True)

	if not public:
		return []

	dates = [getdate(row.holiday_date) for row in public]
	weekly_off_dates = set(
		frappe.get_all(
			"Holiday",
			filters={"parent": holiday_list, "weekly_off": 1, "holiday_date": ["in", dates]},
			pluck="holiday_date",
			ignore_permissions=True,
		)
	)
	weekly_off_dates = {getdate(d) for d in weekly_off_dates}
	elections = get_elections_map(employee, dates)

	result = []
	for row in public:
		holiday_date = getdate(row.holiday_date)
		is_work_day = holiday_date not in weekly_off_dates
		is_past = holiday_date < today
		result.append(
			{
				"name": row.name,
				"holiday_date": str(holiday_date),
				"description": strip_html(row.description or "").strip(),
				"will_work": bool(elections.get(holiday_date)),
				"is_work_day": is_work_day,
				"can_toggle": is_work_day and not is_past,
			}
		)
	return result


def set_holiday_work_election(employee: str, holiday_date, will_work) -> dict:
	assert_can_set_election(employee)
	holiday_date = getdate(holiday_date)
	will_work = cint(will_work)
	context = get_holiday_work_context(employee, holiday_date)
	if not context["is_public"]:
		frappe.throw(_("This date is not a public holiday."))
	if not context["is_work_day"]:
		frappe.throw(_("You can only elect to work when the holiday falls on a work day."))
	if context["is_past"]:
		frappe.throw(_("You cannot change an election for a past holiday."))

	existing = frappe.db.exists(
		"Holiday Work Election",
		{"employee": employee, "holiday_date": holiday_date},
	)
	if existing:
		doc = frappe.get_doc("Holiday Work Election", existing)
		doc.will_work = will_work
		doc.flags.ignore_permissions = True
		doc.save()
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Holiday Work Election",
				"employee": employee,
				"holiday_date": holiday_date,
				"holiday_description": context["description"],
				"will_work": will_work,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()

	return {
		"name": doc.name,
		"employee": employee,
		"holiday_date": str(holiday_date),
		"will_work": bool(cint(doc.will_work)),
	}


def get_active_employees(on_date=None) -> list[dict]:
	on_date = getdate(on_date)
	employees = frappe.get_all(
		"Employee",
		fields=["name", "employee_name", "department", "company", "image", "date_of_joining", "relieving_date"],
		filters={"status": "Active"},
		order_by="employee_name",
	)
	active = []
	for row in employees:
		if row.date_of_joining and getdate(row.date_of_joining) > on_date:
			continue
		if row.relieving_date and getdate(row.relieving_date) < on_date:
			continue
		active.append(row)
	return active


def _employee_holiday_lists(employees: list[dict], on_date) -> dict[str, str | None]:
	on_date = getdate(on_date)
	mapping = {}
	for row in employees:
		mapping[row.name] = get_holiday_list_for_employee(row.name, raise_exception=False, as_on=on_date)
	return mapping


def _holidays_by_list(holiday_lists: set[str], from_date) -> tuple[dict, dict]:
	if not holiday_lists:
		return {}, {}

	public_rows = frappe.get_all(
		"Holiday",
		filters={"parent": ["in", list(holiday_lists)], "weekly_off": 0, "holiday_date": [">=", from_date]},
		fields=["parent", "holiday_date", "description"],
		ignore_permissions=True,
	)
	weekly_rows = frappe.get_all(
		"Holiday",
		filters={"parent": ["in", list(holiday_lists)], "weekly_off": 1, "holiday_date": [">=", from_date]},
		fields=["parent", "holiday_date"],
		ignore_permissions=True,
	)

	public = defaultdict(dict)
	for row in public_rows:
		public[row.parent][getdate(row.holiday_date)] = strip_html(row.description or "").strip()

	weekly = defaultdict(set)
	for row in weekly_rows:
		weekly[row.parent].add(getdate(row.holiday_date))

	return public, weekly


def get_company_upcoming_holidays() -> list[dict]:
	today = getdate()
	employees = get_active_employees(today)
	list_map = _employee_holiday_lists(employees, today)
	public, weekly = _holidays_by_list({name for name in list_map.values() if name}, today)

	eligible_by_date: dict = defaultdict(set)
	descriptions: dict = {}
	for employee in employees:
		holiday_list = list_map.get(employee.name)
		if not holiday_list:
			continue
		for holiday_date, description in public.get(holiday_list, {}).items():
			if holiday_date in weekly.get(holiday_list, set()):
				continue
			eligible_by_date[holiday_date].add(employee.name)
			descriptions.setdefault(holiday_date, description)

	if not eligible_by_date:
		return []

	dates = list(eligible_by_date)
	elections = frappe.get_all(
		"Holiday Work Election",
		filters={"holiday_date": ["in", dates], "will_work": 1},
		fields=["employee", "holiday_date"],
		ignore_permissions=True,
	)
	working_by_date: dict = defaultdict(set)
	for row in elections:
		holiday_date = getdate(row.holiday_date)
		if row.employee in eligible_by_date.get(holiday_date, set()):
			working_by_date[holiday_date].add(row.employee)

	holidays = []
	for holiday_date in sorted(eligible_by_date):
		working = len(working_by_date.get(holiday_date, set()))
		eligible = len(eligible_by_date[holiday_date])
		holidays.append(
			{
				"holiday_date": str(holiday_date),
				"description": descriptions.get(holiday_date) or _("Public Holiday"),
				"working_count": working,
				"not_working_count": max(eligible - working, 0),
			}
		)
	return holidays


def get_holiday_work_roster(holiday_date, department: str | None = None) -> dict:
	holiday_date = getdate(holiday_date)
	employees = get_active_employees(holiday_date)
	departments = sorted({row.department for row in employees if row.department})
	list_map = _employee_holiday_lists(employees, holiday_date)
	public, weekly = _holidays_by_list({name for name in list_map.values() if name}, holiday_date)

	elections = {
		row.employee: cint(row.will_work)
		for row in frappe.get_all(
			"Holiday Work Election",
			filters={"holiday_date": holiday_date},
			fields=["employee", "will_work"],
			ignore_permissions=True,
		)
	}

	description = ""
	details = []
	for employee in employees:
		if department == "__none__" and employee.department:
			continue
		if department and department != "__none__" and employee.department != department:
			continue

		holiday_list = list_map.get(employee.name)
		if not holiday_list:
			continue
		if holiday_date not in public.get(holiday_list, {}):
			continue
		if holiday_date in weekly.get(holiday_list, set()):
			continue

		if not description:
			description = public[holiday_list][holiday_date]

		will_work = bool(elections.get(employee.name))
		details.append(
			{
				"employee": employee.name,
				"employee_name": employee.employee_name,
				"department": employee.department,
				"image": employee.image,
				"will_work": will_work,
				"status": "Working" if will_work else "Not Working",
			}
		)

	return {
		"holiday_date": str(holiday_date),
		"description": description or _("Public Holiday"),
		"departments": departments,
		"details": details,
		"working_count": sum(1 for row in details if row["will_work"]),
		"not_working_count": sum(1 for row in details if not row["will_work"]),
	}
