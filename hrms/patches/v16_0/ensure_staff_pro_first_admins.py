# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from hrms.first_admins import ensure_staff_pro_first_admins


def execute():
	"""Create Matt, Micheal, and Myra as first-login System Managers."""
	ensure_staff_pro_first_admins()
