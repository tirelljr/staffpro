# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.model.document import Document


class AISettings(Document):
	def validate(self):
		if self.model == "deepseek-reasoner":
			frappe.throw(_("Ask AI requires a DeepSeek model that supports tool calling. Use deepseek-chat."))
		if not self.api_base or urlparse(self.api_base).scheme not in {"http", "https"}:
			frappe.throw(_("API Base URL must be a valid HTTP or HTTPS URL."))
		if not 1 <= (self.max_tool_rounds or 0) <= 12:
			frappe.throw(_("Maximum Tool Rounds must be between 1 and 12."))
