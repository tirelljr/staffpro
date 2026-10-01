# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document


class MasterKeySettings(Document):
	def onload(self):
		self.key_hash = None

	def as_dict(self, *args, **kwargs):
		data = super().as_dict(*args, **kwargs)
		data["key_hash"] = None
		return data

	def validate(self):
		if self.flags.get("allow_master_key_update"):
			return
		for field in ("key_hash", "key_configured", "lock_status", "locked_until", "locked_by", "locked_on"):
			self.set(field, frappe.db.get_single_value("Master Key Settings", field))
