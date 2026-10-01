# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Add role access switches and hide unused Role fields."""


def execute():
	from hrms.hr.role_access import ensure_role_access_fields

	ensure_role_access_fields()
