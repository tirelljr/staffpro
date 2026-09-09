app_name = "hrms"
app_title = "Staff Pro BPO"
app_publisher = "Staff Pro BPO"
app_description = "HR and Payroll Software for Staff Pro BPO"
app_email = "contact@frappe.io"
app_license = "GNU General Public License (v3)"
required_apps = ["frappe/erpnext"]
source_link = "http://github.com/frappe/hrms"
app_logo_url = "/assets/hrms/images/staff-pro-bpo-logo.png"
app_home = "/desk/dashboard-view/Human Resource"
email_brand_image = "/assets/hrms/images/staff-pro-bpo-logo.png"

add_to_apps_screen = [
	{
		"name": "hrms",
		"logo": "/assets/hrms/images/staff-pro-bpo-logo.png",
		"title": "Staff Pro BPO",
		"route": app_home,
		"has_permission": "hrms.hr.utils.check_app_permission",
		"sequence_id": 1,
	}
]

extend_bootinfo = "hrms.boot.extend_bootinfo"
get_website_user_home_page = "hrms.boot.get_staff_pro_home_page"
on_login = "hrms.boot.on_staff_pro_login"

website_context = {
	"favicon": "/assets/hrms/images/staff-pro-bpo-icon.png",
	"splash_image": "/assets/hrms/images/staff-pro-bpo-logo.png",
	"app_name": "Staff Pro BPO",
	"brand_html": "Staff Pro BPO",
	"footer_powered": "Staff Pro BPO<br>developed by Tirell Arzu",
}

update_website_context = ["hrms.branding.update_website_context"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/hrms/css/hrms.css"
app_include_js = [
	"/assets/hrms/js/staff_pro_home_redirect.js",
	"/assets/hrms/js/client_ip.js",
	"hrms.bundle.js",
]
app_include_css = "hrms.bundle.css"

# website

# include js, css files in header of web template
web_include_css = "hrms.bundle.css"
# web_include_js = "/assets/hrms/js/hrms.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "hrms/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Employee": "public/js/erpnext/employee.js",
	"Company": "public/js/erpnext/company.js",
	"Department": "public/js/erpnext/department.js",
	"Timesheet": "public/js/erpnext/timesheet.js",
	"Payment Entry": "public/js/erpnext/payment_entry.js",
	"Journal Entry": "public/js/erpnext/journal_entry.js",
	"Holiday List": "public/js/erpnext/holiday_list.js",
	"System Settings": "public/js/erpnext/system_settings.js",
	"Sales Invoice": "public/js/erpnext/sales_invoice.js",
	"Customer": "public/js/erpnext/customer.js",
}
doctype_list_js = {
	"Employee": "public/js/erpnext/employee_list.js",
	"Sales Invoice": "public/js/erpnext/sales_invoice_list.js",
	"Customer": "public/js/erpnext/customer_list.js",
	"Dashboard Chart": "public/js/bpo_dashboard_list.js",
	"Number Card": "public/js/bpo_dashboard_list.js",
	"Dashboard": "public/js/bpo_dashboard_list.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

calendars = ["Leave Application"]

# Generators
# ----------

# automatically create page for each record of this doctype
website_generators = ["Job Opening"]

website_route_rules = [
	{"from_route": "/agents", "to_route": "hrms"},
	{"from_route": "/agents/<path:app_path>", "to_route": "hrms"},
	{"from_route": "/hr/<path:app_path>", "to_route": "roster"},
]

website_redirects = [
	{"source": "/hrms", "target": "/agents"},
	{"source": r"/hrms/(.*)", "target": r"/agents/\1"},
]
# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {
	"methods": [
		"hrms.utils.get_country",
		"hrms.branding.staff_pro_logo_url",
	],
}

# Installation
# ------------

