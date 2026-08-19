import frappe


def execute():
	"""Hide legacy People workspace; Workforce is the canonical dock item labeled People."""
	if frappe.db.exists("Workspace", "People"):
		frappe.db.set_value(
			"Workspace",
			"People",
			{"is_hidden": 1, "public": 0},
			update_modified=False,
		)
