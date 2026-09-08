"""Seed bonus types and the hidden Bonus salary component used for payroll."""

import frappe

from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars
from hrms.payroll.doctype.bonus_type.bonus_type import seed_bonus_types


def execute():
	if frappe.db.table_exists("Bonus Type"):
		seed_bonus_types()

	try:
		sync_staff_pro_sidebars()
	except Exception:
		frappe.log_error(title="Bonus Type sidebar sync")