# before_install = "hrms.install.before_install"
after_install = "hrms.install.after_install"
after_migrate = [
	"hrms.setup.update_select_perm_after_install",
	"hrms.branding.apply_branding",
	"hrms.hr.bpo_employee_labels.apply_bpo_employee_labels",
	"hrms.hr.belize_banks.ensure_belize_company_bank_accounts",
	"hrms.hr.bpo_bank_account.apply_bank_account_layout",
	"hrms.payroll.bpo_customer.apply_bpo_customer_layout",
	"hrms.payroll.bpo_sales_invoice.apply_bpo_sales_invoice_layout",
	"hrms.payroll.bpo_client_accounts.setup_usd_client_billing",
	"hrms.patches.v16_0.hide_cost_center.hide_cost_center_fields",
	"hrms.patches.v16_0.remove_workspace_sidebar_home_links.execute",
	"hrms.patches.v16_0.disable_app_onboarding.execute",
	"hrms.patches.v16_0.split_finance_and_admin.execute",
	"hrms.hr.staff_pro_sidebars.sync_staff_pro_sidebars",
	"hrms.payroll.doctype.bonus_type.bonus_type.seed_bonus_types",
	"hrms.hr.staff_pro_holiday_list.ensure_staff_pro_holiday_list",
	"hrms.hr.staff_pro_shift_locations.ensure_staff_pro_shift_locations",
	"hrms.hr.doctype.office_floor.office_floor.seed_office_floors",
	"hrms.boot.hide_unused_erpnext_workspaces",
	"hrms.boot.prepare_staff_pro_first_login",
	"hrms.overrides.bpo_dashboards.hide_non_bpo_dashboard_records",
]

setup_wizard_requires = "assets/hrms/js/setup_wizard.js"
setup_wizard_complete = "hrms.hr.staff_pro_sidebars.after_setup_wizard"

# Uninstallation
# ------------

before_uninstall = "hrms.uninstall.before_uninstall"
# after_uninstall = "hrms.uninstall.after_uninstall"

# Disable / Enable
# ----------------

before_disable = "hrms.setup.before_disable"
after_enable = "hrms.setup.after_enable"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "hrms.utils.before_app_install"
after_app_install = "hrms.setup.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

before_app_uninstall = "hrms.setup.before_app_uninstall"
# after_app_uninstall = "hrms.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "hrms.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Dashboard Chart": "hrms.overrides.bpo_dashboards.get_chart_permission_query_conditions",
	"Number Card": "hrms.overrides.bpo_dashboards.get_card_permission_query_conditions",
	"Dashboard": "hrms.overrides.bpo_dashboards.get_dashboard_permission_query_conditions",
	"Holiday Work Election": "hrms.hr.doctype.holiday_work_election.holiday_work_election.get_permission_query_conditions",
}

has_permission = {
	"Holiday Work Election": "hrms.hr.doctype.holiday_work_election.holiday_work_election.has_permission",
}

