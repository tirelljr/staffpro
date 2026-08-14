def extend_bootinfo(bootinfo):
	"""Keep Staff Pro BPO as the only app on the desk apps screen."""
	apps = bootinfo.get("apps") or []
	filtered = [app for app in apps if app.get("name") == "hrms"]
	if filtered:
		bootinfo["apps"] = filtered


def hide_unused_erpnext_workspaces():
	"""Hide ERPNext module workspaces so they do not appear beside Staff Pro BPO."""
	from hrms.subscription_utils import update_erpnext_workspaces

	# Always hide stock/CRM/etc. Accounting is surfaced via Finance & Admin instead.
	update_erpnext_workspaces(disable=True)
