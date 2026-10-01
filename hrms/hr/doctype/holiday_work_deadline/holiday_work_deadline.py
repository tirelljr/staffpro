# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate

HR_ROLES = ("HR User", "HR Manager", "System Manager", "Administrator")


class HolidayWorkDeadline(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.Data | None
		holiday_date: DF.Date
		response_deadline: DF.Datetime
	# end: auto-generated types

	def validate(self):
		self.holiday_date = getdate(self.holiday_date)
		self.response_deadline = get_datetime(self.response_deadline)
		if not self.response_deadline:
			frappe.throw(_("Notification deadline is required."))
		if getdate(self.response_deadline) > self.holiday_date:
			frappe.throw(_("The notification deadline must be on or before the holiday."))


def _assert_hr():
	frappe.only_for(list(HR_ROLES))


def set_holiday_work_deadline(holiday_date, response_deadline=None, description: str | None = None) -> dict:
	_assert_hr()
	holiday_date = getdate(holiday_date)
	existing = frappe.db.exists("Holiday Work Deadline", {"holiday_date": holiday_date})
	deadline_value = str(response_deadline or "").strip()
	if not deadline_value:
		if existing:
			frappe.delete_doc("Holiday Work Deadline", existing, ignore_permissions=True)
		return {"holiday_date": str(holiday_date), "response_deadline": None}

	if existing:
		doc = frappe.get_doc("Holiday Work Deadline", existing)
	else:
		doc = frappe.new_doc("Holiday Work Deadline")
		doc.holiday_date = holiday_date

	doc.response_deadline = get_datetime(deadline_value.replace("T", " "))
	if description:
		doc.description = description
	elif not doc.description:
		doc.description = _("Public Holiday")
	doc.flags.ignore_permissions = True
	doc.save()

	return {
		"holiday_date": str(holiday_date),
		"response_deadline": str(doc.response_deadline),
		"description": doc.description,
	}


def apply_default_working_after_deadline() -> int:
	"""Count non-responders as working once a holiday's notification deadline has passed."""
	if not frappe.db.table_exists("Holiday Work Deadline"):
		return 0

	from hrms.hr.doctype.holiday_work_election.holiday_work_election import deadline_has_passed

	today = getdate()
	rows = frappe.get_all(
		"Holiday Work Deadline",
		filters={"holiday_date": [">=", today]},
		fields=["holiday_date", "description", "response_deadline"],
		ignore_permissions=True,
	)
	created = 0
	for row in rows:
		if not deadline_has_passed(row.response_deadline):
			continue
		created += _assign_default_working(row.holiday_date)
	return created


def _assign_default_working(holiday_date) -> int:
	from hrms.hr.doctype.holiday_work_election.holiday_work_election import (
		_employee_holiday_lists,
		_holidays_by_list,
		get_active_employees,
		set_holiday_work_election,
	)

	holiday_date = getdate(holiday_date)
	employees = get_active_employees(holiday_date)
	list_map = _employee_holiday_lists(employees, holiday_date)
	public, weekly = _holidays_by_list({name for name in list_map.values() if name}, holiday_date)
	existing = set(
		frappe.get_all(
			"Holiday Work Election",
			filters={"holiday_date": holiday_date},
			pluck="employee",
			ignore_permissions=True,
		)
	)

	created = 0
	for employee in employees:
		if employee.name in existing:
			continue
		holiday_list = list_map.get(employee.name)
		if not holiday_list:
			continue
		if holiday_date not in public.get(holiday_list, {}):
			continue
		if holiday_date in weekly.get(holiday_list, set()):
			continue
		set_holiday_work_election(
			employee.name,
			holiday_date,
			1,
			skip_permission=True,
			skip_deadline=True,
		)
		created += 1
	return created
