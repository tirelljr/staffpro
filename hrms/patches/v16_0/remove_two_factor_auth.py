# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Remove two-factor authentication from Role, User, and System Settings."""


def execute():
	from hrms.hr.role_access import disable_two_factor_auth

	disable_two_factor_auth()
