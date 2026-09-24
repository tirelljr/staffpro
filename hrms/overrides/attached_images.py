# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Python 3.14 rejects Frappe's list[str] annotation for attached image lookups."""

import frappe


def _as_name_list(names) -> list[str]:
	if names is None:
		return []
	parsed = frappe.parse_json(names) if not isinstance(names, (list, tuple, set)) else names
	if parsed is None:
		return []
	if isinstance(parsed, str):
		return [parsed] if parsed else []
	if not isinstance(parsed, (list, tuple, set)):
		return []
	return [name for name in parsed if isinstance(name, str) and name]


@frappe.whitelist()
def get_attached_images(doctype: str, names=None):
	"""Return image URLs as `{name: [file_url, ...]}` for the given documents."""
	names = _as_name_list(names)
	if not names:
		return frappe._dict()

	img_urls = frappe.db.get_list(
		"File",
		filters={
			"attached_to_doctype": doctype,
			"attached_to_name": ("in", names),
			"is_folder": 0,
		},
		fields=["file_url", "attached_to_name as docname"],
	)

	out = frappe._dict()
	for row in img_urls:
		out[row.docname] = out.get(row.docname, [])
		out[row.docname].append(row.file_url)
	return out
