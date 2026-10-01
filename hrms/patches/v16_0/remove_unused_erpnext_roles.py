# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Delete leftover ERPNext roles that block cleanup (Supplier, Customer, etc.)."""


def execute():
	from hrms.hr.bpo_user_permissions import remove_unused_erpnext_roles

	remove_unused_erpnext_roles()
