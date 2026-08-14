import frappe

from hrms.branding import apply_branding


def execute():
	_rename_desktop_icon()
	apply_branding()


def _rename_desktop_icon():
	old_name = "Frappe HR"
	new_name = "Staff Pro BPO"

	if not frappe.db.exists("Desktop Icon", old_name):
		return

	if frappe.db.exists("Desktop Icon", new_name):
		frappe.db.sql(
			"update `tabDesktop Icon` set parent_icon = %s where parent_icon = %s",
			(new_name, old_name),
		)
		frappe.delete_doc("Desktop Icon", old_name, force=True, ignore_permissions=True)
		return

	frappe.rename_doc("Desktop Icon", old_name, new_name, force=True)
	frappe.db.sql(
		"update `tabDesktop Icon` set parent_icon = %s where parent_icon = %s",
		(new_name, old_name),
	)
