# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Agents stay Website Users with no desk access."""


def execute():
	from hrms.hr.bpo_user_permissions import apply_bpo_user_permissions

	apply_bpo_user_permissions()
