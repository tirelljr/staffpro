# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Add the Talent Filesystem page and seed agent document categories."""

import frappe

from hrms.hr.doctype.document_category.document_category import seed_document_categories
from hrms.hr.staff_pro_sidebars import sync_staff_pro_sidebars


def execute():
	seed_document_categories()
	try:
		sync_staff_pro_sidebars()
	except Exception:
		frappe.log_error(title="Agent Filesystem sidebar sync")
