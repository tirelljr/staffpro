# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Master key: a System Manager can shut off sign-in until a time, or until the key turns it back on.

The key is stored as a salted hash. Clear a lost key from the server console only:

    bench --site <site> execute hrms.hr.master_key.clear_master_key
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from datetime import datetime

try:
	import frappe
	from frappe import _
except ImportError:  # unit tests outside a bench
	frappe = None

	def _(text, *args, **kwargs):
		return text


MIN_MASTER_KEY_LENGTH = 12
MAX_MASTER_KEY_LENGTH = 128
HASH_ITERATIONS = 260_000
ATTEMPT_LIMIT = 5
ATTEMPT_WINDOW_SECONDS = 15 * 60
CACHE_KEY = "hrms_system_lock_state"
LOCK_SCREEN = "/system-lock"
SETTINGS = "Master Key Settings"
SECRET_FIELDS = ("master_key", "confirm_key", "account_password", "current_key")
ALLOWED_METHODS = frozenset(
	{
		"hrms.hr.master_key.unlock_system",
		"hrms.hr.master_key.get_public_lock_status",
	}
)
LOCK_PATHS = frozenset({"/system-lock", "/system_lock"})


def hash_master_key(key: str, salt: str | None = None) -> str:
	normalized = _normalize_key(key)
	salt = salt or secrets.token_hex(16)
	digest = hashlib.pbkdf2_hmac(
		"sha256",
		normalized.encode("utf-8"),
		salt.encode("utf-8"),
		HASH_ITERATIONS,
	)
	return f"pbkdf2_sha256${HASH_ITERATIONS}${salt}${digest.hex()}"


def verify_master_key(key: str, stored: str | None) -> bool:
	normalized = _normalize_key(key)
	if not normalized or len(normalized) > MAX_MASTER_KEY_LENGTH:
		return False
	parsed = _parse_hash(stored)
	if not parsed:
		return False
	iterations, salt, digest = parsed
	check = hashlib.pbkdf2_hmac(
		"sha256",
		normalized.encode("utf-8"),
		salt.encode("utf-8"),
		iterations,
	)
	try:
		return hmac.compare_digest(check.hex(), digest)
	except Exception:
		return False


def check_new_master_key(master_key, confirm_key) -> tuple[bool, str, str]:
	key = _normalize_key(master_key)
	confirm = _normalize_key(confirm_key)
	if not key or not confirm:
		return False, "", "required"
	if key != confirm:
		return False, "", "mismatch"
	if len(key) < MIN_MASTER_KEY_LENGTH:
		return False, "", "short"
	if len(key) > MAX_MASTER_KEY_LENGTH:
		return False, "", "long"
	return True, key, ""


def parse_lock_time(value):
	if value is None or value == "":
		return None
	if isinstance(value, datetime):
		return value.replace(tzinfo=None) if value.tzinfo else value
	text = str(value).strip().replace("T", " ")
	if text.endswith("Z"):
		text = text[:-1]
	if len(text) == 16:
		text = text + ":00"
	for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
		try:
			return datetime.strptime(text, fmt)
		except ValueError:
			continue
	return None


def lock_is_active(lock_status, locked_until, now) -> bool:
	status = str(lock_status or "Off").strip()
	if status in {"", "Off"}:
		return False
	if status == "Manual":
		return True
	if status == "Until":
		until = parse_lock_time(locked_until)
		current = parse_lock_time(now)
		if until is None or current is None:
			return True
		return current < until
	return True


def user_can_manage_master_key(user, roles=None) -> bool:
	if not user or user == "Guest":
		return False
	if user == "Administrator":
		return True
	return "System Manager" in set(roles or [])


def is_master_key_sidebar_item(item) -> bool:
	if not isinstance(item, dict):
		return False
	if str(item.get("type") or "") in {"Section Break", "section"}:
		return False
	label = str(item.get("label") or "").strip()
	link = str(item.get("link_to") or "").strip()
	return label == "Master Key" or link == "master-key"


