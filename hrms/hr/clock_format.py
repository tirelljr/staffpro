# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""12-hour clock labels and work-date parsing for employee and employer portals."""

from frappe.utils import cstr, get_datetime, getdate

# Frappe System Settings only ships 24-hour presets; Desk still understands this moment format.
FRAPPE_TIME_FORMAT = "hh:mm A"
DISPLAY_CLOCK_FORMAT = "%I:%M %p"


def format_clock(value) -> str:
	"""Return a 12-hour clock such as 3:00 PM, never 15:00."""
	if not value:
		return ""
	text = get_datetime(value).strftime(DISPLAY_CLOCK_FORMAT)
	return text[1:] if text.startswith("0") else text


def parse_work_date(value=None):
	"""Site-local work date. 'today' follows System Settings timezone, not UTC."""
	text = cstr(value).strip()
	if not text or text.lower() in {"today", "todays", "now"}:
		return getdate()
	return getdate(text)
