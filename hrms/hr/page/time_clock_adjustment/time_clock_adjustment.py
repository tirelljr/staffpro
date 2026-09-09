# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

from datetime import date

import frappe

from hrms.hr.doctype.time_clock_adjustment.time_clock_adjustment import (
	HR_ROLES,
	get_time_clock_adjustments,
	review_time_clock_adjustment,
)


def _assert_hr():
	frappe.only_for(list(HR_ROLES))


@frappe.whitelist()
def get_adjustments(
	status: str | None = None,
	department: str | None = None,
	from_date: str | date | None = None,
	to_date: str | date | None = None,
) -> dict:
	_assert_hr()
	return get_time_clock_adjustments(
		status=status, department=department, from_date=from_date, to_date=to_date
	)


@frappe.whitelist()
def review_adjustment(name: str, action: str, comment: str | None = None) -> dict:
	_assert_hr()
	return review_time_clock_adjustment(name, action, comment)
