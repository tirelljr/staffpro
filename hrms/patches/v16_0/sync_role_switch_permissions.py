# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.hr.role_access import ensure_role_access_fields, sync_all_role_switch_permissions


def execute():
	# Leave the migrate transaction before any Role ALTER / Custom Field writes.
	frappe.db.commit()
	ensure_role_access_fields()
	frappe.db.commit()
	sync_all_role_switch_permissions()
