# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from frappe.model.document import Document


class SocialSecurityWageBand(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		band_label: DF.Data
		employee_amount: DF.Currency
		employer_amount: DF.Currency
		from_weekly_earnings: DF.Currency
		insurable_earnings: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		to_weekly_earnings: DF.Currency
	# end: auto-generated types

	pass
