"""Remove unused People, Pay, and SS and Taxes sidebar links on existing sites."""

from hrms.patches.v16_0 import apply_bpo_sidebar_labels as sync


def execute():
	sync.execute()
