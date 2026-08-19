# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class EmployeeTaxAdjustment(Document):
	def validate(self):
		self.validate_period_dates()
		self.validate_employees()
		self.validate_include_fields()
		self.prevent_duplicate_employees()

	def validate_period_dates(self):
		period = frappe.get_cached_doc("Payroll Period", self.payroll_period)
		if period.company and period.company != self.company:
			frappe.throw(_("Tax Period {0} does not belong to Company {1}").format(self.payroll_period, self.company))

		period_start = getdate(period.start_date)
		period_end = getdate(period.end_date)
		valid_from = getdate(self.valid_from) if self.valid_from else period_start
		valid_to = getdate(self.valid_to) if self.valid_to else period_end

		if valid_from > valid_to:
			frappe.throw(_("Valid From cannot be after Valid To"))
		if valid_from < period_start or valid_to > period_end:
			frappe.throw(_("Validity dates must fall within Tax Period {0} ({1} to {2})").format(
				self.payroll_period, period.start_date, period.end_date
			))

		if not self.valid_from:
			self.valid_from = period_start
		if not self.valid_to:
			self.valid_to = period_end

	def validate_employees(self):
		if not self.employees:
			frappe.throw(_("Add at least one agent"))

		seen = set()
		for row in self.employees:
			if row.employee in seen:
				frappe.throw(_("Agent {0} is listed more than once").format(row.employee_name or row.employee))
			seen.add(row.employee)
			company = frappe.db.get_value("Employee", row.employee, "company")
			if company and company != self.company:
				frappe.throw(_("Agent {0} does not belong to Company {1}").format(
					row.employee_name or row.employee, self.company
				))

	def validate_include_fields(self):
		if self.adjustment_type != "Include in Tax Period":
			return
		if self.tax_amount_override and self.tax_amount_override < 0:
			frappe.throw(_("Tax Amount Override cannot be negative"))

	def prevent_duplicate_employees(self):
		employees = [row.employee for row in self.employees]
		if not employees:
			return

		Adjustment = frappe.qb.DocType("Employee Tax Adjustment")
		Detail = frappe.qb.DocType("Employee Tax Adjustment Employee")
		query = (
			frappe.qb.from_(Adjustment)
			.join(Detail)
			.on(Detail.parent == Adjustment.name)
			.select(Detail.employee, Adjustment.name)
			.where(Adjustment.docstatus == 1)
			.where(Adjustment.company == self.company)
			.where(Adjustment.payroll_period == self.payroll_period)
			.where(Adjustment.adjustment_type == self.adjustment_type)
			.where(Detail.employee.isin(employees))
		)
		if not self.is_new():
			query = query.where(Adjustment.name != self.name)

		overlaps = query.run(as_dict=True)
		if not overlaps:
			return

		valid_from = getdate(self.valid_from)
		valid_to = getdate(self.valid_to)
		for row in overlaps:
			other = frappe.db.get_value(
				"Employee Tax Adjustment",
				row.name,
				["valid_from", "valid_to"],
				as_dict=True,
			)
			if not other:
				continue
			other_from = getdate(other.valid_from)
			other_to = getdate(other.valid_to)
			if other_from <= valid_to and other_to >= valid_from:
				frappe.throw(
					_("Agent {0} already has a submitted {1} for this tax period ({2})").format(
						row.employee, self.adjustment_type, row.name
					)
				)
