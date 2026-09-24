# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from hrms.overrides.attached_images import _as_name_list, get_attached_images
from hrms.tests.utils import HRMSTestSuite


class TestAttachedImages(HRMSTestSuite):
	def test_as_name_list_drops_nulls(self):
		self.assertEqual(_as_name_list(None), [])
		self.assertEqual(_as_name_list([None]), [])
		self.assertEqual(_as_name_list(["HR-EMP-0001", None, ""]), ["HR-EMP-0001"])
		self.assertEqual(_as_name_list('["HR-EMP-0001"]'), ["HR-EMP-0001"])
		self.assertEqual(_as_name_list("HR-EMP-0001"), ["HR-EMP-0001"])

	def test_get_attached_images_rejects_empty_names(self):
		self.assertEqual(get_attached_images("Employee", [None]), {})
		self.assertEqual(get_attached_images("Employee", None), {})
		self.assertEqual(get_attached_images("Employee", "[]"), {})
