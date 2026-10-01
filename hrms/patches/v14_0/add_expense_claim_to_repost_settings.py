import frappe


def execute():
	"""Allow Expense Claim ledgers to be reposted.

	Older ERPNext keeps this list on Repost Accounting Ledger Settings.
	Current ERPNext keeps it on Accounts Settings. A missing settings
	DocType is loaded as a Core controller and fails migrate.
	"""
	allowed_types = ["Expense Claim"]

	if _add_to_repost_settings(allowed_types):
		return

	_add_to_accounts_settings(allowed_types)


def _add_to_repost_settings(allowed_types):
	if not frappe.db.exists("DocType", "Repost Accounting Ledger Settings"):
		return False

	try:
		repost_settings = frappe.get_doc("Repost Accounting Ledger Settings")
	except ImportError:
		return False

	if not repost_settings.meta.has_field("allowed_types"):
		return False

	existing = {row.document_type for row in repost_settings.get("allowed_types")}
	changed = False
	for document_type in allowed_types:
		if document_type not in existing:
			repost_settings.append("allowed_types", {"document_type": document_type, "allowed": True})
			changed = True

	if changed:
		repost_settings.save()

	return True


def _add_to_accounts_settings(allowed_types):
	if not frappe.db.exists("DocType", "Accounts Settings"):
		return

	if not frappe.get_meta("Accounts Settings").has_field("repost_allowed_types"):
		return

	accounts_settings = frappe.get_doc("Accounts Settings")
	existing = {row.document_type for row in accounts_settings.get("repost_allowed_types")}
	changed = False
	for document_type in allowed_types:
		if document_type not in existing:
			accounts_settings.append("repost_allowed_types", {"document_type": document_type})
			changed = True

	if changed:
		accounts_settings.save()
