# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from hrms.hr.role_access import ensure_role_access_fields, sync_all_role_switch_permissions


def execute():
	ensure_role_access_fields()
	sync_all_role_switch_permissions()
