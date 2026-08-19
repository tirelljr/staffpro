# Copyright (c) 2026, Staff Pro BPO and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SocialSecurityContributionSchedule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from hrms.payroll.doctype.social_security_wage_band.social_security_wage_band import (
			SocialSecurityWageBand,
		)

		company: DF.Link | None
		currency: DF.Link | None
		disabled: DF.Check
		effective_from: DF.Date
		injury_only_employee_amount: DF.Currency
		injury_only_employer_amount: DF.Currency
		wage_bands: DF.Table[SocialSecurityWageBand]
	# end: auto-generated types

	def validate(self):
		self.validate_wage_bands()

	def validate_wage_bands(self):
		if not self.wage_bands:
			frappe.throw(_("Please add at least one wage band."))

		previous_to = None
		for idx, band in enumerate(self.wage_bands):
			from_amt = flt(band.from_weekly_earnings)
			to_amt = flt(band.to_weekly_earnings) if band.to_weekly_earnings is not None else None

			if to_amt is not None and to_amt and from_amt > to_amt:
				frappe.throw(
					_("Row #{0}: From Weekly Earnings cannot be greater than To Weekly Earnings.").format(
						idx + 1
					)
				)

			if previous_to is not None and from_amt < previous_to:
				frappe.throw(
					_("Row #{0}: Wage bands must be in ascending order without overlapping ranges.").format(
						idx + 1
					)
				)

			previous_to = to_amt if to_amt else from_amt
