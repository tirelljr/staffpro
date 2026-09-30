# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Per-agent document vault used by the Filesystem desk page and the agent portal."""

from __future__ import annotations

import base64
import io
import re
from mimetypes import guess_type

import frappe
from frappe import _
from frappe.handler import ALLOWED_MIMETYPES
from frappe.utils import cint, cstr, now_datetime
from frappe.utils.file_manager import save_file

from hrms.hr.doctype.agent_document.agent_document import (
	assert_can_store,
	get_session_employee,
	is_hr_user,
)
from hrms.hr.doctype.document_category.document_category import seed_document_categories

ROOT_FOLDER = "Agent Files"
DOCUMENTS_TAB_FIELD = "agent_documents_tab"
DOCUMENTS_HTML_FIELD = "agent_documents_html"


def field_before_employee_profile_tab() -> str:
	"""Place the Documents tab immediately before the Employee Profile tab."""
	fallback = "default_ipv4"
	try:
		if not frappe.db.exists("DocType", "Employee"):
			return fallback
		meta = frappe.get_meta("Employee")
	except Exception:
		return fallback

	previous = fallback
	for df in meta.fields:
		if df.fieldname in {DOCUMENTS_TAB_FIELD, DOCUMENTS_HTML_FIELD}:
			continue
		label = cstr(df.label).strip().lower()
		if df.fieldtype == "Tab Break" and label == "profile":
			return previous
		previous = df.fieldname
	return previous


def employee_document_tab_fields() -> list[dict]:
	return [
		{
			"fieldname": DOCUMENTS_TAB_FIELD,
			"fieldtype": "Tab Break",
			"label": _("Documents"),
			"insert_after": field_before_employee_profile_tab(),
		},
		{
			"fieldname": DOCUMENTS_HTML_FIELD,
			"fieldtype": "HTML",
			"insert_after": DOCUMENTS_TAB_FIELD,
		},
	]


def ensure_employee_documents_tab() -> None:
	if not frappe.db.exists("DocType", "Employee"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"Employee": employee_document_tab_fields()}, ignore_validate=True)
	frappe.clear_cache(doctype="Employee")


def _assert_hr() -> None:
	if not is_hr_user():
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def _assert_filesystem_user() -> None:
	if is_hr_user() or get_session_employee():
		return
	frappe.throw(_("Not permitted"), frappe.PermissionError)


def _assert_employee_exists(employee: str) -> None:
	if not employee or not frappe.db.exists("Employee", employee):
		frappe.throw(_("Agent {0} was not found.").format(employee or ""))


def _assert_can_access_employee(employee: str) -> None:
	_assert_employee_exists(employee)
	if is_hr_user():
		return
	if get_session_employee() == employee:
		return
	frappe.throw(_("You can only open your own files."), frappe.PermissionError)


def _can_delete(employee: str, uploaded_by: str | None) -> bool:
	if is_hr_user():
		return True
	return get_session_employee() == employee and uploaded_by == frappe.session.user


def _safe_folder_name(value: str, limit: int = 80) -> str:
	cleaned = re.sub(r"[\\/]+", "-", cstr(value)).strip().strip(".")
	cleaned = re.sub(r"\s+", " ", cleaned)
	return (cleaned[:limit] or "Untitled").strip()


def _ensure_folder(file_name: str, parent: str) -> str:
	existing = frappe.db.get_value(
		"File",
		{"is_folder": 1, "file_name": file_name, "folder": parent},
		"name",
	)
	if existing:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"is_folder": 1,
			"folder": parent,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def ensure_category_folder(employee: str, category: str) -> str:
	"""Create Home / Agent Files / {id} - {name} / {category} and return the category folder name."""
	if not frappe.db.exists("File", "Home"):
		home = frappe.get_doc({"doctype": "File", "file_name": "Home", "is_folder": 1, "is_home_folder": 1})
		home.flags.ignore_permissions = True
		home.insert()

	employee_name = frappe.db.get_value("Employee", employee, "employee_name") or employee
	root = _ensure_folder(ROOT_FOLDER, "Home")
	agent_folder = _ensure_folder(_safe_folder_name(f"{employee} - {employee_name}"), root)
	return _ensure_folder(_safe_folder_name(category), agent_folder)


