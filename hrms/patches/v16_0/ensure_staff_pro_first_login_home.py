# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from hrms.boot import prepare_staff_pro_first_login


def execute():
	"""First desk login after setup must open the custom BPO home, not apps/HR."""
	prepare_staff_pro_first_login()
