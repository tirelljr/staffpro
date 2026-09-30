# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Job letter defaults and the Office Print request type."""

import frappe

from hrms.hr.doctype.hr_request_type.hr_request_type import seed_hr_request_types
from hrms.hr.job_letter import ensure_letterhead_defaults


def execute():
	seed_hr_request_types()
	ensure_letterhead_defaults()
	frappe.clear_cache(doctype="HR Settings")
