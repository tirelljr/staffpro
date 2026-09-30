# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Add the Documents tab to the Employee form, before Profile."""

from hrms.hr.agent_filesystem import ensure_employee_documents_tab


def execute():
	ensure_employee_documents_tab()