def master_key_link_allowed(item, is_system_manager) -> bool:
	if not is_master_key_sidebar_item(item):
		return True
	return bool(is_system_manager)


def _normalize_key(key) -> str:
	return str(key or "").strip()


def _parse_hash(stored: str | None):
	if not stored or stored.count("$") != 3:
		return None
	try:
		algo, iterations, salt, digest = str(stored).split("$")
		if algo != "pbkdf2_sha256" or not salt or not digest:
			return None
		count = int(iterations)
	except (TypeError, ValueError):
		return None
	if count < 1 or count > 2_000_000:
		return None
	return count, salt, digest


def _whitelist(allow_guest=False, methods=None):
	def decorator(fn):
		if frappe is None:
			return fn
		kwargs = {"allow_guest": allow_guest}
		if methods:
			kwargs["methods"] = methods
		return frappe.whitelist(**kwargs)(fn)

	return decorator


def _scrub_secrets():
	if frappe is None:
		return
	form = getattr(frappe, "form_dict", None)
	if not form:
		return
	for field in SECRET_FIELDS:
		try:
			form.pop(field, None)
		except Exception:
			pass


def _request_ip() -> str:
	if frappe is None:
		return "unknown"
	ip = getattr(frappe.local, "request_ip", None)
	if ip:
		return str(ip)
	request = getattr(frappe.local, "request", None)
	remote = getattr(request, "remote_addr", None) if request is not None else None
	return str(remote or "unknown")


def _require_system_manager():
	user = frappe.session.user
	roles = [] if user == "Administrator" else frappe.get_roles(user)
	if not user_can_manage_master_key(user, roles):
		frappe.throw(_("Only a System Manager can use the master key."), frappe.PermissionError)


def _check_account_password(password: str):
	if not _normalize_key(password):
		frappe.throw(_("Enter your login password."))
	from frappe.utils.password import check_password

	try:
		check_password(frappe.session.user, password)
	except frappe.AuthenticationError:
		frappe.throw(_("Login password is incorrect."), frappe.AuthenticationError)


def _key_error(code: str):
	if code == "mismatch":
		frappe.throw(_("Enter the same master key in both fields."))
	if code == "short":
		frappe.throw(_("Use at least {0} characters.").format(MIN_MASTER_KEY_LENGTH))
	if code == "long":
		frappe.throw(_("Use at most {0} characters.").format(MAX_MASTER_KEY_LENGTH))
	frappe.throw(_("Enter a master key."))


def _settings_ready() -> bool:
	try:
		return bool(frappe.db.exists("DocType", SETTINGS))
	except Exception:
		return False


def _read_public_state() -> dict:
	status = frappe.db.get_single_value(SETTINGS, "lock_status") or "Off"
	return {
		"key_configured": bool(frappe.db.get_single_value(SETTINGS, "key_hash")),
		"lock_status": status,
		"locked_until": frappe.db.get_single_value(SETTINGS, "locked_until"),
		"locked_by": frappe.db.get_single_value(SETTINGS, "locked_by") or "",
		"locked_on": frappe.db.get_single_value(SETTINGS, "locked_on"),
	}


def _cache_state(state: dict) -> dict:
	until = state.get("locked_until")
	locked_on = state.get("locked_on")
	payload = {
		"key_configured": bool(state.get("key_configured")),
		"lock_status": state.get("lock_status") or "Off",
		"locked_until": str(until) if until else None,
		"locked_by": state.get("locked_by") or "",
		"locked_on": str(locked_on) if locked_on else None,
	}
	try:
		frappe.cache().set_value(CACHE_KEY, payload)
	except Exception:
		pass
	return payload


def _write_settings(**values) -> dict:
	for field, value in values.items():
		frappe.db.set_single_value(SETTINGS, field, value)
	frappe.db.commit()
	try:
		frappe.clear_document_cache(SETTINGS, SETTINGS)
	except Exception:
		pass
	return _cache_state(_read_public_state())


