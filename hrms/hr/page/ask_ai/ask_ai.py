# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from hrms.ai.permissions import ensure_ai_access


def get_context(context):
	ensure_ai_access()
	return context
