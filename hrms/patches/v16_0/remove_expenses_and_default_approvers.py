"""Hide expense claiming and point blank leave and shift approvers at the HR manager."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.overrides.employee_master import get_default_hr_approver
from hrms.setup import get_custom_fields


def execute():
	_hide_expense_fields()
	_backfill_approvers()
	from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars

	sync_staff_pro_sidebars()
	frappe.clear_cache()


def _hide_expense_fields():
	wanted = {"expense_approver", "expense_approvers"}
	custom_fields = get_custom_fields()
	to_update = {}
	for doctype in ("Employee", "Department"):
		rows = [row for row in custom_fields.get(doctype, []) if row.get("fieldname") in wanted]
		if rows:
			to_update[doctype] = rows
	if to_update:
		create_custom_fields(to_update, ignore_validate=True, update=True)


def _backfill_approvers():
	approver = get_default_hr_approver()
	if not approver or not frappe.db.table_exists("Employee"):
		return

	for fieldname in ("leave_approver", "shift_request_approver"):
		if not frappe.db.has_column("Employee", fieldname):
			continue
		frappe.db.sql(
			f"""
			UPDATE `tabEmployee`
			SET `{fieldname}` = %(approver)s
			WHERE IFNULL(`{fieldname}`, '') = ''
			""",
			{"approver": approver},
		)

	if frappe.db.exists("User", approver):
		user = frappe.get_doc("User", approver)
		user.flags.ignore_permissions = True
		user.add_roles("Leave Approver")