def _now():
	return frappe.utils.now_datetime()


def _stored_hash() -> str:
	return frappe.db.get_single_value(SETTINGS, "key_hash") or ""


def _public_view(state: dict) -> dict:
	locked = lock_is_active(state.get("lock_status"), state.get("locked_until"), _now())
	until = state.get("locked_until")
	until_text = ""
	if until:
		try:
			until_text = frappe.utils.format_datetime(until)
		except Exception:
			until_text = str(until)
	if locked and state.get("lock_status") == "Until" and until_text:
		message = _("System access is turned off until {0}. Enter the master key to turn it back on sooner.").format(
			until_text
		)
	elif locked:
		message = _("System access is turned off. Enter the master key to turn it back on.")
	else:
		message = _("System access is on.")
	return {
		"key_configured": bool(state.get("key_configured")),
		"locked": locked,
		"lock_status": state.get("lock_status") or "Off",
		"locked_until": until_text or None,
		"locked_by": state.get("locked_by") or "",
		"locked_on": str(state.get("locked_on") or "") or None,
		"message": message,
	}


def current_lock_state() -> dict:
	if not _settings_ready():
		return {"locked": False, "lock_status": "Off", "key_configured": False}
	cached = None
	try:
		cached = frappe.cache().get_value(CACHE_KEY)
	except Exception:
		cached = None
	if not isinstance(cached, dict) or "lock_status" not in cached:
		cached = _cache_state(_read_public_state())
	if cached.get("lock_status") == "Until" and not lock_is_active("Until", cached.get("locked_until"), _now()):
		return _release_lock("System access lock expired")
	view = _public_view(cached)
	return view


def _release_lock(subject: str) -> dict:
	state = _write_settings(lock_status="Off", locked_until=None)
	_audit(subject)
	view = _public_view(state)
	view["locked"] = False
	return view


