import frappe

from hrms.boot import STAFF_PRO_DESK_HOME


def execute():
	"""Ensure Staff Pro BPO opens the Human Resource dashboard, not the Workforce workspace."""
	link = f"/{STAFF_PRO_DESK_HOME}"
	if frappe.db.exists("Desktop Icon", "Staff Pro BPO"):
		frappe.db.set_value(
			"Desktop Icon",
			"Staff Pro BPO",
			"link",
			link,
			update_modified=False,
		)
