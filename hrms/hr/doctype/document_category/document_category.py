# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document

DEFAULT_DOCUMENT_CATEGORIES = (
	("Social Security", "Social security card or number documentation.", 1),
	("Job Letter", "Employment or job letters.", 2),
	("Bank Salary Declaration", "Bank salary declaration letters.", 3),
	("Identification", "Government IDs and identification documents.", 4),
	("Writeups", "Performance writeups and disciplinary notes.", 5),
	("Other", "Other agent documents.", 6),
	("Tax Forms", "Signed TD4 and other tax forms.", 7),
)


class DocumentCategory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		category_name: DF.Data
		description: DF.Text | None
		sort_order: DF.Int
	# end: auto-generated types

	pass


def seed_document_categories() -> None:
	if not frappe.db.table_exists("Document Category"):
		return
	for name, description, sort_order in DEFAULT_DOCUMENT_CATEGORIES:
		if frappe.db.exists("Document Category", name):
			continue
		try:
			frappe.get_doc(
				{
					"doctype": "Document Category",
					"category_name": name,
					"description": description,
					"sort_order": sort_order,
				}
			).insert(ignore_permissions=True, ignore_if_duplicate=True)
		except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
			frappe.clear_last_message()
