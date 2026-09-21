# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Drop corrupted Employee list fields that crash reportview with DocType e not found."""

import json

import frappe
from frappe.utils import cstr


def execute():
	_clean_list_view_settings()
	_clean_user_settings()
	frappe.clear_cache(doctype="Employee")


def _is_garbage_field(field) -> bool:
	if isinstance(field, dict):
		field = field.get("fieldname") or field.get("field") or ""
	text = cstr(field).replace("`", "").strip()
	if not text or len(text) == 1:
		return True
	parts = text.split(".")
	parent = parts[0]
	if parent.lower().startswith("tab"):
		parent = parent[3:]
	return len(parts) == 2 and len(parent) <= 1


def _clean_fields(fields):
	if not isinstance(fields, list):
		return fields, False
	cleaned = [field for field in fields if not _is_garbage_field(field)]
	return cleaned, cleaned != fields


def _clean_settings_payload(raw):
	try:
		data = json.loads(raw) if isinstance(raw, str) else raw
	except (TypeError, ValueError):
		return raw, False
	if not isinstance(data, dict):
		return raw, False
	changed = False
	if "fields" in data:
		cleaned, dirty = _clean_fields(data.get("fields"))
		if dirty:
			data["fields"] = cleaned
			changed = True
	for view in data.values():
		if not isinstance(view, dict) or "fields" not in view:
			continue
		cleaned, dirty = _clean_fields(view.get("fields"))
		if dirty:
			view["fields"] = cleaned
			changed = True
	return json.dumps(data), changed


def _clean_list_view_settings():
	if not frappe.db.exists("DocType", "List View Settings"):
		return
	if not frappe.db.exists("List View Settings", "Employee"):
		return
	raw = frappe.db.get_value("List View Settings", "Employee", "fields")
	if not raw:
		return
	try:
		fields = json.loads(raw)
	except (TypeError, ValueError):
		return
	cleaned, dirty = _clean_fields(fields)
	if dirty:
		frappe.db.set_value(
			"List View Settings",
			"Employee",
			"fields",
			json.dumps(cleaned),
			update_modified=False,
		)


def _clean_user_settings():
	if not frappe.db.sql("SHOW TABLES LIKE %s", "__UserSettings"):
		return
	rows = frappe.db.sql(
		"select `user` as user_name, doctype, data from `__UserSettings` where doctype=%s",
		"Employee",
		as_dict=True,
	)
	for row in rows:
		cleaned, changed = _clean_settings_payload(row.data)
		if not changed:
			continue
		frappe.db.sql(
			"update `__UserSettings` set data=%s where `user`=%s and doctype=%s",
			(cleaned, row.user_name, row.doctype),
		)
