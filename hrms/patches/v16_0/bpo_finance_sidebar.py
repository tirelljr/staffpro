# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Replace ERPNext accounting links on Finance with call-center BPO billing."""

from hrms.patches.v16_0.apply_bpo_sidebar_labels import execute as sync_sidebars


def execute():
	sync_sidebars()
