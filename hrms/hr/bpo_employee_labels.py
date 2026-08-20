# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Relabel Employee salary fields for BPO hourly pay (not India CTC/PAN)."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

EMPLOYEE_FIELD_LABELS = {
	"ctc": "Agent Hourly",
	"pan_number": "Tax Number",
	"designation": "Role",
}

OTHER_DOCTYPE_FIELD_LABELS = {
	"Salary Structure Assignment": {"ctc": "Agent Hourly"},
	"Salary Slip": {"ctc": "Agent Hourly"},
	"Employee Promotion": {
		"current_ctc": "Current Agent Hourly",
		"revised_ctc": "Revised Agent Hourly",
	},
	"Designation": {"designation_name": "Role"},
}


def apply_bpo_employee_labels():
	_relabel_fields("Employee", EMPLOYEE_FIELD_LABELS)
	_sync_custom_field_labels("Employee", EMPLOYEE_FIELD_LABELS)

	for doctype, labels in OTHER_DOCTYPE_FIELD_LABELS.items():
		_relabel_fields(doctype, labels)

	for doctype in ["Employee", *OTHER_DOCTYPE_FIELD_LABELS]:
		if frappe.db.exists("DocType", doctype):
			frappe.clear_cache(doctype=doctype)


def _relabel_fields(doctype: str, labels: dict[str, str]):
	if not frappe.db.exists("DocType", doctype):
		return

	meta = frappe.get_meta(doctype)
	for fieldname, label in labels.items():
		if not meta.has_field(fieldname):
			continue
		make_property_setter(
			doctype,
			fieldname,
			"label",
			label,
			"Data",
			validate_fields_for_doctype=False,
		)


def _sync_custom_field_labels(doctype: str, labels: dict[str, str]):
	for fieldname, label in labels.items():
		name = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": fieldname}, "name")
		if not name:
			continue
		frappe.db.set_value("Custom Field", name, "label", label, update_modified=False)
