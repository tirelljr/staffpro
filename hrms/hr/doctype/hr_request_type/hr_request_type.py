# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

DEFAULT_HR_REQUEST_TYPES = (
	("Job Letter", "Request an employment or job letter for banks, visas, or other official use."),
	("Employment Verification", "Ask HR to confirm employment details for a third party."),
	("Address / Personal Details Update", "Request a change to address, name, or other personal details."),
	("General Inquiry", "Send a general question or request to the HR team."),
)


class HRRequestType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.Text | None
		request_type_name: DF.Data
	# end: auto-generated types

	pass


def seed_hr_request_types() -> None:
	for name, description in DEFAULT_HR_REQUEST_TYPES:
		if frappe.db.exists("HR Request Type", name):
			continue
		frappe.get_doc(
			{
				"doctype": "HR Request Type",
				"request_type_name": name,
				"description": description,
			}
		).insert(ignore_permissions=True)
