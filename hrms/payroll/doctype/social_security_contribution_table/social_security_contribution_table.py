# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SocialSecurityContributionTable(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from hrms.payroll.doctype.social_security_wage_band.social_security_wage_band import (
			SocialSecurityWageBand,
		)

		bands: DF.Table[SocialSecurityWageBand]
		company: DF.Link | None
		currency: DF.Link | None
		disabled: DF.Check
		effective_from: DF.Date
		injury_only_employee_amount: DF.Currency
		injury_only_employer_amount: DF.Currency
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		if not self.bands:
			frappe.throw(_("Add at least one wage band."))
		self._validate_band_ranges()

	def _validate_band_ranges(self):
		sorted_bands = sorted(self.bands, key=lambda row: flt(row.from_weekly_earnings))
		for row in sorted_bands:
			if flt(row.to_weekly_earnings) and flt(row.to_weekly_earnings) < flt(row.from_weekly_earnings):
				frappe.throw(
					_("Wage band {0}: To Weekly Earnings cannot be less than From Weekly Earnings.").format(
						row.band_label or row.idx
					)
				)
