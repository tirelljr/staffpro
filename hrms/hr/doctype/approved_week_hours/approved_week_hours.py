# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class ApprovedWeekHours(Document):
	def validate(self):
		from hrms.payroll.daily_pay import week_bounds

		if not self.employee or not self.week_start:
			frappe.throw(_("Employee and week are required."))
		start, _end = week_bounds(self.week_start)
		self.week_start = getdate(start)
		if flt(self.hours) < 0:
			frappe.throw(_("Hours cannot be negative."))
		self.hours = flt(self.hours, 2)
		if not self.employee_name:
			self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")
		duplicate = frappe.db.get_value(
			"Approved Week Hours",
			{"employee": self.employee, "week_start": self.week_start, "name": ["!=", self.name]},
			"name",
		)
		if duplicate:
			frappe.throw(_("Approved hours for this agent and week already exist."))
