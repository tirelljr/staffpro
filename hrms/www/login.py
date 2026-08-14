from frappe.www.login import get_context as _get_context

no_cache = True


def get_context(context):
	_get_context(context)
	context["logo"] = "/assets/hrms/images/staff-pro-bpo-logo.png"
	return context

