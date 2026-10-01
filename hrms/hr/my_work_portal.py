# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""One-time handoff so a signed-in internal employee opens My Work without a second login."""

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import cint

from hrms.hr.staff_pro_roles import MY_WORK_PORTAL_PATH, can_use_my_work_portal

HANDOFF_TTL_SECONDS = 90
_HANDOFF_KEY = "staff_pro_my_work_handoff"
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{20,128}$")


def _cache_key(token: str) -> str:
	return f"{_HANDOFF_KEY}:{token}"


def _pin_my_work_home() -> None:
	response = getattr(frappe.local, "response", None)
	if isinstance(response, dict):
		response["home_page"] = MY_WORK_PORTAL_PATH
		response["redirect_to"] = MY_WORK_PORTAL_PATH


def _establish_session(user: str) -> None:
	"""Continue as this user. Tests avoid login_as because it commits the session."""
	if frappe.session.user == user:
		_pin_my_work_home()
		return

	if cint(getattr(frappe.flags, "in_test", 0)):
		frappe.set_user(user)
		_pin_my_work_home()
		return

	manager = getattr(frappe.local, "login_manager", None)
	if not manager:
		frappe.set_user(user)
		_pin_my_work_home()
		return

	manager.login_as(user)
	_pin_my_work_home()


@frappe.whitelist(methods=["POST"])
def create_handoff() -> dict:
	"""Mint a short-lived token for the user who is already signed in on the desk."""
	user = frappe.session.user
	if not user or user == "Guest" or not can_use_my_work_portal(user):
		frappe.throw(_("You cannot open My Work from this account."), frappe.PermissionError)

	token = frappe.generate_hash(length=32)
	if not _TOKEN.match(token):
		frappe.throw(_("Could not open My Work. Try again."), frappe.ValidationError)

	frappe.cache.set_value(_cache_key(token), user, expires_in_sec=HANDOFF_TTL_SECONDS)
	return {"token": token, "redirect": MY_WORK_PORTAL_PATH}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def consume_handoff(token: str | None = None) -> dict:
	"""Trade a My Work token for the existing user's portal session. No password."""
	token = (token or "").strip()
	if not _TOKEN.match(token):
		frappe.throw(_("This My Work link is invalid. Open it again from the desk."), frappe.PermissionError)

	key = _cache_key(token)
	user = frappe.cache.get_value(key)
	frappe.cache.delete_value(key)
	if not user or user == "Guest" or not frappe.db.exists("User", user):
		frappe.throw(_("This My Work link expired. Open it again from the desk."), frappe.PermissionError)
	if not can_use_my_work_portal(user):
		frappe.throw(_("You cannot open My Work from this account."), frappe.PermissionError)

	_establish_session(user)
	return {"user": user, "my_work": True, "home": MY_WORK_PORTAL_PATH}
