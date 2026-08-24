# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Export Client Invoices and Posted Invoices as CSV, PDF, or ZIP."""

from __future__ import annotations

import io
import zipfile

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, formatdate, getdate
from frappe.utils.csvutils import to_csv
from frappe.utils.pdf import get_pdf

from hrms.branding import staff_pro_logo_url

ALLOWED_DOCTYPES = {
	"Client Invoice": {
		"label": _("Client Invoice"),
		"plural": _("Client Invoices"),
		"file_stem": "Client_Invoices",
	},
	"Sales Invoice": {
		"label": _("Posted Invoice"),
		"plural": _("Posted Invoices"),
		"file_stem": "Posted_Invoices",
	},
}


@frappe.whitelist()
def download_csv(doctype: str, names: str | list | None = None) -> None:
	"""Download selected invoices as one CSV of line items."""
	if doctype == "Salary Slip":
		from hrms.payroll.salary_slip_export import download_csv as download_salary_slip_csv

		return download_salary_slip_csv(doctype, names)

	invoices = _load_invoices(doctype, names)
	config = ALLOWED_DOCTYPES[doctype]
	rows = _csv_rows(doctype, invoices)
	_respond_file(_download_filename(invoices, config["file_stem"], "csv"), _csv_bytes(rows))


@frappe.whitelist()
def download_pdf(doctype: str, names: str | list | None = None) -> None:
	"""Download selected invoices as one branded PDF."""
	if doctype == "Salary Slip":
		from hrms.payroll.salary_slip_export import download_pdf as download_salary_slip_pdf

		return download_salary_slip_pdf(doctype, names)

	invoices = _load_invoices(doctype, names)
	config = ALLOWED_DOCTYPES[doctype]
	_respond_file(
		_download_filename(invoices, config["file_stem"], "pdf"),
		get_pdf(_render_pdf_html(doctype, invoices)),
	)


@frappe.whitelist()
def download_zip(doctype: str, names: str | list | None = None) -> None:
	"""Download one CSV per selected invoice, packed as a ZIP."""
	if doctype == "Salary Slip":
		from hrms.payroll.salary_slip_export import download_zip as download_salary_slip_zip

		return download_salary_slip_zip(doctype, names)

	invoices = _load_invoices(doctype, names)
	config = ALLOWED_DOCTYPES[doctype]
	if len(invoices) < 2:
		frappe.throw(_("Select more than one {0} to export a ZIP of CSV files.").format(config["label"]))

	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
		used_names = set()
		for invoice in invoices:
			filename = _unique_zip_name(_invoice_filename(invoice, "csv"), used_names)
			archive.writestr(filename, _csv_bytes(_csv_rows(doctype, [invoice])))

	_respond_file(f"{config['file_stem']}.zip", buffer.getvalue())


def _render_pdf_html(doctype: str, invoices: list[dict]) -> str:
	config = ALLOWED_DOCTYPES[doctype]
	return frappe.render_template(
		"hrms/payroll/invoice_export.html",
		{
			"title": config["plural"] if len(invoices) > 1 else config["label"],
			"logo": staff_pro_logo_url(),
			"generated_on": formatdate(getdate()),
			"invoices": [_pdf_invoice(invoice) for invoice in invoices],
		},
	)


def _load_invoices(doctype: str, names: str | list | None) -> list[dict]:
	if doctype not in ALLOWED_DOCTYPES:
		frappe.throw(_("Invalid invoice type"))
	_assert_can_export(doctype)

	selected = _as_list(names)
	if not selected:
		frappe.throw(_("Select at least one {0} to export.").format(ALLOWED_DOCTYPES[doctype]["label"]))

	docs = []
	seen = set()
	for name in selected:
		if name in seen:
			continue
		seen.add(name)
		if not frappe.db.exists(doctype, name):
			frappe.throw(_("{0} {1} does not exist").format(ALLOWED_DOCTYPES[doctype]["label"], name))
		docs.append(_serialize_invoice(frappe.get_doc(doctype, name)))
	return docs


def _serialize_invoice(doc) -> dict:
	if doc.doctype == "Client Invoice":
		rows = [
			{
				"code": row.employee,
				"description": row.employee_name or row.employee,
				"hours": flt(row.hours),
				"rate": flt(row.billing_rate),
				"amount": flt(row.amount),
			}
			for row in doc.agents
		]
		return {
			"doctype": doc.doctype,
			"name": doc.name,
			"client": doc.customer_name or doc.customer,
			"company": doc.company,
			"from_date": doc.from_date,
			"to_date": doc.to_date,
			"posting_date": doc.posting_date,
			"due_date": None,
			"status": doc.status,
			"outstanding": None,
			"currency": doc.currency or "USD",
			"total_hours": flt(doc.total_hours),
			"total_amount": flt(doc.total_amount),
			"period_label": _period_label(doc.from_date, doc.to_date),
			"rows": rows,
		}

	rows = [
		{
			"code": row.item_code,
			"description": row.item_name or row.description or row.item_code,
			"hours": flt(row.qty),
			"rate": flt(row.rate),
			"amount": flt(row.amount),
		}
		for row in doc.items
	]
	from_date = doc.get("billing_from") or doc.get("from_date")
	to_date = doc.get("billing_to") or doc.get("to_date")
	return {
		"doctype": doc.doctype,
		"name": doc.name,
		"client": doc.customer_name or doc.customer,
		"company": doc.company,
		"from_date": from_date,
		"to_date": to_date,
		"posting_date": doc.posting_date,
		"due_date": doc.due_date,
		"status": doc.status,
		"outstanding": flt(doc.outstanding_amount),
		"currency": doc.currency or "USD",
		"total_hours": flt(doc.total_qty),
		"total_amount": flt(doc.grand_total),
		"period_label": _period_label(from_date, to_date),
		"rows": rows,
	}


