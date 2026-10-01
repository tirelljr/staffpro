# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.hr.role_access import _ensure_role_switch_columns


def execute():
	# Only add missing columns. Full Custom Field + permission grants run on
	# boot. Doing that here holds MariaDB locks and leaves Render on 502.
	frappe.db.commit()
	_ensure_role_switch_columns()