has_upload_permission = {"Employee": "erpnext.setup.doctype.employee.employee.has_upload_permission"}

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Employee": "hrms.overrides.employee_master.EmployeeMaster",
	"Timesheet": "hrms.overrides.employee_timesheet.EmployeeTimesheet",
	"Payment Entry": "hrms.overrides.employee_payment_entry.EmployeePaymentEntry",
	"Project": "hrms.overrides.employee_project.EmployeeProject",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"User": {
		"validate": [
			"erpnext.setup.doctype.employee.employee.validate_employee_role",
			"hrms.overrides.employee_master.update_approver_user_roles",
		],
	},
	"Company": {
		"validate": "hrms.overrides.company.validate_default_accounts",
		"after_insert": "hrms.hr.staff_pro_holiday_list.assign_default_holiday_list_to_company",
		"on_update": [
			"hrms.overrides.company.make_company_fixtures",
			"hrms.overrides.company.set_default_hr_accounts",
			"hrms.hr.staff_pro_holiday_list.assign_default_holiday_list_to_company",
		],
		"on_trash": "hrms.overrides.company.handle_linked_docs",
	},
	"Holiday List": {
		"validate": "hrms.utils.holiday_list.validate_holiday_list_pay_toggles",
		"on_update": "hrms.utils.holiday_list.invalidate_cache",
		"on_trash": [
			"hrms.hr.staff_pro_holiday_list.prevent_default_holiday_list_delete",
			"hrms.utils.holiday_list.invalidate_cache",
		],
	},
	"Customer": {
		"validate": "hrms.payroll.bpo_client_accounts.set_client_billing_defaults",
		"after_insert": "hrms.payroll.bpo_client_accounts.after_insert_customer",
	},
	"System Settings": {
		"on_update": "hrms.hr.agent_access.apply_office_ipv4_defaults_on_settings",
	},
	"Timesheet": {"validate": "hrms.hr.utils.validate_active_employee"},
	"Payment Entry": {
		"on_submit": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
		"on_cancel": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
		"on_update_after_submit": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
	},
	"Unreconcile Payment": {
		"on_submit": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
	},
	"Journal Entry": {
		"validate": "hrms.hr.doctype.expense_claim.expense_claim.validate_expense_claim_in_jv",
		"on_submit": [
			"hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
			"hrms.hr.doctype.full_and_final_statement.full_and_final_statement.update_full_and_final_statement_status",
			"hrms.payroll.doctype.salary_withholding.salary_withholding.update_salary_withholding_payment_status",
		],
		"on_update_after_submit": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
		"on_cancel": [
			"hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
			"hrms.payroll.doctype.salary_slip.salary_slip.unlink_ref_doc_from_salary_slip",
			"hrms.hr.doctype.full_and_final_statement.full_and_final_statement.update_full_and_final_statement_status",
			"hrms.payroll.doctype.salary_withholding.salary_withholding.update_salary_withholding_payment_status",
		],
	},
	"Loan": {"validate": "hrms.hr.utils.validate_loan_repay_from_salary"},
	"Employee": {
		"before_validate": "hrms.overrides.employee_master.sync_employee_username",
		"validate": "hrms.overrides.employee_master.validate_onboarding_process",
		"on_update": [
			"hrms.overrides.employee_master.update_approver_role",
			"hrms.overrides.employee_master.publish_update",
			"hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment.assign_structure_from_agent_hourly",
		],
		"after_insert": "hrms.overrides.employee_master.update_job_applicant_and_offer",
		"on_trash": "hrms.overrides.employee_master.update_employee_transfer",
		"after_delete": "hrms.overrides.employee_master.publish_update",
	},
	"Project": {"validate": "hrms.controllers.employee_boarding_controller.update_employee_boarding_status"},
	"Task": {"on_update": "hrms.controllers.employee_boarding_controller.update_task"},
	"Employee Checkin": {
		"after_insert": "hrms.payroll.daily_pay.on_employee_checkin",
		"on_update": "hrms.payroll.daily_pay.on_employee_checkin",
	},
	"Payroll Entry": {
		"on_submit": "hrms.payroll.auto_client_invoice.create_invoices_for_payroll_entry",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"all": [
		"hrms.hr.doctype.interview.interview.send_interview_reminder",
	],
	"hourly": [
		"hrms.hr.doctype.daily_work_summary_group.daily_work_summary_group.trigger_emails",
	],
	"hourly_long": [
		"hrms.hr.doctype.shift_type.shift_type.update_last_sync_of_checkin",
		"hrms.hr.doctype.shift_type.shift_type.process_auto_attendance_for_all_shifts",
		"hrms.hr.doctype.shift_schedule_assignment.shift_schedule_assignment.process_auto_shift_creation",
	],
	"daily": [
		"hrms.controllers.employee_reminders.send_birthday_reminders",
		"hrms.controllers.employee_reminders.send_work_anniversary_reminders",
		"hrms.hr.doctype.daily_work_summary_group.daily_work_summary_group.send_summary",
		"hrms.hr.doctype.interview.interview.send_daily_feedback_reminder",
		"hrms.hr.doctype.shift_assignment.shift_assignment.mark_expired_shift_assignments_as_inactive",
		"hrms.hr.doctype.job_opening.job_opening.close_expired_job_openings",
		"hrms.payroll.auto_payroll.run_scheduled_payroll",
		"hrms.payroll.auto_client_invoice.run_scheduled_invoices",
	],
	"daily_long": [
		"hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry.process_expired_allocation",
		"hrms.hr.utils.generate_leave_encashment",
		"hrms.hr.utils.allocate_earned_leaves",
	],
	"weekly": ["hrms.controllers.employee_reminders.send_reminders_in_advance_weekly"],
	"monthly": ["hrms.controllers.employee_reminders.send_reminders_in_advance_monthly"],
}