def _decode_upload(filename: str, content: str) -> bytes:
	try:
		decoded = base64.b64decode(content)
	except Exception:
		frappe.throw(_("The uploaded file could not be read."))

	content_type = guess_type(filename)[0]
	if content_type not in ALLOWED_MIMETYPES:
		frappe.throw(_("You can only upload JPG, PNG, PDF, TXT or Microsoft documents."))

	if content_type and content_type.startswith("image/jpeg"):
		from PIL import Image, ImageOps
		with Image.open(io.BytesIO(decoded)) as image:
			transposed = ImageOps.exif_transpose(image)
			buffer = io.BytesIO()
			transposed.save(buffer, format="JPEG")
			return buffer.getvalue()
	return decoded


def _file_format(file_name: str) -> str:
	base = cstr(file_name).rsplit("/", 1)[-1]
	if "." not in base:
		return ""
	return base.rsplit(".", 1)[-1].upper()[:12]


def _file_row(row) -> dict:
	uploaded_by = row.uploaded_by
	uploaded_by_name = ""
	if uploaded_by:
		uploaded_by_name = frappe.db.get_value("User", uploaded_by, "full_name") or uploaded_by
	file_url = row.file or ""
	file_name = row.file_name or (file_url.rsplit("/", 1)[-1] if file_url else "")
	return {
		"name": row.name,
		"employee": row.employee,
		"employee_name": row.get("employee_name") or "",
		"category": row.category,
		"file_name": file_name,
		"file_format": _file_format(file_name),
		"file": file_url,
		"file_url": file_url,
		"notes": row.notes or "",
		"uploaded_by": uploaded_by or "",
		"uploaded_by_name": uploaded_by_name,
		"uploaded_on": cstr(row.uploaded_on) if row.uploaded_on else "",
		"hr_request": row.get("hr_request") or "",
		"can_delete": _can_delete(row.employee, uploaded_by),
	}


def _attach_employee_names(rows: list[dict]) -> list[dict]:
	ids = sorted({row.get("employee") for row in rows if row.get("employee") and not row.get("employee_name")})
	names = {}
	if ids:
		for employee in frappe.get_all(
			"Employee",
			filters={"name": ["in", ids]},
			fields=["name", "employee_name"],
			limit_page_length=0,
		):
			names[employee.name] = employee.employee_name or employee.name
	for row in rows:
		if not row.get("employee_name"):
			row["employee_name"] = names.get(row.get("employee"), row.get("employee") or "")
	return rows


def _category_rows(employee: str | None = None) -> list[dict]:
	categories = frappe.get_all(
		"Document Category",
		fields=["name", "category_name", "description", "sort_order"],
		order_by="sort_order asc, category_name asc",
		limit_page_length=0,
	)
	counts: dict[str, int] = {}
	if employee:
		for row in frappe.get_all(
			"Agent Document",
			filters={"employee": employee},
			fields=["category", {"COUNT": "*", "as": "file_count"}],
			group_by="category",
		):
			counts[row.category] = cint(row.file_count)
	result = []
	for row in categories:
		result.append(
			{
				"name": row.name,
				"category_name": row.category_name or row.name,
				"description": row.description or "",
				"sort_order": cint(row.sort_order),
				"file_count": counts.get(row.name, 0),
			}
		)
	return result


@frappe.whitelist()
def list_agents(search: str | None = None, category: str | None = None) -> list[dict]:
	_assert_hr()
	seed_document_categories()
	search = (search or "").strip()
	category = (category or "").strip()
	list_kwargs = {
		"fields": ["name", "employee_name", "image", "designation", "department", "status"],
		"order_by": "employee_name asc",
		"limit_page_length": 0,
	}
	if search:
		like = f"%{search}%"
		list_kwargs["or_filters"] = {"name": ["like", like], "employee_name": ["like", like]}

	employees = frappe.get_all("Employee", **list_kwargs)
	count_kwargs = {
		"fields": ["employee", {"COUNT": "*", "as": "file_count"}],
		"group_by": "employee",
	}
	if category:
		count_kwargs["filters"] = {"category": category}
	counts = {
		row.employee: cint(row.file_count)
		for row in frappe.get_all("Agent Document", **count_kwargs)
	}
	for row in employees:
		row["file_count"] = counts.get(row.name, 0)
	return employees


