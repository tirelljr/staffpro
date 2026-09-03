# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Create Social Security Payable and map it on SS salary components."""

from hrms.payroll.social_security import ensure_ss_salary_components


def execute():
	ensure_ss_salary_components()
