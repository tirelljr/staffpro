# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Relabel Employee Grade to Campaign on agent and payroll forms."""

from hrms.hr.bpo_employee_labels import apply_bpo_employee_labels


def execute():
	apply_bpo_employee_labels()
