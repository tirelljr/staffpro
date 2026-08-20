# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Belize public holiday dates for Holiday List seeding."""

from __future__ import annotations

from datetime import date, timedelta

import frappe
from frappe.utils import getdate


def easter_sunday(year: int) -> date:
	"""Western (Gregorian) Easter Sunday — Anonymous Gregorian algorithm."""
	a = year % 19
	b = year // 100
	c = year % 100
	d = b // 4
	e = b % 4
	f = (b + 8) // 25
	g = (b - f + 1) // 3
	h = (19 * a + b - d - g + 15) % 30
	i = c // 4
	k = c % 4
	l = (32 + 2 * e + 2 * i - h - k) % 7
	m = (a + 11 * h + 22 * l) // 451
	month = (h + l - 7 * m + 114) // 31
	day = ((h + l - 7 * m + 114) % 31) + 1
	return date(year, month, day)


def get_belize_holidays(year: int | None = None) -> list[dict]:
	"""Return Belize public holidays for a calendar year as `{holiday_date, description}`."""
	year = int(year or getdate().year)
	easter = easter_sunday(year)
	rows = [
		{"holiday_date": date(year, 1, 1), "description": "New Year's Day"},
		{"holiday_date": date(year, 1, 15), "description": "George Price Day"},
		{"holiday_date": date(year, 3, 9), "description": "National Heroes and Benefactors Day"},
		{"holiday_date": easter - timedelta(days=2), "description": "Good Friday"},
		{"holiday_date": easter - timedelta(days=1), "description": "Holy Saturday"},
		{"holiday_date": easter + timedelta(days=1), "description": "Easter Monday"},
		{"holiday_date": date(year, 5, 1), "description": "Labour Day"},
		{"holiday_date": date(year, 8, 1), "description": "Emancipation Day"},
		{"holiday_date": date(year, 9, 10), "description": "St. George's Caye Day"},
		{"holiday_date": date(year, 9, 21), "description": "Independence Day"},
		{"holiday_date": date(year, 10, 12), "description": "Indigenous People's Resistance Day"},
		{"holiday_date": date(year, 11, 19), "description": "Garifuna Settlement Day"},
		{"holiday_date": date(year, 12, 25), "description": "Christmas Day"},
		{"holiday_date": date(year, 12, 26), "description": "Boxing Day"},
	]
	return rows


def add_belize_holidays_to_list(holiday_list: str, year: int | None = None) -> int:
	"""Append missing Belize public holidays to a Holiday List. Returns count added."""
	if not holiday_list or not frappe.db.exists("Holiday List", holiday_list):
		return 0

	doc = frappe.get_doc("Holiday List", holiday_list)
	year = int(year or getdate(doc.from_date).year)
	existing = {getdate(row.holiday_date) for row in doc.holidays}
	added = 0
	for row in get_belize_holidays(year):
		holiday_date = getdate(row["holiday_date"])
		if holiday_date < getdate(doc.from_date) or holiday_date > getdate(doc.to_date):
			continue
		if holiday_date in existing:
			continue
		doc.append(
			"holidays",
			{
				"holiday_date": holiday_date,
				"description": row["description"],
				"weekly_off": 0,
			},
		)
		existing.add(holiday_date)
		added += 1

	if added:
		doc.save(ignore_permissions=True)
	return added


@frappe.whitelist()
def get_belize_holidays_for_list(holiday_list: str | None = None) -> dict:
	"""Whitelisted: add Belize holidays to the given Holiday List for its from_date year."""
	frappe.has_permission("Holiday List", "write", throw=True)
	name = holiday_list or frappe.form_dict.get("name")
	if not name:
		frappe.throw(frappe._("Holiday List is required."))
	added = add_belize_holidays_to_list(name)
	return {"added": added, "message": frappe._("Added {0} Belize holiday(s).").format(added)}
