# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Use username (not email) for employee login and clock-in."""

import frappe

from hrms.hr.bpo_employee_labels import apply_bpo_employee_labels
from hrms.overrides.employee_master import suggest_username, unique_username


def execute():
	apply_bpo_employee_labels()
	_backfill_user_usernames()


def _backfill_user_usernames():
	if not frappe.db.exists("DocType", "User"):
		return

	users = frappe.get_all(
		"User",
		filters={"name": ["not in", ["Administrator", "Guest"]], "enabled": 1},
		fields=["name", "username", "first_name", "last_name", "full_name"],
	)
	for user in users:
		if user.username:
			continue
		base = suggest_username(user.first_name, user.last_name, user.name.split("@")[0])
		frappe.db.set_value("User", user.name, "username", unique_username(base, user.name), update_modified=False)
