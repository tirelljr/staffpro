import frappe
from frappe import _

BPO_DOCTYPE_UI_MESSAGES = {
	"Designation": "Role",
	"Designations": "Roles",
	"Add Designation": "Add Role",
	"New Designation": "New Role",
	"Employee Grade": "Campaign",
	"Employee Grades": "Campaigns",
	"Add Employee Grade": "Add Campaign",
	"New Employee Grade": "New Campaign",
	"Additional Salary": "Bonuses",
	"Additional Salaries": "Bonuses",
	"Add Additional Salary": "Add Bonus",
	"New Additional Salary": "New Bonus",
}

STAFF_PRO_DESK_HOME_DASHBOARD = "Human Resource"
STAFF_PRO_DESK_HOME = f"desk/dashboard-view/{STAFF_PRO_DESK_HOME_DASHBOARD}"
STAFF_PRO_DESK_HOME_ROUTE = ["dashboard-view", STAFF_PRO_DESK_HOME_DASHBOARD]
STAFF_PRO_PORTAL_ROUTES = {
	"hr": f"/{STAFF_PRO_DESK_HOME}",
	"accounting": "/desk/finance",
	"admin": "/desk/admin",
}
STAFF_PRO_INTEGRATIONS = [
	{
		"name": "whatsapp",
		"label": "WhatsApp",
		"url": "https://web.whatsapp.com",
		"icon": "/assets/hrms/images/integrations/whatsapp.svg",
	},
	{
		"name": "freshdesk",
		"label": "Freshdesk",
		"url": "https://freshdesk.com/login",
		"icon": "/assets/hrms/images/integrations/freshdesk.svg",
	},
]
STAFF_PRO_BRAND = {
	"title": "Staff Pro BPO",
	"logo_url": "/assets/hrms/images/staff-pro-bpo-logo.png",
}
EMPLOYEE_ONLY_ROLES = frozenset({"Employee Self Service"})
# Unified workspaces may be opened as dashboards by title/name; map to real Dashboard docs.
WORKSPACE_DASHBOARD_ALIASES = {
	"Workforce": "Human Resource",
	"People": "Human Resource",
	"Time": "Attendance",
	"Pay": "Payroll",
	"Talent": "Recruitment",
	"SS and Taxes": "SS and Taxes",
}
# Left-nav / dock sidebars kept for call-center BPO (everything else stripped from boot).
BPO_WORKSPACE_SIDEBARS = frozenset(
	{
		"workforce",
		"people",
		"time",
		"pay",
		"ss and taxes",
		"talent",
		"finance",
		"admin",
	}
)


def resolve_dashboard_name(dashboard_name: str) -> str:
	return WORKSPACE_DASHBOARD_ALIASES.get(dashboard_name, dashboard_name)


@frappe.whitelist()
def get_permitted_cards(dashboard_name: str):
	from frappe.desk.doctype.dashboard.dashboard import get_permitted_cards as _get_permitted_cards

	return _get_permitted_cards(resolve_dashboard_name(dashboard_name))


@frappe.whitelist()
def get_permitted_charts(dashboard_name: str):
	from frappe.desk.doctype.dashboard.dashboard import get_permitted_charts as _get_permitted_charts

	return _get_permitted_charts(resolve_dashboard_name(dashboard_name))


def is_employee_self_service_user(user=None):
	"""True when the user is an employee portal user, not a desk admin."""
	user = user or frappe.session.user
	if user == "Guest":
		return False

	if frappe.get_cached_value("User", user, "user_type") == "Website User":
		return True

	roles = set(frappe.get_roles(user)) - {"All"}
	return roles.issubset(EMPLOYEE_ONLY_ROLES)


def is_staff_pro_desk_admin(user=None):
	"""Desk admins land in the HRM hub; employee-only users keep their existing flow."""
	user = user or frappe.session.user
	if user == "Guest":
		return False

	if is_employee_self_service_user(user):
		return False

	return frappe.get_cached_value("User", user, "user_type") == "System User"


def get_staff_pro_home_page(user):
	"""Send desk admins to the People dashboard after login."""
	if is_staff_pro_desk_admin(user):
		return STAFF_PRO_DESK_HOME
	return None


def _patch_get_default_path():
	import frappe.apps as apps_module

	if getattr(apps_module, "_staff_pro_patched_default_path", False):
		return

	apps_module._staff_pro_patched_default_path = True
	original = apps_module.get_default_path

	@frappe.whitelist()
	@apps_module.request_cache
	def get_default_path():
		if is_staff_pro_desk_admin():
			return f"/{STAFF_PRO_DESK_HOME}"
		return original()

	apps_module.get_default_path = get_default_path


_patch_get_default_path()


def extend_bootinfo(bootinfo):
	"""Keep Staff Pro BPO as the only app on the desk apps screen."""
	apps = bootinfo.get("apps") or []
	filtered = [app for app in apps if app.get("name") == "hrms"]
	if filtered:
		bootinfo["apps"] = filtered

	if is_staff_pro_desk_admin():
		bootinfo["staff_pro_skip_desktop"] = True
		bootinfo["staff_pro_desk_home"] = STAFF_PRO_DESK_HOME_ROUTE
		bootinfo["staff_pro_portal_routes"] = STAFF_PRO_PORTAL_ROUTES
		bootinfo["staff_pro_brand"] = STAFF_PRO_BRAND
		bootinfo["staff_pro_integrations"] = STAFF_PRO_INTEGRATIONS

	_disable_app_onboarding_bootinfo(bootinfo)

	first_name = ""
	user = frappe.session.user
	if user and user != "Guest":
		first_name = frappe.db.get_value("User", user, "first_name") or ""
		if not first_name:
			full_name = frappe.utils.get_fullname(user) or ""
			first_name = full_name.split()[0] if full_name else ""
	bootinfo["staff_pro_user"] = {"first_name": first_name}
	bootinfo["staff_pro_bpo_sidebar_labels"] = get_sidebar_label_maps()
	apply_payroll_frequency_translations(bootinfo)
	_filter_bpo_workspace_sidebars(bootinfo)
	_filter_bpo_module_sidebars(bootinfo)
	_filter_bpo_app_workspaces(bootinfo)


