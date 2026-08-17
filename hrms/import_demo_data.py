"""Import ERPNext demo data for the existing company."""

import frappe


def run():
	company_name = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company_name:
		companies = frappe.get_all("Company", pluck="name", limit=1)
		if not companies:
			print("No company found. Complete setup wizard first.")
			return
		company_name = companies[0]

	demo_company = frappe.db.get_single_value("Global Defaults", "demo_company")
	if demo_company and frappe.db.exists("Company", demo_company):
		print(f"Demo company already exists: {demo_company}")
		return

	print(f"Creating demo data from company: {company_name}")
	from erpnext.setup.demo import setup_demo_data

	setup_demo_data(company_name)
	frappe.db.commit()

	demo_company = frappe.db.get_single_value("Global Defaults", "demo_company")
	print(f"Demo data import complete. Demo company: {demo_company}")


def status():
	for doctype in ("Company", "Employee", "Item", "Customer", "Supplier", "Sales Order", "Purchase Order"):
		print(f"{doctype}: {frappe.db.count(doctype)}")
