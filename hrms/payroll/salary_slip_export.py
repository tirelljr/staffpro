# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Export Salary Slips (pay stubs) as CSV, PDF, or ZIP."""

from __future__ import annotations

import io
import zipfile

import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.csvutils import to_csv
from frappe.utils.pdf import get_pdf

PRINT_FORMAT = "Salary Slip Standard"
FILE_STEM = "Salary_Slips"


@frappe.whitelist()
def download_csv(doctype: str, names: str | list | None = None) -> None:
	"""Download selected salary slips as one CSV of earnings and deductions."""
	slips = _load_slips(doctype, names)
	_respond_file(_download_filename(slips, "csv"), _csv_bytes(_csv_rows(slips)))


@frappe.whitelist()
def download_pdf(doctype: str, names: str | list | None = None) -> None:
	"""Download selected salary slips as one branded PDF."""
	slips = _load_slips(doctype, names)
	_respond_file(_download_filename(slips, "pdf"), get_pdf(_render_pdf_html(slips)))


@frappe.whitelist()
def download_zip(doctype: str, names: str | list | None = None) -> None:
	"""Download one CSV per selected salary slip, packed as a ZIP."""
	slips = _load_slips(doctype, names)
	if len(slips) < 2:
		frappe.throw(_("Select more than one Salary Slip to export a ZIP of CSV files."))

	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
		used_names = set()
		for slip in slips:
			filename = _unique_zip_name(_slip_filename(slip, "csv"), used_names)
			archive.writestr(filename, _csv_bytes(_csv_rows([slip])))

	_respond_file(f"{FILE_STEM}.zip", buffer.getvalue())


def _render_pdf_html(slips: list) -> str:
	print_format = _print_format()
	return "".join(
		frappe.get_print(
			"Salary Slip",
			slip.name,
			print_format=print_format,
			doc=slip,
			no_letterhead=True,
		)
		for slip in slips
	)


def _load_slips(doctype: str, names: str | list | None) -> list:
	if doctype != "Salary Slip":
		frappe.throw(_("Invalid document type"))
	_assert_can_export()

	selected = _as_list(names)
	if not selected:
		frappe.throw(_("Select at least one Salary Slip to export."))

	docs = []
	seen = set()
	for name in selected:
		if name in seen:
			continue
		seen.add(name)
		if not frappe.db.exists("Salary Slip", name):
			frappe.throw(_("Salary Slip {0} does not exist").format(name))
		docs.append(frappe.get_doc("Salary Slip", name))
	return docs


def _csv_rows(slips: list) -> list[list]:
	headers = [
		_("Salary Slip"),
		_("Employee"),
		_("Employee Name"),
		_("Company"),
		_("Start Date"),
		_("End Date"),
		_("Posting Date"),
		_("Payment Status"),
		_("Type"),
		_("Component"),
		_("Amount"),
		_("Gross Pay"),
		_("Total Deduction"),
		_("Social Security"),
		_("Net Pay"),
		_("Currency"),
	]
	rows = [headers]
	for slip in slips:
		lines = _slip_lines(slip)
		if not lines:
			rows.append(_slip_row(slip, "", "", ""))
			continue
		for line in lines:
			rows.append(_slip_row(slip, line["type"], line["component"], line["amount"]))
	return rows


def _slip_lines(slip) -> list[dict]:
	lines = []
	for row in slip.get("earnings") or []:
		lines.append(
			{
				"type": _("Earning"),
				"component": row.salary_component or "",
				"amount": flt(row.amount),
			}
		)
	for row in slip.get("deductions") or []:
		lines.append(
			{
				"type": _("Deduction"),
				"component": row.salary_component or "",
				"amount": flt(row.amount),
			}
		)
	return lines


def _slip_row(slip, line_type, component, amount) -> list:
	return [
		slip.name,
		slip.employee or "",
		slip.employee_name or "",
		slip.company or "",
		slip.start_date or "",
		slip.end_date or "",
		slip.posting_date or "",
		slip.payment_status or "",
		line_type,
		component,
		amount if amount != "" else "",
		flt(slip.gross_pay),
		flt(slip.total_deduction),
		flt(slip.ss_employee_amount),
		flt(slip.net_pay),
		slip.currency or "",
	]


def _print_format() -> str:
	if frappe.db.exists("Print Format", PRINT_FORMAT):
		return PRINT_FORMAT
	return frappe.get_meta("Salary Slip").default_print_format or "Standard"


def _download_filename(slips: list, extension: str) -> str:
	if len(slips) == 1:
		return _slip_filename(slips[0], extension)
	return f"{FILE_STEM}.{extension}"


def _slip_filename(slip, extension: str) -> str:
	employee = _safe_filename(slip.employee_name or slip.employee or "Salary_Slip")
	name = _safe_filename(slip.name or "salary_slip")
	return f"{employee}_{name}.{extension}"


def _unique_zip_name(filename: str, used: set[str]) -> str:
	if filename not in used:
		used.add(filename)
		return filename
	stem, _, extension = filename.rpartition(".")
	index = 2
	while True:
		candidate = f"{stem}_{index}.{extension}"
		if candidate not in used:
			used.add(candidate)
			return candidate
		index += 1


def _safe_filename(value: str) -> str:
	cleaned = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in str(value or ""))
	return cleaned.strip().replace(" ", "_") or "salary_slip"


def _csv_bytes(rows: list) -> str:
	return to_csv(rows)


def _respond_file(filename: str, content, file_type: str = "binary"):
	frappe.response["filename"] = filename
	frappe.response["filecontent"] = content
	frappe.response["type"] = file_type


def _assert_can_export():
	if not frappe.has_permission("Salary Slip", "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not (
		frappe.permissions.can_export("Salary Slip") or frappe.has_permission("Salary Slip", "print")
	):
		frappe.throw(_("Not permitted to export"), frappe.PermissionError)


def _as_list(value) -> list:
	if value in (None, "", []):
		return []
	if isinstance(value, str):
		stripped = value.strip()
		if stripped.startswith("["):
			value = frappe.parse_json(stripped)
		else:
			return [stripped] if stripped else []
	if isinstance(value, (list, tuple, set)):
		return [item for item in value if item not in (None, "")]
	return [value]