advance_payment_payable_doctypes = ["Leave Encashment", "Gratuity", "Employee Advance"]

invoice_doctypes = ["Expense Claim"]

period_closing_doctypes = ["Payroll Entry"]

accounting_dimension_doctypes = [
	"Expense Claim",
	"Expense Claim Detail",
	"Expense Taxes and Charges",
	"Payroll Entry",
	"Leave Encashment",
]

bank_reconciliation_doctypes = ["Expense Claim"]

# Testing
# -------

before_tests = "hrms.tests.test_utils.before_tests"

# Overriding Methods
# -----------------------------

# get matching queries for Bank Reconciliation
get_matching_queries = "hrms.hr.utils.get_matching_queries"

regional_overrides = {
	"Belize": {
		"hrms.payroll.doctype.income_tax_slab.income_tax_slab.calculate_tax_by_tax_slab": "hrms.regional.belize.utils.calculate_tax_by_tax_slab",
		"hrms.payroll.doctype.salary_slip.salary_slip.apply_regional_deductions": "hrms.regional.belize.utils.apply_regional_deductions",
	},
}

# ERPNext doctypes for Global Search
global_search_doctypes = {
	"Default": [
		{"doctype": "Salary Slip", "index": 19},
		{"doctype": "Leave Application", "index": 20},
		{"doctype": "Expense Claim", "index": 21},
		{"doctype": "Employee Grade", "index": 37},
		{"doctype": "Job Opening", "index": 39},
		{"doctype": "Job Applicant", "index": 40},
		{"doctype": "Job Offer", "index": 41},
		{"doctype": "Salary Structure Assignment", "index": 42},
		{"doctype": "Appraisal", "index": 43},
	],
}

override_whitelisted_methods = {
	"frappe.desk.doctype.dashboard.dashboard.get_permitted_cards": "hrms.boot.get_permitted_cards",
	"frappe.desk.doctype.dashboard.dashboard.get_permitted_charts": "hrms.boot.get_permitted_charts",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
override_doctype_dashboards = {
	"Employee": "hrms.overrides.dashboard_overrides.get_dashboard_for_employee",
	"Holiday List": "hrms.overrides.dashboard_overrides.get_dashboard_for_holiday_list",
	"Task": "hrms.overrides.dashboard_overrides.get_dashboard_for_project",
	"Project": "hrms.overrides.dashboard_overrides.get_dashboard_for_project",
	"Timesheet": "hrms.overrides.dashboard_overrides.get_dashboard_for_timesheet",
	"Bank Account": "hrms.overrides.dashboard_overrides.get_dashboard_for_bank_account",
}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

ignore_links_on_delete = ["PWA Notification"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"hrms.auth.validate"
# ]

# Translation
# --------------------------------

# Make link fields search translated document names for these DocTypes
# Recommended only for DocTypes which have limited documents with untranslated names
# For example: Role, Gender, etc.
# translated_search_doctypes = []

company_data_to_be_ignored = [
	"Salary Component Account",
	"Salary Structure",
	"Salary Structure Assignment",
	"Payroll Period",
	"Income Tax Slab",
	"Leave Period",
	"Leave Policy Assignment",
	"Employee Onboarding Template",
	"Employee Separation Template",
]

# List of apps whose translatable strings should be excluded from this app's translations.
ignore_translatable_strings_from = ["frappe", "erpnext"]
employee_holiday_list = ["hrms.utils.holiday_list.get_holiday_list_for_employee"]
export_python_type_annotations = True
require_type_annotated_api_methods = True
repost_allowed_doctypes = ["Expense Claim"]
