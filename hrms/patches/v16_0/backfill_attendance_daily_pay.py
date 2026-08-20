# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Fill hour rate, gross, SS, and tax on clock days that were stored without pay."""

import frappe
from frappe.utils import add_days, get_first_day_of_week, getdate, nowdate


def execute():
	from hrms.import_hr_demo_data import _backfill_attendance_pay, _get_company

	company = _get_company()
	if not company:
		return
	end = getdate(nowdate())
	start = add_days(get_first_day_of_week(end), -49)
	try:
		_backfill_attendance_pay(company, start, end)
	except Exception:
		frappe.log_error(title="Attendance daily pay backfill failed")
