# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Floor worker fields, default schedule, and sidebar links."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import get_custom_fields

HR_DEFAULTS = {
	"floor_worker_start_time": "08:00:00",
	"floor_worker_end_time": "17:00:00",
	"floor_work_monday": 1,
	"floor_work_tuesday": 1,
	"floor_work_wednesday": 1,
	"floor_work_thursday": 1,
	"floor_work_friday": 1,
	"floor_work_saturday": 0,
	"floor_work_sunday": 0,
}


def execute():
	create_custom_fields(get_custom_fields(), ignore_validate=True)
	_set_hr_defaults()
	_backfill_working_days()
	from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars

	sync_staff_pro_sidebars()
	frappe.clear_cache(doctype="Employee")
	frappe.clear_cache(doctype="HR Settings")


def _set_hr_defaults():
	if not frappe.db.exists("DocType", "HR Settings"):
		return
	meta = frappe.get_meta("HR Settings")
	for fieldname, value in HR_DEFAULTS.items():
		if not meta.has_field(fieldname):
			continue
		current = frappe.db.get_single_value("HR Settings", fieldname)
		if current in (None, ""):
			frappe.db.set_single_value("HR Settings", fieldname, value)


def _backfill_working_days():
	if not frappe.db.has_column("Employee", "work_monday"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabEmployee`
		SET
			work_monday = IFNULL(work_monday, 1),
			work_tuesday = IFNULL(work_tuesday, 1),
			work_wednesday = IFNULL(work_wednesday, 1),
			work_thursday = IFNULL(work_thursday, 1),
			work_friday = IFNULL(work_friday, 1),
			work_saturday = IFNULL(work_saturday, 0),
			work_sunday = IFNULL(work_sunday, 0),
			is_floor_worker = IFNULL(is_floor_worker, 0)
		"""
	)
