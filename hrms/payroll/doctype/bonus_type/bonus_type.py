# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

DEFAULT_BONUS_TYPES = (
	("Performance Bonus", "Awarded for meeting or exceeding performance targets."),
	("Attendance Bonus", "Awarded for meeting attendance or punctuality goals."),
	("Referral Bonus", "Awarded for referring a hired candidate."),
	("Holiday Bonus", "Seasonal or holiday bonus paid with regular wages."),
	("Other", "Any other one-time bonus added to gross pay."),
)

BONUS_SALARY_COMPONENT = "Bonus"


class BonusType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bonus_type_name: DF.Data
		description: DF.SmallText | None
		disabled: DF.Check
	# end: auto-generated types

	pass


def seed_bonus_types() -> None:
	if not frappe.db.table_exists("Bonus Type"):
		return

	ensure_bonus_salary_component()

	for name, description in DEFAULT_BONUS_TYPES:
		if frappe.db.exists("Bonus Type", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Bonus Type",
				"bonus_type_name": name,
				"description": description,
			}
		).insert(ignore_permissions=True)


def ensure_bonus_salary_component() -> str:
	"""Payroll still posts bonuses through the Bonus earning so they hit gross pay."""
	if frappe.db.exists("Salary Component", BONUS_SALARY_COMPONENT):
		return BONUS_SALARY_COMPONENT

	if not frappe.db.table_exists("Salary Component"):
		return BONUS_SALARY_COMPONENT

	doc = frappe.get_doc(
		{
			"doctype": "Salary Component",
			"salary_component": BONUS_SALARY_COMPONENT,
			"salary_component_abbr": "BNS",
			"type": "Earning",
			"is_tax_applicable": 1,
			"earning_category": "Bonus",
			"depends_on_payment_days": 0,
			"do_not_include_in_total": 0,
			"description": "Bonus added to gross pay for the payroll period.",
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return BONUS_SALARY_COMPONENT
