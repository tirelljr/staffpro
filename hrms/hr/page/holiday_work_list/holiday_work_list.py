# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe

from hrms.hr.doctype.holiday_work_election.holiday_work_election import (
	get_company_upcoming_holidays,
	get_holiday_work_roster,
)

HR_ROLES = ("HR Manager", "HR User", "System Manager", "Administrator")


def _assert_hr():
	frappe.only_for(list(HR_ROLES))


@frappe.whitelist()
def get_upcoming_holidays() -> list[dict]:
	_assert_hr()
	return get_company_upcoming_holidays()


@frappe.whitelist()
def get_holiday_work_list(holiday_date: str | None = None, department: str | None = None) -> dict:
	_assert_hr()
	if not holiday_date:
		frappe.throw(frappe._("Holiday Date is required."))
	return get_holiday_work_roster(holiday_date, department)
