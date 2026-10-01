# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import unittest

from hrms.hr.master_key import (
	check_new_master_key,
	hash_master_key,
	is_master_key_sidebar_item,
	lock_is_active,
	master_key_link_allowed,
	user_can_manage_master_key,
	verify_master_key,
)


class TestMasterKey(unittest.TestCase):
	def test_hash_hides_the_key_and_checks_it(self):
		key = "correct horse battery"
		stored = hash_master_key(key)
		self.assertNotIn(key, stored)
		self.assertTrue(verify_master_key(key, stored))
		self.assertTrue(verify_master_key("  " + key + "  ", stored))
		self.assertFalse(verify_master_key("wrong horse battery", stored))
		self.assertFalse(verify_master_key("", stored))
		self.assertFalse(verify_master_key(key, ""))
		self.assertFalse(verify_master_key(key, stored + "ab"))
		self.assertNotEqual(hash_master_key(key), stored)

	def test_new_key_must_match_and_be_long_enough(self):
		ok, key, code = check_new_master_key("a" * 12, "a" * 12)
		self.assertTrue(ok)
		self.assertEqual(key, "a" * 12)
		self.assertEqual(code, "")
		self.assertEqual(check_new_master_key("short-key", "short-key")[2], "short")
		self.assertEqual(check_new_master_key("a" * 12, "b" * 12)[2], "mismatch")
		self.assertEqual(check_new_master_key("", "a" * 12)[2], "required")
		self.assertEqual(check_new_master_key("a" * 129, "a" * 129)[2], "long")

	def test_timed_lock_expires_and_manual_stays_on(self):
		self.assertFalse(lock_is_active("Off", None, "2026-10-01 12:00:00"))
		self.assertFalse(lock_is_active("", None, "2026-10-01 12:00:00"))
		self.assertTrue(lock_is_active("Manual", None, "2026-10-01 12:00:00"))
		self.assertTrue(lock_is_active("Until", "2026-10-01 12:00:00", "2026-10-01 11:59:59"))
		self.assertFalse(lock_is_active("Until", "2026-10-01 12:00:00", "2026-10-01 12:00:00"))
		self.assertFalse(lock_is_active("Until", "2026-10-01 12:00:00", "2026-10-01 13:00:00"))
		self.assertTrue(lock_is_active("Until", None, "2026-10-01 13:00:00"))
		self.assertTrue(lock_is_active("SomethingElse", None, "2026-10-01 13:00:00"))

	def test_only_system_managers_can_use_the_key(self):
		self.assertFalse(user_can_manage_master_key(None, ["System Manager"]))
		self.assertFalse(user_can_manage_master_key("Guest", ["System Manager"]))
		self.assertFalse(user_can_manage_master_key("", ["System Manager"]))
		self.assertFalse(user_can_manage_master_key("hr@example.com", ["HR Manager", "HR User"]))
		self.assertTrue(user_can_manage_master_key("admin@example.com", ["HR Manager", "System Manager"]))
		self.assertTrue(user_can_manage_master_key("Administrator", []))

	def test_sidebar_link_is_hidden_from_everyone_else(self):
		link = {"type": "Link", "label": "Master Key", "link_to": "master-key", "link_type": "Page"}
		section = {"type": "Section Break", "label": "Master Key"}
		other = {"type": "Link", "label": "User", "link_to": "User"}
		self.assertTrue(is_master_key_sidebar_item(link))
		self.assertFalse(is_master_key_sidebar_item(section))
		self.assertFalse(is_master_key_sidebar_item(other))
		self.assertFalse(master_key_link_allowed(link, False))
		self.assertTrue(master_key_link_allowed(link, True))
		self.assertTrue(master_key_link_allowed(other, False))
