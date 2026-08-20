# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Remove Other Statutory (Provident Fund and Professional Tax) from SS and Taxes."""

from hrms.patches.v16_0.apply_bpo_sidebar_labels import execute as sync_sidebars


def execute():
	sync_sidebars()