@frappe.whitelist()
def create_folder(folder_name: str | None = None) -> dict:
	"""Add a document category, which is a folder under every agent."""
	_assert_hr()
	name = " ".join((folder_name or "").split())
	if not name:
		frappe.throw(_("Folder name is required."))
	if frappe.db.exists("Document Category", name):
		frappe.throw(_("Folder {0} already exists.").format(name))
	latest = frappe.get_all(
		"Document Category",
		fields=["sort_order"],
		order_by="sort_order desc",
		limit=1,
	)
	sort_order = (cint(latest[0].sort_order) if latest else 0) + 1
	doc = frappe.get_doc(
		{
			"doctype": "Document Category",
			"category_name": name,
			"sort_order": sort_order,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return {"name": doc.name, "category_name": doc.category_name or doc.name}


@frappe.whitelist()
def list_categories(employee: str | None = None) -> list[dict]:
	seed_document_categories()
	_assert_filesystem_user()
	if employee:
		_assert_can_access_employee(employee)
	return _category_rows(employee)


@frappe.whitelist()
def list_files(employee: str | None = None, category: str | None = None) -> list[dict]:
	employee = (employee or "").strip()
	category = (category or "").strip()
	if employee:
		_assert_can_access_employee(employee)
	else:
		_assert_hr()
	filters = {}
	if employee:
		filters["employee"] = employee
	if category:
		filters["category"] = category
	fields = ["name", "employee", "category", "file", "file_name", "notes", "uploaded_by", "uploaded_on"]
	if frappe.get_meta("Agent Document").has_field("hr_request"):
		fields.append("hr_request")
	rows = frappe.get_all(
		"Agent Document",
		filters=filters,
		fields=fields,
		order_by="uploaded_on desc, creation desc",
		limit_page_length=0,
	)
	return _attach_employee_names([_file_row(row) for row in rows])


@frappe.whitelist()
def upload_file(
	employee: str | None = None,
	category: str | None = None,
	filename: str | None = None,
	content: str | None = None,
	notes: str | None = None,
) -> dict:
	employee = employee or get_session_employee()
	if not employee:
		frappe.throw(_("No active agent is linked to your user."), frappe.PermissionError)
	if not category:
		frappe.throw(_("Category is required."))
	if not filename or not content:
		frappe.throw(_("A file is required."))
	if not frappe.db.exists("Document Category", category):
		frappe.throw(_("Category {0} was not found.").format(category))

	_assert_can_access_employee(employee)
	assert_can_store(employee)
	file_bytes = _decode_upload(filename, content)
	folder = ensure_category_folder(employee, category)

	doc = frappe.get_doc(
		{
			"doctype": "Agent Document",
			"employee": employee,
			"category": category,
			"file_name": filename,
			"notes": notes or "",
			"uploaded_by": frappe.session.user,
			"uploaded_on": now_datetime(),
		}
	)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.insert()

	try:
		save_file(
			filename,
			file_bytes,
			"Agent Document",
			doc.name,
			folder=folder,
			is_private=1,
			df="file",
		)
	except Exception:
		frappe.delete_doc("Agent Document", doc.name, ignore_permissions=True, force=True)
		raise

	doc.reload()
	if not doc.file:
		file_url = frappe.db.get_value(
			"File",
			{"attached_to_doctype": "Agent Document", "attached_to_name": doc.name, "is_folder": 0},
			"file_url",
		)
		if file_url:
			doc.db_set("file", file_url, update_modified=False)
			doc.file = file_url
	if not doc.file_name:
		doc.db_set("file_name", filename, update_modified=False)
		doc.file_name = filename
	return _file_row(doc)


@frappe.whitelist()
def delete_file(name: str) -> dict:
	if not name or not frappe.db.exists("Agent Document", name):
		frappe.throw(_("File {0} was not found.").format(name or ""))
	doc = frappe.get_doc("Agent Document", name)
	_assert_can_access_employee(doc.employee)
	if not _can_delete(doc.employee, doc.uploaded_by):
		frappe.throw(_("You can only delete files you uploaded."), frappe.PermissionError)
	frappe.delete_doc("Agent Document", doc.name, ignore_permissions=True, force=True)
	return {"name": name, "deleted": True}


@frappe.whitelist()
def get_my_filesystem() -> dict:
	seed_document_categories()
	employee = get_session_employee()
	if not employee:
		frappe.throw(_("No active agent is linked to your user."), frappe.PermissionError)
	employee_name = frappe.db.get_value("Employee", employee, "employee_name")
	categories = _category_rows(employee)
	grouped: dict[str, list] = {row["name"]: [] for row in categories}
	for file_row in list_files(employee):
		grouped.setdefault(file_row["category"], []).append(file_row)
	for row in categories:
		row["files"] = grouped.get(row["name"], [])
	return {
		"employee": employee,
		"employee_name": employee_name or employee,
		"categories": categories,
	}
