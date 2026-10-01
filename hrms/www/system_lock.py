# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _

no_cache = 1
no_sitemap = 1


def get_context(context):
	context.no_cache = 1
	from hrms.hr.master_key import current_lock_state

	state = current_lock_state()
	if not state.get("locked"):
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/login"
		frappe.flags.redirect_location = "/login"
		raise frappe.Redirect

	context.lock_message = state.get("message") or _("System access is turned off.")
	context.csrf_token = _csrf_token()


def _csrf_token():
	try:
		from frappe.sessions import get_csrf_token

		return get_csrf_token()
	except Exception:
		data = getattr(frappe.session, "data", None) or {}
		token = data.get("csrf_token") if isinstance(data, dict) else None
		if not token:
			token = frappe.generate_hash()
			if isinstance(data, dict):
				data["csrf_token"] = token
		return token
