# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Move Filesystem from the Talent menu onto its own dock item under Talent."""

import frappe

from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars


def execute():
	try:
		sync_staff_pro_sidebars()
	except Exception:
		frappe.log_error(title="Filesystem dock sync")