def apply_payroll_frequency_translations(bootinfo):
	"""Show 2-weeks in the UI; stored payroll frequency stays Fortnightly."""
	from hrms.payroll.auto_payroll import FREQUENCY_LABELS

	label = FREQUENCY_LABELS.get("Fortnightly", "2-weeks")
	messages = bootinfo.get("__messages")
	if not isinstance(messages, dict):
		messages = {}
		bootinfo["__messages"] = messages
	messages["Fortnightly"] = label
	messages["2 Weeks"] = label
	messages["Add Sales Invoice"] = "Add Client Invoice"
	messages["New Sales Invoice"] = "New Client Invoice"
	messages["Sales Invoice"] = "Client Invoice"
	messages.update(BPO_DOCTYPE_UI_MESSAGES)


def _normalize_workspace_key(name) -> str:
	if isinstance(name, dict):
		name = name.get("name") or name.get("title") or name.get("label")
	return str(name or "").lower().replace("-", " ").replace("_", " ")


def _is_bpo_workspace_name(name) -> bool:
	return _normalize_workspace_key(name) in BPO_WORKSPACE_SIDEBARS


def _filter_bpo_workspace_sidebars(bootinfo):
	"""Drop Stock/Buying/Selling/etc. from the Desk workspace switcher payload."""
	sidebars = bootinfo.get("workspace_sidebar_item")
	if not isinstance(sidebars, dict):
		return
	bootinfo["workspace_sidebar_item"] = {
		key: value
		for key, value in sidebars.items()
		if _normalize_workspace_key(key) in BPO_WORKSPACE_SIDEBARS
	}


def _is_bpo_dock_entry(entry) -> bool:
	if not isinstance(entry, dict):
		return _is_bpo_workspace_name(entry)
	return _is_bpo_workspace_name(
		entry.get("link_to") or entry.get("title") or entry.get("name") or entry.get("label")
	)


def _filter_bpo_module_sidebars(bootinfo):
	"""Keep Frappe v17 shells and the hrms dock on Staff Pro portals only."""
	sidebars = bootinfo.get("module_sidebars")
	if isinstance(sidebars, dict):
		bootinfo["module_sidebars"] = {
			key: value
			for key, value in sidebars.items()
			if _is_bpo_workspace_name(key)
			or (isinstance(value, dict) and _is_bpo_workspace_name(value.get("title")))
		}

	dock = bootinfo.get("dock")
	if isinstance(dock, dict):
		hrms_dock = dock.get("hrms")
		bootinfo["dock"] = {"hrms": hrms_dock} if isinstance(hrms_dock, list) else {}
		if isinstance(hrms_dock, list):
			bootinfo["dock"]["hrms"] = [entry for entry in hrms_dock if _is_bpo_dock_entry(entry)]

	app_data = bootinfo.get("app_data")
	if not isinstance(app_data, list):
		return
	for app in app_data:
		if not isinstance(app, dict):
			continue
		if app.get("app_name") == "hrms":
			entries = app.get("dock")
			if isinstance(entries, list):
				app["dock"] = [entry for entry in entries if _is_bpo_dock_entry(entry)]
		else:
			app["dock"] = []
			app["on_apps_screen"] = False


def _filter_bpo_app_workspaces(bootinfo):
	"""Keep dock / apps-screen workspace lists on call-center HR and payroll."""
	app_data = bootinfo.get("app_data")
	if isinstance(app_data, list):
		for app in app_data:
			if not isinstance(app, dict):
				continue
			workspaces = app.get("workspaces")
			if isinstance(workspaces, list):
				app["workspaces"] = [name for name in workspaces if _is_bpo_workspace_name(name)]

	workspaces = bootinfo.get("workspaces")
	if isinstance(workspaces, dict):
		pages = workspaces.get("pages")
		if isinstance(pages, list):
			workspaces["pages"] = [page for page in pages if _is_bpo_workspace_name(page)]


def _disable_app_onboarding_bootinfo(bootinfo):
	"""Keep module onboarding off even if System Settings has not been patched yet."""
	sysdefaults = bootinfo.get("sysdefaults")
	if sysdefaults is None:
		bootinfo["sysdefaults"] = {"enable_onboarding": 0}
	else:
		sysdefaults["enable_onboarding"] = 0


def get_sidebar_label_maps():
	from hrms.hr.bpo_sidebar_labels import get_sidebar_label_maps as _get_maps

	return _get_maps()


@frappe.whitelist()
def set_user_language(language: str | None = None):
	"""Persist the signed-in user's desk language using Frappe's language resolution."""
	from frappe.translate import get_lang_code

	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in to change language"))

	language = get_lang_code(language or "") or (language or "en")
	if not frappe.db.exists("Language", language):
		frappe.throw(_("Language {0} is not available").format(language))

	user = frappe.get_doc("User", frappe.session.user)
	user.language = language
	user.save(ignore_permissions=True)
	return language


def hide_unused_erpnext_workspaces():
	"""Hide ERPNext module workspaces so they do not appear beside Staff Pro BPO."""
	from hrms.subscription_utils import update_erpnext_workspaces

	# Always hide stock/CRM/etc. Client billing is surfaced via the Finance workspace.
	update_erpnext_workspaces(disable=True)