def _pdf_invoice(invoice: dict) -> dict:
	currency = invoice["currency"]
	return {
		**invoice,
		"is_posted": invoice["doctype"] == "Sales Invoice",
		"status_label": _(invoice["status"]) if invoice.get("status") else "",
		"posting_date_label": formatdate(invoice["posting_date"]) if invoice.get("posting_date") else "",
		"due_date_label": formatdate(invoice["due_date"]) if invoice.get("due_date") else "",
		"outstanding_label": (
			_money(invoice.get("outstanding"), currency)
			if invoice.get("outstanding") is not None
			else ""
		),
		"total_hours_label": _hours(invoice["total_hours"]),
		"total_amount_label": _money(invoice["total_amount"], currency),
		"rows": [
			{
				**row,
				"hours_label": _hours(row["hours"]),
				"rate_label": _money(row["rate"], currency),
				"amount_label": _money(row["amount"], currency),
			}
			for row in invoice["rows"]
		],
	}


def _csv_rows(doctype: str, invoices: list[dict]) -> list[list]:
	if doctype == "Client Invoice":
		headers = [
			_("Invoice"),
			_("Client"),
			_("Company"),
			_("From Date"),
			_("To Date"),
			_("Posting Date"),
			_("Status"),
			_("Agent"),
			_("Agent Name"),
			_("Hours"),
			_("Billing Rate"),
			_("Amount"),
			_("Currency"),
		]
		rows = [headers]
		for invoice in invoices:
			if invoice["rows"]:
				for row in invoice["rows"]:
					rows.append(
						[
							invoice["name"],
							invoice["client"],
							invoice["company"],
							invoice["from_date"] or "",
							invoice["to_date"] or "",
							invoice["posting_date"] or "",
							invoice["status"] or "",
							row["code"] or "",
							row["description"] or "",
							row["hours"],
							row["rate"],
							row["amount"],
							invoice["currency"],
						]
					)
			else:
				rows.append(
					[
						invoice["name"],
						invoice["client"],
						invoice["company"],
						invoice["from_date"] or "",
						invoice["to_date"] or "",
						invoice["posting_date"] or "",
						invoice["status"] or "",
						"",
						"",
						invoice["total_hours"],
						"",
						invoice["total_amount"],
						invoice["currency"],
					]
				)
		return rows

	headers = [
		_("Invoice"),
		_("Client"),
		_("Company"),
		_("Invoice Date"),
		_("Billing From"),
		_("Billing To"),
		_("Status"),
		_("Outstanding"),
		_("Description"),
		_("Hours"),
		_("Billing Rate"),
		_("Amount"),
		_("Currency"),
	]
	rows = [headers]
	for invoice in invoices:
		if invoice["rows"]:
			for row in invoice["rows"]:
				rows.append(
					[
						invoice["name"],
						invoice["client"],
						invoice["company"],
						invoice["posting_date"] or "",
						invoice["from_date"] or "",
						invoice["to_date"] or "",
						invoice["status"] or "",
						invoice["outstanding"],
						row["description"] or "",
						row["hours"],
						row["rate"],
						row["amount"],
						invoice["currency"],
					]
				)
		else:
			rows.append(
				[
					invoice["name"],
					invoice["client"],
					invoice["company"],
					invoice["posting_date"] or "",
					invoice["from_date"] or "",
					invoice["to_date"] or "",
					invoice["status"] or "",
					invoice["outstanding"],
					"",
					invoice["total_hours"],
					"",
					invoice["total_amount"],
					invoice["currency"],
				]
			)
	return rows


def _money(value, currency: str) -> str:
	return fmt_money(flt(value), currency=currency)


def _hours(value) -> str:
	return frappe.format_value(flt(value), {"fieldtype": "Float"})


def _period_label(from_date, to_date) -> str:
	if from_date and to_date:
		return _("{0} to {1}").format(formatdate(from_date), formatdate(to_date))
	if from_date:
		return formatdate(from_date)
	if to_date:
		return formatdate(to_date)
	return ""


def _download_filename(invoices: list[dict], stem: str, extension: str) -> str:
	if len(invoices) == 1:
		return _invoice_filename(invoices[0], extension)
	return f"{stem}.{extension}"


def _invoice_filename(invoice: dict, extension: str) -> str:
	client = _safe_filename(invoice.get("client") or "Invoice")
	name = _safe_filename(invoice.get("name") or "invoice")
	return f"{client}_{name}.{extension}"


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
	return cleaned.strip().replace(" ", "_") or "invoice"


def _csv_bytes(rows: list) -> str:
	return to_csv(rows)


def _respond_file(filename: str, content, file_type: str = "binary"):
	frappe.response["filename"] = filename
	frappe.response["filecontent"] = content
	frappe.response["type"] = file_type


def _assert_can_export(doctype: str):
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not frappe.permissions.can_export(doctype):
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
