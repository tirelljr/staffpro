# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Rename Cost to Company (CTC) to Agent Hourly and PAN Number to Tax Number."""

from hrms.hr.bpo_employee_labels import apply_bpo_employee_labels


def execute():
	apply_bpo_employee_labels()
