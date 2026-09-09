# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt

DEFAULT_BONUS_TYPES = (
	("Performance Bonus", "Awarded for meeting or exceeding performance targets."),
	("Attendance Bonus", "Awarded for meeting attendance or punctuality goals."),
	("Referral Bonus", "Awarded for referring a hired candidate."),
	("Holiday Bonus", "Seasonal or holiday bonus paid with regular wages."),
	("Other", "Any other one-time bonus added to gross pay."),
)

ATTENDANCE_BONUS_DEFAULTS = {
	"auto_calculate": 1,
	"period_months": 3,
	"attendance_target": 90,
	"if_below": "No Bonus",
}

BONUS_SALARY_COMPONENT = "Bonus"
ATTENDANCE_DEDUCTION_COMPONENT = "Attendance Deduction"


class BonusType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		attendance_target: DF.Percent
		auto_calculate: DF.Check
		bonus_amount: DF.Currency
		bonus_type_name: DF.Data
		description: DF.SmallText | None
		disabled: DF.Check
		if_below: DF.Literal["No Bonus", "Deduct"]
		period_months: DF.Int
	# end: auto-generated types

	def validate(self):
		if not cint(self.auto_calculate):
			return
		if cint(self.period_months) < 1:
			frappe.throw(frappe._("Default Over Months must be at least 1"))
		if flt(self.attendance_target) <= 0 or flt(self.attendance_target) > 100:
			frappe.throw(frappe._("Default Attendance Target must be between 1 and 100"))
		if flt(self.bonus_amount) < 0:
			frappe.throw(frappe._("Default Bonus Amount cannot be negative"))


def seed_bonus_types() -> None:
	if not frappe.db.table_exists("Bonus Type"):
		return

	ensure_bonus_salary_component()
	ensure_attendance_deduction_component()

	for name, description in DEFAULT_BONUS_TYPES:
		if frappe.db.exists("Bonus Type", name):
			continue
		values = {
			"doctype": "Bonus Type",
			"bonus_type_name": name,
			"description": description,
		}
		if name == "Attendance Bonus":
			values.update(ATTENDANCE_BONUS_DEFAULTS)
		frappe.get_doc(values).insert(ignore_permissions=True)


def configure_attendance_bonus_defaults() -> None:
	if not frappe.db.exists("Bonus Type", "Attendance Bonus"):
		return

	doc = frappe.get_doc("Bonus Type", "Attendance Bonus")
	changed = False
	if not cint(doc.auto_calculate):
		doc.auto_calculate = 1
		changed = True
	if not cint(doc.period_months):
		doc.period_months = ATTENDANCE_BONUS_DEFAULTS["period_months"]
		changed = True
	if not flt(doc.attendance_target):
		doc.attendance_target = ATTENDANCE_BONUS_DEFAULTS["attendance_target"]
		changed = True
	if not doc.if_below:
		doc.if_below = ATTENDANCE_BONUS_DEFAULTS["if_below"]
		changed = True
	if changed:
		doc.save(ignore_permissions=True)


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


def ensure_attendance_deduction_component() -> str:
	if frappe.db.exists("Salary Component", ATTENDANCE_DEDUCTION_COMPONENT):
		return ATTENDANCE_DEDUCTION_COMPONENT

	if not frappe.db.table_exists("Salary Component"):
		return ATTENDANCE_DEDUCTION_COMPONENT

	doc = frappe.get_doc(
		{
			"doctype": "Salary Component",
			"salary_component": ATTENDANCE_DEDUCTION_COMPONENT,
			"salary_component_abbr": "ATD",
			"type": "Deduction",
			"is_tax_applicable": 0,
			"depends_on_payment_days": 0,
			"do_not_include_in_total": 0,
			"description": "Attendance shortfall taken from pay when the agent is below their user bonus target.",
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return ATTENDANCE_DEDUCTION_COMPONENT
