# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Drop settings/payment shortcuts duplicated outside Admin."""

import frappe

from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars


def execute():
	sync_staff_pro_sidebars()
	frappe.db.commit()
