"""Drop Expense Claim.vehicle_log before DocType sync.

Frappe refuses ALTER TABLE inside the sync transaction. If this leftover
column is still on the site, migrate dies during Updating DocTypes for hrms
with ImplicitCommitError and the progress bar looks frozen around 60-70%.
"""

import frappe


def execute():
	if not frappe.db.table_exists("Expense Claim"):
		return
	if not frappe.db.has_column("Expense Claim", "vehicle_log"):
		return
	frappe.db.sql_ddl("alter table `tabExpense Claim` drop column `vehicle_log`")
	frappe.clear_cache(doctype="Expense Claim")
