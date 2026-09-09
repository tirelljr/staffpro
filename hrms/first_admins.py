# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils.password import update_password

from hrms.hr.bpo_employee_labels import enable_username_login

STAFF_PRO_FIRST_ADMIN_PASSWORD = "admin"
STAFF_PRO_FIRST_ADMINS = (
	{
		"first_name": "Matt",
		"last_name": "Chavez",
		"username": "Matt Chavez",
		"email": "matt.chavez@staffpro.local",
	},
	{
		"first_name": "Micheal",
		"last_name": "Graylord",
		"username": "Micheal Graylord",
		"email": "micheal.graylord@staffpro.local",
	},
	{
		"first_name": "Myra",
		"last_name": "Chavez",
		"username": "Myra Chavez",
		"email": "myra.chavez@staffpro.local",
	},
)
STAFF_PRO_FIRST_ADMIN_ROLES = ("System Manager",)


def ensure_staff_pro_first_admins():
	"""Create the named first-login System Managers used after a fresh setup."""
	if not frappe.db.exists("DocType", "User"):
		return []

	enable_username_login()
	created = []
	for spec in STAFF_PRO_FIRST_ADMINS:
		created.append(_ensure_first_admin(spec))
	frappe.clear_cache()
	return created


def _ensure_first_admin(spec: dict) -> str:
	email = spec["email"]
	username = spec["username"]
	user_name = frappe.db.get_value("User", {"email": email}, "name") or (
		frappe.db.get_value("User", {"username": username}, "name")
	)

	if user_name:
		user = frappe.get_doc("User", user_name)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": spec["first_name"],
				"last_name": spec["last_name"],
				"username": username,
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		)
		user.flags.ignore_permissions = True
		user.flags.ignore_password_policy = True
		user.insert()
		user_name = user.name

	user.reload()
	user.enabled = 1
	user.user_type = "System User"
	user.send_welcome_email = 0
	user.first_name = spec["first_name"]
	user.last_name = spec["last_name"]
	user.username = username
	if user.meta.has_field("default_app"):
		user.default_app = "hrms"
	if user.meta.has_field("last_password_reset_date"):
		from frappe.utils import today

		user.last_password_reset_date = today()
	user.flags.ignore_permissions = True
	user.flags.ignore_password_policy = True
	user.save()

	for role in STAFF_PRO_FIRST_ADMIN_ROLES:
		if frappe.db.exists("Role", role):
			user.add_roles(role)

	update_password(user_name, STAFF_PRO_FIRST_ADMIN_PASSWORD, logout_all_sessions=False)
	# Username with a space can fail User.validate; keep the exact login name.
	if frappe.db.get_value("User", user_name, "username") != username:
		frappe.db.set_value("User", user_name, "username", username, update_modified=False)
	return user_name
