# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Hide ERPNext modules from Desk so nav stays call-center BPO focused."""


def execute():
	from hrms.boot import hide_unused_erpnext_workspaces

	hide_unused_erpnext_workspaces()
