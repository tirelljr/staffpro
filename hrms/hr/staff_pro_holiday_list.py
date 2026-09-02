# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Ship a default, editable Staff Pro Holiday List on every site."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import get_first_day, get_last_day, getdate

DEFAULT_HOLIDAY_LIST = "Staff Pro Holiday List"


def ensure_staff_pro_holiday_list(company: str | None = None) -> str | None:
	"""Create the default holiday list if missing and assign it to companies.

	The list is seeded once (Sundays + Belize public holidays) and then left
	editable. Later migrate/install runs do not overwrite user changes.
	"""
	if not frappe.db.exists("DocType", "Holiday List"):
		return None

	list_name = _ensure_list_record()
	if not list_name:
		return None

	companies = [company] if company else frappe.get_all("Company", pluck="name")
	for company_name in companies:
		if company_name:
			assign_default_holiday_list_to_company(company_name)

	return list_name


def assign_default_holiday_list_to_company(doc, method=None):
	"""Point a company at the default holiday list when it has none."""
	company = doc if isinstance(doc, str) else getattr(doc, "name", None)
	if not company or not frappe.db.exists("Company", company):
		return

	list_name = _ensure_list_record()
	if not list_name:
		return

	if not frappe.db.get_value("Company", company, "default_holiday_list"):
		frappe.db.set_value("Company", company, "default_holiday_list", list_name)
		if not isinstance(doc, str) and hasattr(doc, "default_holiday_list"):
			doc.default_holiday_list = list_name

	_ensure_company_assignment(company, list_name)


def prevent_default_holiday_list_delete(doc, method=None):
	if getattr(doc, "name", None) == DEFAULT_HOLIDAY_LIST:
		frappe.throw(
			_("{0} is the default holiday calendar and cannot be deleted. Edit the holidays instead.").format(
				frappe.bold(DEFAULT_HOLIDAY_LIST)
			)
		)


def get_fallback_holiday_list(company: str | None = None, as_on=None, as_dict: bool = False):
	"""Company default, then the shipped Staff Pro list. Does not create records."""
	name = None
	if company:
		name = frappe.db.get_value("Company", company, "default_holiday_list")
	if not name and frappe.db.exists("Holiday List", DEFAULT_HOLIDAY_LIST):
		name = DEFAULT_HOLIDAY_LIST
	if not name:
		return None
	if as_dict:
		from_date = frappe.db.get_value("Holiday List", name, "from_date")
		return frappe._dict(holiday_list=name, from_date=from_date)
	return name


def _ensure_list_record() -> str | None:
	if frappe.db.exists("Holiday List", DEFAULT_HOLIDAY_LIST):
		return DEFAULT_HOLIDAY_LIST

	today = getdate()
	from_date = get_first_day(today.replace(month=1, day=1))
	to_date = get_last_day(today.replace(month=12, day=31))

	holiday_list = frappe.get_doc(
		{
			"doctype": "Holiday List",
			"holiday_list_name": DEFAULT_HOLIDAY_LIST,
			"from_date": from_date,
			"to_date": to_date,
			"weekly_off": "Sunday",
		}
	)
	holiday_list.insert(ignore_permissions=True)
	holiday_list.get_weekly_off_dates()
	holiday_list.save(ignore_permissions=True)

	from hrms.hr.belize_holidays import add_belize_holidays_to_list

	add_belize_holidays_to_list(DEFAULT_HOLIDAY_LIST, year=from_date.year)
	return DEFAULT_HOLIDAY_LIST


def _ensure_company_assignment(company: str, list_name: str) -> None:
	if not frappe.db.exists("DocType", "Holiday List Assignment"):
		return

	existing = frappe.db.exists(
		"Holiday List Assignment",
		{"applicable_for": "Company", "assigned_to": company, "holiday_list": list_name},
	)
	if existing:
		if frappe.db.get_value("Holiday List Assignment", existing, "docstatus") == 0:
			doc = frappe.get_doc("Holiday List Assignment", existing)
			doc.flags.ignore_permissions = True
			doc.submit()
		return

	from_date = frappe.db.get_value("Holiday List", list_name, "from_date") or get_first_day(getdate())
	assignment = frappe.get_doc(
		{
			"doctype": "Holiday List Assignment",
			"applicable_for": "Company",
			"assigned_to": company,
			"holiday_list": list_name,
			"from_date": from_date,
		}
	)
	assignment.flags.ignore_permissions = True
	assignment.insert(ignore_permissions=True)
	assignment.submit()