def _audit(subject: str):
	user = getattr(frappe.session, "user", None)
	if not user or user == "Guest":
		user = "Administrator"
	try:
		frappe.get_doc(
			{
				"doctype": "Activity Log",
				"subject": subject[:140],
				"status": "Success",
				"user": user,
				"ip_address": _request_ip(),
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="Master key activity log")


def _attempt_key() -> str:
	return f"hrms_master_key_unlock:{_request_ip()}"


def _too_many_attempts() -> bool:
	payload = frappe.cache().get_value(_attempt_key()) or {}
	if not isinstance(payload, dict):
		return False
	started = float(payload.get("started") or 0)
	if time.time() - started > ATTEMPT_WINDOW_SECONDS:
		return False
	return int(payload.get("count") or 0) >= ATTEMPT_LIMIT


def _record_failed_attempt():
	key = _attempt_key()
	now = time.time()
	payload = frappe.cache().get_value(key) or {}
	if not isinstance(payload, dict) or now - float(payload.get("started") or 0) > ATTEMPT_WINDOW_SECONDS:
		payload = {"started": now, "count": 0}
	payload["count"] = int(payload.get("count") or 0) + 1
	try:
		frappe.cache().set_value(key, payload, expires_in_sec=ATTEMPT_WINDOW_SECONDS)
	except TypeError:
		frappe.cache().set_value(key, payload)


def _clear_attempts():
	try:
		frappe.cache().delete_value(_attempt_key())
	except Exception:
		pass


def _verify_configured_key(master_key: str):
	stored = _stored_hash()
	if not stored:
		frappe.throw(_("Set a master key before locking access."))
	if not verify_master_key(master_key, stored):
		frappe.throw(_("Master key is incorrect."), frappe.AuthenticationError)


def clear_all_user_sessions():
	try:
		rows = frappe.db.sql("select sid from `tabSessions`", as_dict=True)
	except Exception:
		rows = []
	cache = frappe.cache()
	for row in rows or []:
		sid = row.get("sid") if isinstance(row, dict) else None
		if not sid:
			continue
		try:
			cache.delete_value(f"session:{sid}")
		except Exception:
			pass
	try:
		frappe.db.sql("delete from `tabSessions`")
		frappe.db.commit()
	except Exception:
		frappe.log_error(title="Master key session clear")


def _mark_guest(holder):
	if holder is None:
		return
	try:
		holder.user = "Guest"
	except Exception:
		pass
	data = getattr(holder, "data", None)
	if isinstance(data, dict):
		data["user"] = "Guest"
		data["full_name"] = "Guest"
		data["user_type"] = "Website User"


def _drop_current_login():
	sid = getattr(frappe.session, "sid", None)
	try:
		if sid:
			frappe.db.sql("delete from `tabSessions` where sid=%s", sid)
			frappe.cache().delete_value(f"session:{sid}")
			frappe.db.commit()
	except Exception:
		pass
	try:
		frappe.set_user("Guest")
	except Exception:
		pass
	_mark_guest(getattr(frappe, "session", None))
	_mark_guest(getattr(frappe.local, "session_obj", None))
	try:
		frappe.local.cookie_manager.delete_cookie("sid")
		frappe.local.cookie_manager.delete_cookie("user_id")
		frappe.local.cookie_manager.delete_cookie("full_name")
		frappe.local.cookie_manager.delete_cookie("system_user")
	except Exception:
		pass


def _sign_everyone_out():
	_drop_current_login()
	clear_all_user_sessions()


@_whitelist(methods=["POST"])
def get_status():
	_require_system_manager()
	_scrub_secrets()
	if not _settings_ready():
		frappe.throw(_("Master Key is not installed yet. Run bench migrate."))
	return current_lock_state()


@_whitelist(methods=["POST"])
def set_master_key(master_key=None, confirm_key=None, account_password=None, current_key=None):
	_require_system_manager()
	_scrub_secrets()
	try:
		if not _settings_ready():
			frappe.throw(_("Master Key is not installed yet. Run bench migrate."))
		_check_account_password(account_password or "")
		ok, key, code = check_new_master_key(master_key, confirm_key)
		if not ok:
			_key_error(code)
		stored = _stored_hash()
		if stored:
			if not verify_master_key(current_key or "", stored):
				frappe.throw(_("Master key is incorrect."), frappe.AuthenticationError)
			subject = "Master key was changed"
		else:
			subject = "Master key was set"
		_write_settings(key_hash=hash_master_key(key), key_configured=1)
		_audit(subject)
		return {"key_configured": True}
	finally:
		_scrub_secrets()


@_whitelist(methods=["POST"])
def lock_access(master_key=None, mode=None, locked_until=None):
	_require_system_manager()
	_scrub_secrets()
	try:
		if not _settings_ready():
			frappe.throw(_("Master Key is not installed yet. Run bench migrate."))
		_verify_configured_key(master_key or "")
		choice = str(mode or "").strip().lower()
		now = _now()
		if choice == "manual":
			_write_settings(
				lock_status="Manual",
				locked_until=None,
				locked_by=frappe.session.user,
				locked_on=now,
			)
			_audit("System access locked until turned back on")
		elif choice == "until":
			until = parse_lock_time(locked_until)
			current = parse_lock_time(now)
			if until is None or current is None or until <= current:
				frappe.throw(_("Choose a time in the future."))
			_write_settings(
				lock_status="Until",
				locked_until=until.strftime("%Y-%m-%d %H:%M:%S"),
				locked_by=frappe.session.user,
				locked_on=now,
			)
			_audit("System access locked until " + until.strftime("%Y-%m-%d %H:%M:%S"))
		else:
			frappe.throw(_("Choose how long to keep access off."))
		_sign_everyone_out()
		return {"locked": True, "redirect": LOCK_SCREEN}
	finally:
		_scrub_secrets()


@_whitelist(allow_guest=True, methods=["POST"])
def unlock_system(master_key=None):
	_scrub_secrets()
	try:
		if not _settings_ready():
			return {"locked": False, "redirect": "/login"}
		if _too_many_attempts():
			frappe.throw(_("Too many attempts. Try again in a few minutes."), frappe.RateLimitExceededError)
		state = current_lock_state()
		if not state.get("locked"):
			_clear_attempts()
			return {"locked": False, "redirect": "/login"}
		if not verify_master_key(master_key or "", _stored_hash()):
			_record_failed_attempt()
			_audit("Failed system unlock attempt")
			frappe.throw(_("Master key is incorrect."), frappe.AuthenticationError)
		_clear_attempts()
		_release_lock("System access restored")
		return {"locked": False, "redirect": "/login"}
	finally:
		_scrub_secrets()


@_whitelist(allow_guest=True)
def get_public_lock_status():
	if not _settings_ready():
		return {"locked": False, "message": _("System access is on.")}
	state = current_lock_state()
	return {
		"locked": bool(state.get("locked")),
		"lock_status": state.get("lock_status") or "Off",
		"locked_until": state.get("locked_until"),
		"message": state.get("message"),
	}


def clear_master_key():
	"""Drop the master key and turn access back on. Server console only."""
	if getattr(frappe.local, "request", None):
		frappe.throw(_("The master key can only be cleared from the server console."))
	if not _settings_ready():
		return "Master Key is not installed yet."
	_write_settings(
		key_hash="",
		key_configured=0,
		lock_status="Off",
		locked_until=None,
		locked_by="",
		locked_on=None,
	)
	try:
		frappe.cache().delete_value(CACHE_KEY)
	except Exception:
		pass
	_audit("Master key cleared from the server console")
	return "Master key cleared and system access is on."


def _request_path(request) -> str:
	return (getattr(request, "path", None) or "").split("?", 1)[0].rstrip("/").lower()


def _is_static(path: str) -> bool:
	return path.startswith("/assets/") or path == "/favicon.ico"


def _is_lock_screen(path: str) -> bool:
	return path in LOCK_PATHS


def _is_unlock_call(path: str) -> bool:
	for method in ALLOWED_METHODS:
		if path.endswith("/" + method.lower()):
			return True
	if path == "/api/method":
		cmd = str(frappe.form_dict.get("cmd") or "")
		return cmd in ALLOWED_METHODS
	return False


def _request_is_allowed(request) -> bool:
	path = _request_path(request)
	return _is_static(path) or _is_lock_screen(path) or _is_unlock_call(path)


def enforce_system_lock():
	if frappe is None:
		return
	if getattr(frappe.flags, "in_migrate", False) or getattr(frappe.flags, "in_install", False):
		return
	request = getattr(frappe.local, "request", None)
	if request is None:
		return
	if _is_static(_request_path(request)):
		return
	try:
		if not _settings_ready():
			return
		state = current_lock_state()
	except Exception:
		frappe.log_error(title="Master key lock check")
		return
	if not state.get("locked"):
		return
	user = getattr(frappe.session, "user", None)
	if user and user != "Guest":
		_drop_current_login()
	if _request_is_allowed(request):
		return
	_deny_locked_request()


def _deny_locked_request():
	for field in SECRET_FIELDS + ("password", "pwd", "usr"):
		try:
			frappe.form_dict.pop(field, None)
		except Exception:
			pass
	path = _request_path(getattr(frappe.local, "request", None))
	wants_json = path.startswith("/api/") or bool(frappe.form_dict.get("cmd"))
	if wants_json:
		frappe.local.response["http_status_code"] = 403
		frappe.throw(_("System access is locked."), frappe.PermissionError)
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = LOCK_SCREEN
	frappe.flags.redirect_location = LOCK_SCREEN
	raise frappe.Redirect
