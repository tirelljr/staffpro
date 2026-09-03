"""Seed HR Request types, ESS permissions, and People sidebar links."""

import frappe

from hrms.hr.doctype.hr_request_type.hr_request_type import seed_hr_request_types
from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars


def execute():
	if frappe.db.table_exists("HR Request Type"):
		seed_hr_request_types()

	_add_ess_permissions()

	try:
		sync_staff_pro_sidebars()
	except Exception:
		frappe.log_error(title="HR Request sidebar sync")


def _add_ess_permissions():
	if not frappe.db.exists("User Type", "Employee Self Service"):
		return

	doc = frappe.get_doc("User Type", "Employee Self Service")
	kept = []
	existing = set()
	changed = False

	for row in doc.user_doctypes:
		if not frappe.db.exists("DocType", row.document_type):
			changed = True
			continue
		kept.append(row)
		existing.add(row.document_type)

	doc.user_doctypes = kept

	if "HR Request" not in existing:
		doc.append(
			"user_doctypes",
			{"document_type": "HR Request", "read": 1, "write": 1, "create": 1, "delete": 1},
		)
		changed = True

	if "HR Request Type" not in existing:
		doc.append("user_doctypes", {"document_type": "HR Request Type", "read": 1})
		changed = True

	if changed:
		doc.flags.ignore_links = True
		doc.save()
