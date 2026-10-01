import frappe


def run():
	frappe.set_user("Administrator")
	print("ESS desk", frappe.db.get_value("Role", "Employee Self Service", "desk_access"))
	print("Employee desk", frappe.db.get_value("Role", "Employee", "desk_access"))
	staff = (
		"System Manager",
		"HR Manager",
		"HR User",
		"Accounts Manager",
		"Accounts User",
		"Payroll Manager",
		"Payroll User",
		"Workspace Manager",
	)
	print("Remaining agent System Users")
	for user in frappe.get_all(
		"User",
		filters={"user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]},
		fields=["name", "full_name"],
	):
		roles = set(frappe.get_roles(user.name))
		if roles.intersection(staff):
			continue
		if roles.intersection({"Employee", "Employee Self Service"}) or frappe.db.exists(
			"Employee", {"user_id": user.name}
		):
			print(user)
	print("Website users")
	for row in frappe.get_all(
		"User",
		filters={"user_type": "Website User", "enabled": 1},
		fields=["name", "full_name"],
		limit=12,
	):
		print(row)
