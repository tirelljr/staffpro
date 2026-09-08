# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Hourly gross pay: regular hours × rate + overtime × 1.5 + holiday + bonus."""

from __future__ import annotations

import frappe
from frappe.utils import flt

HOURLY_BASIC_COMPONENT = "Basic Hourly"
OVERTIME_MULTIPLIER = 1.5
HOURLY_GROSS_FORMULA = "hour_rate * total_working_hours if total_working_hours else base"


def compute_hourly_gross_pay(
	regular_hours=0,
	overtime_hours=0,
	hourly_rate=0,
	holiday_pay=0,
	bonus=0,
	overtime_multiplier=OVERTIME_MULTIPLIER,
) -> float:
	"""Gross from the payroll spreadsheet inputs, rounded to cents."""
	return flt(
		flt(regular_hours) * flt(hourly_rate)
		+ flt(overtime_hours) * flt(hourly_rate) * flt(overtime_multiplier)
		+ flt(holiday_pay)
		+ flt(bonus),
		2,
	)


def is_hourly_basic_component(name: str | None) -> bool:
	return (name or "").strip() == HOURLY_BASIC_COMPONENT


def structure_uses_hourly_wages(salary_structure: str | None) -> bool:
	if not salary_structure or not frappe.db.exists("Salary Structure", salary_structure):
		return False
	return bool(
		frappe.db.exists(
			"Salary Detail",
			{
				"parent": salary_structure,
				"parenttype": "Salary Structure",
				"parentfield": "earnings",
				"salary_component": HOURLY_BASIC_COMPONENT,
			},
		)
	)


def slip_uses_hourly_wages(slip) -> bool:
	if not slip:
		return False
	if getattr(slip, "salary_slip_based_on_timesheet", None):
		return False
	earnings = slip.get("earnings") if hasattr(slip, "get") else getattr(slip, "earnings", None)
	if any(is_hourly_basic_component(getattr(row, "salary_component", None)) for row in (earnings or [])):
		return True
	return structure_uses_hourly_wages(getattr(slip, "salary_structure", None))


def sync_hourly_gross_formula(company=None, account=None, structure_name: str | None = None) -> None:
	"""Keep Basic Hourly on hours × rate, falling back to weekly base when hours are 0."""
	from frappe.utils import cint

	structure_name = structure_name or "Staff Pro Weekly"
	if frappe.db.exists("Salary Component", HOURLY_BASIC_COMPONENT):
		component = frappe.get_doc("Salary Component", HOURLY_BASIC_COMPONENT)
		changed = False
		if component.formula != HOURLY_GROSS_FORMULA or cint(component.depends_on_payment_days):
			component.formula = HOURLY_GROSS_FORMULA
			component.amount_based_on_formula = 1
			component.depends_on_payment_days = 0
			changed = True
		if (
			account
			and company
			and not frappe.db.exists(
				"Salary Component Account", {"parent": HOURLY_BASIC_COMPONENT, "company": company}
			)
		):
			component.append("accounts", {"company": company, "account": account})
			changed = True
		if changed:
			component.save(ignore_permissions=True)

	if not frappe.db.exists("Salary Structure", structure_name):
		return
	structure = frappe.get_doc("Salary Structure", structure_name)
	changed = False
	for row in structure.earnings or []:
		if not is_hourly_basic_component(row.salary_component):
			continue
		if row.formula != HOURLY_GROSS_FORMULA or cint(row.depends_on_payment_days):
			row.formula = HOURLY_GROSS_FORMULA
			row.amount_based_on_formula = 1
			row.depends_on_payment_days = 0
			changed = True
	if not changed:
		return
	if structure.docstatus == 1:
		structure.db_update()
		for row in structure.earnings:
			row.db_update()
	else:
		structure.save(ignore_permissions=True)
