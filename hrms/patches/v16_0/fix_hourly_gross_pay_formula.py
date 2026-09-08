# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Pay hourly agents from hours × rate instead of a day-prorated weekly base."""


def execute():
	from hrms.payroll.hourly_gross import sync_hourly_gross_formula

	sync_hourly_gross_formula()
