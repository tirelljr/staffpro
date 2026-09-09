import os
from collections import defaultdict

import frappe
from frappe import N_ as _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.desk.page.setup_wizard.setup_wizard import make_records
from frappe.permissions import add_permission, update_permission_property

from hrms.overrides.company import delete_company_fixtures

HIDDEN_EMPLOYEE_FIELDS = (
	"salutation",
	"prefered_contact_email",
	"unsubscribed",
	"attendance_device_id",
	"provident_fund_account",
	"employee_advance_account",
	"payroll_cost_center",
	"health_insurance_section",
	"health_insurance_provider",
	"health_insurance_no",
	"iban",
)


def after_install():
	create_custom_fields(get_custom_fields(), ignore_validate=True)
	create_salary_slip_loan_fields()
	make_fixtures()
	setup_notifications()
	update_hr_defaults()
	add_non_standard_user_types()
	set_single_defaults()
	setup_repost_defaults()
	create_default_role_profiles()
	run_post_install_patches()
	add_default_hr_permissions()


def before_uninstall():
	delete_custom_fields(get_custom_fields())
	delete_custom_fields(get_salary_slip_loan_fields())
	delete_company_fixtures()


def before_disable():
	"""Hide the customizations of this app. The site calls this while the app is still active."""
	from frappe.custom import hide_customizations

	hide_customizations(get_customizations())


def after_enable():
	"""Show the customizations of this app again. The site calls this after the app is active."""
	from frappe.custom import unhide_customizations

	unhide_customizations(get_customizations())


def get_regional_custom_fields():
	"""Return the custom fields that the country of each company adds.

	A country with no regional module, or with no function for these fields, adds nothing.
	"""
	sources = []
	for country in frappe.get_all("Company", pluck="country", distinct=True):
		try:
			getter = frappe.get_attr(f"hrms.regional.{frappe.scrub(country)}.setup.get_custom_fields")
		except (ImportError, AttributeError):
			continue
		sources.append(getter())

	return sources


def get_customizations():
	from hrms.hr.bpo_employee_labels import (
		EMPLOYEE_FIELD_DEFAULTS,
		EMPLOYEE_FIELD_LABELS,
		OTHER_DOCTYPE_FIELD_LABELS,
	)
	from hrms.payroll.bpo_customer import CUSTOMER_LABELS, HIDDEN_CUSTOMER_FIELDS
	from hrms.payroll.bpo_sales_invoice import (
		HIDDEN_SALES_INVOICE_FIELDS,
		HIDDEN_SALES_INVOICE_ITEM_FIELDS,
		SALES_INVOICE_ITEM_LABELS,
		SALES_INVOICE_LABELS,
	)

	field_sources = [get_custom_fields(), *get_regional_custom_fields()]
	if "lending" in frappe.get_installed_apps():
		field_sources.append(get_salary_slip_loan_fields())

	fieldnames = defaultdict(list)
	for custom_fields in field_sources:
		for doctype, fields in custom_fields.items():
			fieldnames[doctype].extend(field["fieldname"] for field in fields)

	return {
		"Custom Field": [
			{"dt": doctype, "fieldname": ("in", fields)} for doctype, fields in fieldnames.items()
		],
		"Property Setter": [
			{"doc_type": "Salary Slip", "field_name": "rounded_total", "property": "hidden"},
			{"doc_type": "Salary Slip", "field_name": "rounded_total", "property": "print_hide"},
			{"doc_type": "Salary Slip", "field_name": "total_in_words", "property": "hidden"},
			{"doc_type": "Salary Slip", "field_name": "total_in_words", "property": "print_hide"},
			{"doc_type": "Salary Slip", "field_name": "base_total_in_words", "property": "hidden"},
			{"doc_type": "Salary Slip", "field_name": "base_total_in_words", "property": "print_hide"},
			{"doc_type": "Salary Slip", "field_name": "section_break_55", "property": "hidden"},
			{"doc_type": "Salary Slip", "field_name": "section_break_55", "property": "print_hide"},
			{"doc_type": "Salary Slip", "field_name": "column_break_69", "property": "hidden"},
			{"doc_type": "Salary Slip", "field_name": "column_break_69", "property": "print_hide"},
			{"doc_type": "Salary Slip", "field_name": "year_to_date", "property": "description"},
			{"doc_type": "Salary Slip", "field_name": "month_to_date", "property": "description"},
			{"doc_type": "Employee", "property": "default_view"},
			{"doc_type": "System Settings", "field_name": "default_app", "property": "hidden"},
			{"doc_type": "System Settings", "field_name": "app_tab", "property": "hidden"},
			*[
				{"doc_type": "Employee", "field_name": fieldname, "property": "hidden"}
				for fieldname in HIDDEN_EMPLOYEE_FIELDS
			],
			{"doc_type": "Employee", "field_name": "bank_name", "property": "fieldtype"},
			{"doc_type": "Employee", "field_name": "bank_name", "property": "options"},
			*[
				{"doc_type": "Sales Invoice", "field_name": fieldname, "property": "hidden"}
				for fieldname in HIDDEN_SALES_INVOICE_FIELDS
			],
			*[
				{"doc_type": "Sales Invoice", "field_name": fieldname, "property": "label"}
				for fieldname in SALES_INVOICE_LABELS
			],
			*[
				{"doc_type": "Sales Invoice Item", "field_name": fieldname, "property": "hidden"}
				for fieldname in HIDDEN_SALES_INVOICE_ITEM_FIELDS
			],
			*[
				{"doc_type": "Sales Invoice Item", "field_name": fieldname, "property": "label"}
				for fieldname in SALES_INVOICE_ITEM_LABELS
			],
			*[
				{"doc_type": "Customer", "field_name": fieldname, "property": "hidden"}
				for fieldname in HIDDEN_CUSTOMER_FIELDS
			],
			*[
				{"doc_type": "Customer", "field_name": fieldname, "property": "label"}
				for fieldname in CUSTOMER_LABELS
			],
			*[
				{"doc_type": "Employee", "field_name": fieldname, "property": "label"}
				for fieldname in EMPLOYEE_FIELD_LABELS
			],
			*[
				{"doc_type": "Employee", "field_name": fieldname, "property": "default"}
				for fieldname in EMPLOYEE_FIELD_DEFAULTS
			],
			{"doc_type": "Employee", "field_name": "salary_currency", "property": "read_only"},
			{"doc_type": "Employee", "field_name": "salary_currency", "property": "description"},
			{"doc_type": "Employee", "field_name": "ctc", "property": "description"},
			*[
				{"doc_type": doctype, "field_name": fieldname, "property": "label"}
				for doctype, labels in OTHER_DOCTYPE_FIELD_LABELS.items()
				for fieldname in labels
			],
			{"doc_type": "Department", "field_name": "payroll_cost_center", "property": "hidden"},
		],
		"Custom DocPerm": [
			{"parent": doctype, "role": role}
			for role, permissions in HR_ROLE_PERMISSIONS.items()
			for doctype in permissions
		],
	}


def after_app_install(app_name):
	"""Set up loan integration with payroll"""
	if app_name != "lending":
		return

	print("Updating payroll setup for loans")
	create_custom_fields(get_salary_slip_loan_fields(), ignore_validate=True)
	add_lending_docperms_to_ess()


def before_app_uninstall(app_name):
	"""Clean up loan integration with payroll"""
	if app_name != "lending":
		return

	print("Updating payroll setup for loans")
	delete_custom_fields(get_salary_slip_loan_fields())
	remove_lending_docperms_from_ess()


def get_custom_fields():
	"""HR specific custom fields that need to be added to the masters in ERPNext"""
	return {
		"Company": [
			{
				"fieldname": "hr_and_payroll_tab",
				"fieldtype": "Tab Break",
				"label": _("HR & Payroll"),
				"insert_after": "purchase_expense_contra_account",
			},
			{
				"fieldname": "hr_settings_section",
				"fieldtype": "Section Break",
				"label": _("HR & Payroll Settings"),
				"insert_after": "hr_and_payroll_tab",
			},
			{
				"depends_on": "eval:!doc.__islocal",
				"fieldname": "default_expense_claim_payable_account",
				"fieldtype": "Link",
				"ignore_user_permissions": 1,
				"label": _("Default Expense Claim Payable Account"),
				"no_copy": 1,
				"options": "Account",
				"insert_after": "hr_settings_section",
			},
			{
				"fieldname": "default_employee_advance_account",
				"fieldtype": "Link",
				"label": _("Default Employee Advance Account"),
				"no_copy": 1,
				"options": "Account",
				"insert_after": "default_expense_claim_payable_account",
			},
			{
				"fieldname": "column_break_10",
				"fieldtype": "Column Break",
				"insert_after": "default_employee_advance_account",
			},
			{
				"depends_on": "eval:!doc.__islocal",
				"fieldname": "default_payroll_payable_account",
				"fieldtype": "Link",
				"hidden": 1,
				"ignore_user_permissions": 1,
				"label": _("Default Payroll Payable Account"),
				"no_copy": 1,
				"options": "Account",
				"insert_after": "column_break_10",
			},
		],
		"Department": [
			{
				"fieldname": "section_break_4",
				"fieldtype": "Section Break",
				"insert_after": "disabled",
			},
			{
				"fieldname": "payroll_cost_center",
				"fieldtype": "Link",
				"hidden": 1,
				"label": _("Payroll Cost Center"),
				"options": "Cost Center",
				"insert_after": "section_break_4",
			},
			{
				"fieldname": "column_break_9",
				"fieldtype": "Column Break",
				"insert_after": "payroll_cost_center",
			},
			{
				"description": _("Days for which Holidays are blocked for this department."),
				"fieldname": "leave_block_list",
				"fieldtype": "Link",
				"in_list_view": 1,
				"label": _("Leave Block List"),
				"options": "Leave Block List",
				"insert_after": "column_break_9",
			},
			{
				"description": _("The first Approver in the list will be set as the default Approver."),
				"fieldname": "approvers",
				"fieldtype": "Section Break",
				"label": _("Approvers"),
				"insert_after": "leave_block_list",
			},
			{
				"fieldname": "shift_request_approver",
				"fieldtype": "Table",
				"label": _("Shift Request Approver"),
				"options": "Department Approver",
				"insert_after": "approvers",
			},
			{
				"fieldname": "leave_approvers",
				"fieldtype": "Table",
				"label": _("Leave Approver"),
				"options": "Department Approver",
				"insert_after": "shift_request_approver",
			},
			{
				"fieldname": "expense_approvers",
				"fieldtype": "Table",
				"label": _("Expense Approver"),
				"options": "Department Approver",
				"insert_after": "leave_approvers",
			},
		],
		"Designation": [
			{
				"fieldname": "appraisal_template",
				"fieldtype": "Link",
				"label": _("Appraisal Template"),
				"options": "Appraisal Template",
				"insert_after": "description",
				"allow_in_quick_entry": 1,
			},
			{
				"fieldname": "required_skills_section",
				"fieldtype": "Section Break",
				"label": _("Required Skills"),
				"insert_after": "appraisal_template",
			},
			{
				"fieldname": "skills",
				"fieldtype": "Table",
				"label": _("Skills"),
				"options": "Designation Skill",
				"insert_after": "required_skills_section",
			},
		],
		"Employee": [
			{
				"fieldname": "employment_type",
				"fieldtype": "Link",
				"ignore_user_permissions": 1,
				"label": _("Employment Type"),
				"options": "Employment Type",
				"insert_after": "department",
				"in_list_view": 1,
			},
			{
				"fieldname": "job_applicant",
				"fieldtype": "Link",
				"label": _("Job Applicant"),
				"options": "Job Applicant",
				"insert_after": "employment_details",
			},
			{
				"fieldname": "grade",
				"fieldtype": "Link",
				"label": _("Campaign"),
				"options": "Employee Grade",
				"insert_after": "branch",
				"description": _("BPO campaign this agent is assigned to."),
			},
			{
				"fieldname": "default_shift",
				"fieldtype": "Link",
				"label": _("Default Shift"),
				"options": "Shift Type",
				"insert_after": "holiday_list",
			},
			{
				"collapsible": 1,
				"fieldname": "health_insurance_section",
				"fieldtype": "Section Break",
				"hidden": 1,
				"label": _("Health Insurance"),
				"insert_after": "health_details",
			},
			{
				"fieldname": "health_insurance_provider",
				"fieldtype": "Link",
				"hidden": 1,
				"label": _("Health Insurance Provider"),
				"options": "Employee Health Insurance",
				"insert_after": "health_insurance_section",
			},
			{
				"depends_on": "eval:doc.health_insurance_provider",
				"fieldname": "health_insurance_no",
				"fieldtype": "Data",
				"hidden": 1,
				"label": _("Health Insurance No"),
				"insert_after": "health_insurance_provider",
			},
			{
				"fieldname": "approvers_section",
				"fieldtype": "Section Break",
				"label": _("Approvers"),
				"insert_after": "default_shift",
			},
			{
				"fieldname": "expense_approver",
				"fieldtype": "Link",
				"label": _("Expense Approver"),
				"options": "User",
				"insert_after": "approvers_section",
				"ignore_user_permissions": 1,
			},
			{
				"fieldname": "leave_approver",
				"fieldtype": "Link",
				"label": _("Leave Approver"),
				"options": "User",
				"insert_after": "expense_approver",
				"ignore_user_permissions": 1,
			},
			{
				"fieldname": "column_break_45",
				"fieldtype": "Column Break",
				"insert_after": "leave_approver",
			},
			{
				"fieldname": "shift_request_approver",
				"fieldtype": "Link",
				"label": _("Shift Request Approver"),
				"options": "User",
				"insert_after": "column_break_45",
				"ignore_user_permissions": 1,
			},
			{
				"fieldname": "employee_advance_account",
				"fieldtype": "Link",
				"hidden": 1,
				"label": _("Employee Advance Account"),
				"options": "Account",
				"insert_after": "salary_mode",
			},
			{
				"fieldname": "salary_cb",
				"fieldtype": "Column Break",
				"insert_after": "employee_advance_account",
			},
			{
				"description": _(
					"Amount this agent can earn, for example 500. Paid over the months below if they keep the attendance target."
				),
				"fieldname": "user_bonus",
				"fieldtype": "Currency",
				"label": _("User Bonus"),
				"options": "salary_currency",
				"insert_after": "salary_cb",
			},
			{
				"default": "3",
				"description": _("Pay the user bonus over this many months."),
				"fieldname": "user_bonus_period_months",
				"fieldtype": "Int",
				"label": _("Over Months"),
				"insert_after": "user_bonus",
			},
			{
				"default": "90",
				"description": _("Minimum attendance percent to earn the bonus, for example 90."),
				"fieldname": "user_bonus_attendance_target",
				"fieldtype": "Percent",
				"label": _("Attendance Target"),
				"insert_after": "user_bonus_period_months",
			},
			{
				"default": "No Bonus",
				"description": _(
					"No Bonus withholds the period share. Deduct takes that share off their pay."
				),
				"fieldname": "user_bonus_if_below",
				"fieldtype": "Select",
				"label": _("If Below Target"),
				"options": "No Bonus\nDeduct",
				"insert_after": "user_bonus_attendance_target",
			},
			{
				"fieldname": "user_bonus_attendance",
				"fieldtype": "Percent",
				"label": _("Current Attendance"),
				"read_only": 1,
				"insert_after": "user_bonus_if_below",
			},
			{
				"fieldname": "user_bonus_missed_days",
				"fieldtype": "Float",
				"label": _("Missed Days"),
				"precision": "1",
				"read_only": 1,
				"insert_after": "user_bonus_attendance",
			},
			{
				"fieldname": "user_bonus_status",
				"fieldtype": "Small Text",
				"label": _("Bonus Status"),
				"read_only": 1,
				"insert_after": "user_bonus_missed_days",
			},
			{
				"fetch_from": "department.payroll_cost_center",
				"fetch_if_empty": 1,
				"fieldname": "payroll_cost_center",
				"fieldtype": "Link",
				"hidden": 1,
				"label": _("Payroll Cost Center"),
				"options": "Cost Center",
				"insert_after": "user_bonus_status",
			},
			{
				"fieldname": "billing_section",
				"fieldtype": "Section Break",
				"label": _("Client Billing"),
				"insert_after": "payroll_cost_center",
			},
			{
				"fieldname": "bill_to_customer",
				"fieldtype": "Link",
				"label": _("Bill To Client"),
				"options": "Customer",
				"insert_after": "billing_section",
			},
			{
				"default": "USD",
				"fieldname": "billing_currency",
				"fieldtype": "Link",
				"hidden": 1,
				"label": _("Billing Currency"),
				"options": "Currency",
				"insert_after": "bill_to_customer",
				"read_only": 1,
			},
			{
				"description": _(
					"Hourly rate billed to the client in USD. This is not the agent's pay, which stays in salary currency (BZD)."
				),
				"fieldname": "billing_rate",
				"fieldtype": "Currency",
				"label": _("Billing Rate (Hourly)"),
				"options": "billing_currency",
				"insert_after": "billing_currency",
			},
			{
				"description": _(
					"Bound on first login when device lock is enabled in System Settings. Clear this to allow a new device."
				),
				"fieldname": "login_device_id",
				"fieldtype": "Data",
				"label": _("Registered Device ID"),
				"insert_after": "user_id",
			},
			{
				"description": _(
					"Default workstation IPv4 from System Settings Office IPv4. Used on the floor map when a cubicle has no IP."
				),
				"fieldname": "default_ipv4",
				"fieldtype": "Data",
				"label": _("Default IPv4"),
				"insert_after": "login_device_id",
			},
		],
		"Customer": [
			{
				"default": "USD",
				"fieldname": "billing_currency",
				"fieldtype": "Link",
				"hidden": 1,
				"label": _("Billing Currency"),
				"options": "Currency",
				"insert_after": "customer_type",
				"read_only": 1,
			},
			{
				"description": _("Hourly rate billed to this client in USD."),
				"fieldname": "default_billing_rate",
				"fieldtype": "Currency",
				"in_list_view": 1,
				"label": _("Hourly Billing Rate"),
				"options": "billing_currency",
				"insert_after": "billing_currency",
			},
			{
				"fieldname": "campaign_section",
				"fieldtype": "Section Break",
				"label": _("Campaign"),
				"insert_after": "default_billing_rate",
			},
			{
				"description": _("Client program or campaign this account is billed under."),
				"fieldname": "campaign_name",
				"fieldtype": "Data",
				"label": _("Campaign / Program"),
				"insert_after": "campaign_section",
			},
			{
				"fieldname": "service_type",
				"fieldtype": "Select",
				"label": _("Service Type"),
				"options": "\nInbound\nOutbound\nBlended\nChat\nEmail\nBack Office\nCollections\nTechnical Support",
				"insert_after": "campaign_name",
			},
			{
				"fieldname": "contracted_seats",
				"fieldtype": "Int",
				"label": _("Contracted Seats"),
				"non_negative": 1,
				"insert_after": "service_type",
			},
			{
				"fieldname": "column_break_campaign",
				"fieldtype": "Column Break",
				"insert_after": "contracted_seats",
			},
			{
				"fieldname": "client_timezone",
				"fieldtype": "Select",
				"label": _("Timezone"),
				"options": "\nAmerica/Belize\nAmerica/New_York\nAmerica/Chicago\nAmerica/Denver\nAmerica/Los_Angeles\nUTC",
				"insert_after": "column_break_campaign",
			},
			{
				"description": _("e.g. 24/7 or 8:00–20:00 ET"),
				"fieldname": "hours_of_operation",
				"fieldtype": "Data",
				"label": _("Hours of Operation"),
				"insert_after": "client_timezone",
			},
			{
				"fieldname": "billing_frequency",
				"fieldtype": "Select",
				"label": _("Billing Frequency"),
				"options": "Weekly\nFortnightly\nMonthly",
				"insert_after": "hours_of_operation",
			},
			{
				"fieldname": "contract_section",
				"fieldtype": "Section Break",
				"label": _("Contract"),
				"insert_after": "billing_frequency",
			},
			{
				"fieldname": "contract_start_date",
				"fieldtype": "Date",
				"label": _("Contract Start"),
				"insert_after": "contract_section",
			},
			{
				"fieldname": "column_break_contract",
				"fieldtype": "Column Break",
				"insert_after": "contract_start_date",
			},
			{
				"fieldname": "contract_end_date",
				"fieldtype": "Date",
				"label": _("Contract End"),
				"insert_after": "column_break_contract",
			},
		],
		"Sales Invoice": [
			{
				"fieldname": "billing_from",
				"fieldtype": "Date",
				"label": _("Billing From"),
				"insert_after": "due_date",
			},
			{
				"fieldname": "billing_to",
				"fieldtype": "Date",
				"label": _("Billing To"),
				"insert_after": "billing_from",
			},
		],
		"Project": [
			{
				"fieldname": "total_expense_claim",
				"fieldtype": "Currency",
				"label": _("Total Expense Claim (via Expense Claims)"),
				"read_only": 1,
				"insert_after": "total_costing_amount",
			},
		],
		"Task": [
			{
				"fieldname": "total_expense_claim",
				"fieldtype": "Currency",
				"label": _("Total Expense Claim (via Expense Claim)"),
				"options": "Company:company:default_currency",
				"read_only": 1,
				"insert_after": "total_costing_amount",
			},
		],
		"Timesheet": [
			{
				"fieldname": "salary_slip",
				"fieldtype": "Link",
				"label": _("Salary Slip"),
				"no_copy": 1,
				"options": "Salary Slip",
				"print_hide": 1,
				"read_only": 1,
				"insert_after": "column_break_3",
			},
		],
		"Terms and Conditions": [
			{
				"default": "1",
				"fieldname": "hr",
				"fieldtype": "Check",
				"label": _("HR"),
				"insert_after": "buying",
			},
		],
		"Holiday List": [
			{
				"fieldname": "holiday_pay_section",
				"fieldtype": "Section Break",
				"label": _("Holiday Pay"),
				"insert_after": "weekly_off",
			},
			{
				"fieldname": "pay_time_and_a_half",
				"fieldtype": "Check",
				"label": _("Pay Time and a Half"),
				"insert_after": "holiday_pay_section",
				"description": _("Public holidays only. Mutually exclusive with Double Time."),
			},
			{
				"fieldname": "column_break_holiday_pay",
				"fieldtype": "Column Break",
				"insert_after": "pay_time_and_a_half",
			},
			{
				"fieldname": "pay_double_time",
				"fieldtype": "Check",
				"label": _("Pay Double Time"),
				"insert_after": "column_break_holiday_pay",
				"description": _("Public holidays only. Mutually exclusive with Time and a Half."),
			},
		],
		"System Settings": [
			{
				"fieldname": "agent_access_section",
				"fieldtype": "Section Break",
				"label": _("Agent Access"),
				"insert_after": "allow_login_using_user_name",
			},
			{
				"default": "0",
				"fieldname": "restrict_agent_clockin_to_office_ip",
				"fieldtype": "Check",
				"label": _("Restrict Agent Clock-in to Office IPv4"),
				"insert_after": "agent_access_section",
			},
			{
				"depends_on": "restrict_agent_clockin_to_office_ip",
				"description": _(
					"Agents can clock in only from these IPv4 addresses. Enter one per line. Scan BPO IPv4 uses the same real-network scan as the kiosk (STUN/public IPv4), then ARP/ICMP on a reachable office LAN. The first address becomes every agent's default IP."
				),
				"fieldname": "office_clockin_ipv4",
				"fieldtype": "Small Text",
				"label": _("Office IPv4"),
				"insert_after": "restrict_agent_clockin_to_office_ip",
			},
			{
				"depends_on": "restrict_agent_clockin_to_office_ip",
				"fieldname": "scan_bpo_ipv4",
				"fieldtype": "Button",
				"label": _("Scan BPO IPv4"),
				"insert_after": "office_clockin_ipv4",
			},
			{
				"default": "0",
				"description": _(
					"The first successful agent login binds that browser. Clear Registered Device ID on the Employee to rebind."
				),
				"fieldname": "restrict_agent_login_to_device",
				"fieldtype": "Check",
				"label": _("Restrict Agent Login to Registered Device"),
				"insert_after": "scan_bpo_ipv4",
			},
		],
	}


def make_fixtures():
	records = [
		# expense claim type
		{"doctype": "Expense Claim Type", "name": _("Calls"), "expense_type": _("Calls")},
		{"doctype": "Expense Claim Type", "name": _("Food"), "expense_type": _("Food")},
		{"doctype": "Expense Claim Type", "name": _("Medical"), "expense_type": _("Medical")},
		{"doctype": "Expense Claim Type", "name": _("Others"), "expense_type": _("Others")},
		{"doctype": "Expense Claim Type", "name": _("Travel"), "expense_type": _("Travel")},
		{
			"doctype": "HR Request Type",
			"name": _("Job Letter"),
			"request_type_name": _("Job Letter"),
			"description": _("Request an employment or job letter for banks, visas, or other official use."),
		},
		{
			"doctype": "HR Request Type",
			"name": _("Employment Verification"),
			"request_type_name": _("Employment Verification"),
			"description": _("Ask HR to confirm employment details for a third party."),
		},
		{
			"doctype": "HR Request Type",
			"name": _("Address / Personal Details Update"),
			"request_type_name": _("Address / Personal Details Update"),
			"description": _("Request a change to address, name, or other personal details."),
		},
		{
			"doctype": "HR Request Type",
			"name": _("General Inquiry"),
			"request_type_name": _("General Inquiry"),
			"description": _("Send a general question or request to the HR team."),
		},
		{
			"doctype": "Bonus Type",
			"name": _("Performance Bonus"),
			"bonus_type_name": _("Performance Bonus"),
			"description": _("Awarded for meeting or exceeding performance targets."),
		},
		{
			"doctype": "Bonus Type",
			"name": _("Attendance Bonus"),
			"bonus_type_name": _("Attendance Bonus"),
			"description": _("Awarded for meeting attendance or punctuality goals."),
		},
		{
			"doctype": "Bonus Type",
			"name": _("Referral Bonus"),
			"bonus_type_name": _("Referral Bonus"),
			"description": _("Awarded for referring a hired candidate."),
		},
		{
			"doctype": "Bonus Type",
			"name": _("Holiday Bonus"),
			"bonus_type_name": _("Holiday Bonus"),
			"description": _("Seasonal or holiday bonus paid with regular wages."),
		},
		{
			"doctype": "Bonus Type",
			"name": _("Other"),
			"bonus_type_name": _("Other"),
			"description": _("Any other one-time bonus added to gross pay."),
		},
		# vehicle service item
		{"doctype": "Vehicle Service Item", "service_item": "Brake Oil"},
		{"doctype": "Vehicle Service Item", "service_item": "Brake Pad"},
		{"doctype": "Vehicle Service Item", "service_item": "Clutch Plate"},
		{"doctype": "Vehicle Service Item", "service_item": "Engine Oil"},
		{"doctype": "Vehicle Service Item", "service_item": "Oil Change"},
		{"doctype": "Vehicle Service Item", "service_item": "Wheels"},
		# leave type
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Casual Leave"),
			"name": _("Casual Leave"),
			"allow_encashment": 1,
			"is_carry_forward": 1,
			"max_continuous_days_allowed": "3",
			"include_holiday": 1,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Compensatory Off"),
			"name": _("Compensatory Off"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"include_holiday": 1,
			"is_compensatory": 1,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Sick Leave"),
			"name": _("Sick Leave"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"include_holiday": 1,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Privilege Leave"),
			"name": _("Privilege Leave"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"include_holiday": 1,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Leave Without Pay"),
			"name": _("Leave Without Pay"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"is_lwp": 1,
			"include_holiday": 1,
		},
		# Employment Type
		{"doctype": "Employment Type", "employee_type_name": _("Full-time")},
		{"doctype": "Employment Type", "employee_type_name": _("Part-time")},
		{"doctype": "Employment Type", "employee_type_name": _("Probation")},
		{"doctype": "Employment Type", "employee_type_name": _("Contract")},
		{"doctype": "Employment Type", "employee_type_name": _("Commission")},
		{"doctype": "Employment Type", "employee_type_name": _("Piecework")},
		{"doctype": "Employment Type", "employee_type_name": _("Intern")},
		{"doctype": "Employment Type", "employee_type_name": _("Apprentice")},
		# Job Applicant Source
		{"doctype": "Job Applicant Source", "source_name": _("Website Listing")},
		{"doctype": "Job Applicant Source", "source_name": _("Walk In")},
		{"doctype": "Job Applicant Source", "source_name": _("Employee Referral")},
		{"doctype": "Job Applicant Source", "source_name": _("Campaign")},
		# Offer Term
		{"doctype": "Offer Term", "offer_term": _("Date of Joining")},
		{"doctype": "Offer Term", "offer_term": _("Annual Salary")},
		{"doctype": "Offer Term", "offer_term": _("Probationary Period")},
		{"doctype": "Offer Term", "offer_term": _("Employee Benefits")},
		{"doctype": "Offer Term", "offer_term": _("Working Hours")},
		{"doctype": "Offer Term", "offer_term": _("Stock Options")},
		{"doctype": "Offer Term", "offer_term": _("Department")},
		{"doctype": "Offer Term", "offer_term": _("Job Description")},
		{"doctype": "Offer Term", "offer_term": _("Responsibilities")},
		{"doctype": "Offer Term", "offer_term": _("Leaves per Year")},
		{"doctype": "Offer Term", "offer_term": _("Notice Period")},
		{"doctype": "Offer Term", "offer_term": _("Incentives")},
		# Email Account
		{"doctype": "Email Account", "email_id": "jobs@example.com", "append_to": "Job Applicant"},
	]

	make_records(records)


def setup_notifications():
	base_path = frappe.get_app_path("hrms", "hr", "doctype")

	# Leave Application
	response = frappe.read_file(
		os.path.join(base_path, "leave_application/leave_application_email_template.html")
	)
	records = [
		{
			"doctype": "Email Template",
			"name": _("Leave Approval Notification"),
			"response": response,
			"subject": _("Leave Approval Notification"),
			"owner": frappe.session.user,
		}
	]
	records += [
		{
			"doctype": "Email Template",
			"name": _("Leave Status Notification"),
			"response": response,
			"subject": _("Leave Status Notification"),
			"owner": frappe.session.user,
		}
	]

	# Interview
	response = frappe.read_file(
		os.path.join(base_path, "interview/interview_reminder_notification_template.html")
	)
	records += [
		{
			"doctype": "Email Template",
			"name": _("Interview Reminder"),
			"response": response,
			"subject": _("Interview Reminder"),
			"owner": frappe.session.user,
		}
	]
	response = frappe.read_file(
		os.path.join(base_path, "interview/interview_feedback_reminder_template.html")
	)
	records += [
		{
			"doctype": "Email Template",
			"name": _("Interview Feedback Reminder"),
			"response": response,
			"subject": _("Interview Feedback Reminder"),
			"owner": frappe.session.user,
		}
	]

	# Exit Interview
	response = frappe.read_file(
		os.path.join(base_path, "exit_interview/exit_questionnaire_notification_template.html")
	)
	records += [
		{
			"doctype": "Email Template",
			"name": _("Exit Questionnaire Notification"),
			"response": response,
			"subject": _("Exit Questionnaire Notification"),
			"owner": frappe.session.user,
		}
	]

	make_records(records)


def update_hr_defaults():
	hr_settings = frappe.get_doc("HR Settings")
	hr_settings.emp_created_by = "Full Name"
	hr_settings.standard_working_hours = 40
	hr_settings.send_birthday_reminders = 1
	hr_settings.leave_approval_notification_template = _("Leave Approval Notification")
	hr_settings.leave_status_notification_template = _("Leave Status Notification")

	hr_settings.send_interview_reminder = 1
	hr_settings.interview_reminder_template = _("Interview Reminder")
	hr_settings.remind_before = "00:15:00"

	hr_settings.send_interview_feedback_reminder = 1
	hr_settings.feedback_reminder_notification_template = _("Interview Feedback Reminder")

	hr_settings.exit_questionnaire_notification_template = _("Exit Questionnaire Notification")
	hr_settings.save()


def set_single_defaults():
	for dt in ("HR Settings", "Payroll Settings"):
		default_values = frappe.get_all(
			"DocField",
			filters={"parent": dt},
			fields=["fieldname", "default"],
			as_list=True,
		)
		if default_values:
			try:
				doc = frappe.get_doc(dt, dt)
				for fieldname, value in default_values:
					doc.set(fieldname, value)
				doc.flags.ignore_mandatory = True
				doc.save()
			except frappe.ValidationError:
				pass


def create_default_role_profiles():
	for role_profile_name, roles in DEFAULT_ROLE_PROFILES.items():
		if frappe.db.exists("Role Profile", role_profile_name):
			continue

		role_profile = frappe.new_doc("Role Profile")
		role_profile.role_profile = role_profile_name
		for role in roles:
			role_profile.append("roles", {"role": role})

		role_profile.insert(ignore_permissions=True)


def get_post_install_patches():
	return (
		"erpnext.patches.v13_0.move_tax_slabs_from_payroll_period_to_income_tax_slab",
		"erpnext.patches.v13_0.move_doctype_reports_and_notification_from_hr_to_payroll",
		"erpnext.patches.v13_0.move_payroll_setting_separately_from_hr_settings",
		"erpnext.patches.v13_0.update_start_end_date_for_old_shift_assignment",
		"erpnext.patches.v13_0.updates_for_multi_currency_payroll",
		"erpnext.patches.v13_0.update_reason_for_resignation_in_employee",
		"erpnext.patches.v13_0.set_company_in_leave_ledger_entry",
		"erpnext.patches.v13_0.rename_stop_to_send_birthday_reminders",
		"erpnext.patches.v13_0.set_training_event_attendance",
		"erpnext.patches.v14_0.set_payroll_cost_centers",
		"erpnext.patches.v13_0.update_employee_advance_status",
		"erpnext.patches.v13_0.update_expense_claim_status_for_paid_advances",
		"erpnext.patches.v14_0.delete_employee_transfer_property_doctype",
		"erpnext.patches.v13_0.set_payroll_entry_status",
		# HRMS
		"create_country_fixtures",
		"update_allocate_on_in_leave_type",
		"update_performance_module_changes",
	)


def run_post_install_patches():
	print("\nPatching Existing Data...")

	POST_INSTALL_PATCHES = get_post_install_patches()
	frappe.flags.in_patch = True

	try:
		for patch in POST_INSTALL_PATCHES:
			patch_name = patch.split(".")[-1]
			if not patch_name:
				continue

			frappe.get_attr(f"hrms.patches.post_install.{patch_name}.execute")()
	finally:
		frappe.flags.in_patch = False


# LENDING APP SETUP & CLEANUP
def create_salary_slip_loan_fields():
	if "lending" in frappe.get_installed_apps():
		create_custom_fields(get_salary_slip_loan_fields(), ignore_validate=True)


def add_lending_docperms_to_ess():
	doc = frappe.get_doc("User Type", "Employee Self Service")

	loan_docperms = get_lending_docperms_for_ess()
	append_docperms_to_user_type(loan_docperms, doc)

	doc.flags.ignore_links = True
	doc.save(ignore_permissions=True)


def remove_lending_docperms_from_ess():
	doc = frappe.get_doc("User Type", "Employee Self Service")

	loan_docperms = get_lending_docperms_for_ess()

	for row in list(doc.user_doctypes):
		if row.document_type in loan_docperms:
			doc.user_doctypes.remove(row)

	doc.flags.ignore_links = True
	doc.save(ignore_permissions=True)


# ESS USER TYPE SETUP & CLEANUP
def add_non_standard_user_types():
	user_types = get_user_types_data()

	for user_type, data in user_types.items():
		create_custom_role(data)
		create_user_type(user_type, data)


def get_user_types_data():
	return {
		"Employee Self Service": {
			"role": "Employee Self Service",
			"apply_user_permission_on": "Employee",
			"user_id_field": "user_id",
			"doctypes": {
				# masters
				"Holiday List": ["read"],
				"Employee": ["read", "write"],
				"Company": ["read"],
				# payroll
				"Salary Slip": ["read"],
				"Employee Benefit Application": ["read", "write", "create", "delete"],
				# expenses
				"Expense Claim": ["read", "write", "create", "delete"],
				"Expense Claim Type": ["read"],
				"Employee Advance": ["read", "write", "create", "delete"],
				# leave and attendance
				"Leave Type": ["read"],
				"Leave Application": ["read", "write", "create", "delete"],
				"Attendance Request": ["read", "write", "create", "delete"],
				"Compensatory Leave Request": ["read", "write", "create", "delete"],
				# tax
				"Employee Tax Exemption Declaration": ["read", "write", "create", "delete"],
				"Employee Tax Exemption Proof Submission": ["read", "write", "create", "delete"],
				# projects
				"Timesheet": ["read", "write", "create", "delete", "submit", "cancel", "amend"],
				# trainings
				"Training Program": ["read"],
				"Training Feedback": ["read", "write", "create", "delete", "submit", "cancel", "amend"],
				# shifts
				"Employee Checkin": ["read"],
				"Shift Request": ["read", "write", "create", "delete", "submit", "cancel", "amend"],
				# misc
				"Employee Grievance": ["read", "write", "create", "delete"],
				"HR Request": ["read", "write", "create", "delete"],
				"HR Request Type": ["read"],
				"Employee Referral": ["read", "write", "create", "delete"],
			},
		}
	}


def get_lending_docperms_for_ess():
	return {
		"Loan": ["read"],
		"Loan Application": ["read", "write", "create", "delete", "submit"],
		"Loan Product": ["read"],
	}


def create_custom_role(data):
	if data.get("role") and not frappe.db.exists("Role", data.get("role")):
		frappe.get_doc(
			{"doctype": "Role", "role_name": data.get("role"), "desk_access": 1, "is_custom": 1}
		).insert(ignore_permissions=True)


def create_user_type(user_type, data):
	if frappe.db.exists("User Type", user_type):
		doc = frappe.get_cached_doc("User Type", user_type)
		doc.user_doctypes = []
	else:
		doc = frappe.new_doc("User Type")
		doc.update(
			{
				"name": user_type,
				"role": data.get("role"),
				"user_id_field": data.get("user_id_field"),
				"apply_user_permission_on": data.get("apply_user_permission_on"),
			}
		)

	docperms = data.get("doctypes")
	if doc.role == "Employee Self Service" and "lending" in frappe.get_installed_apps():
		docperms.update(get_lending_docperms_for_ess())

	append_docperms_to_user_type(docperms, doc)

	doc.flags.ignore_links = True
	doc.save(ignore_permissions=True)


def append_docperms_to_user_type(docperms, doc):
	existing_doctypes = [d.document_type for d in doc.user_doctypes]

	for doctype, perms in docperms.items():
		if doctype in existing_doctypes:
			continue

		args = {"document_type": doctype}
		for perm in perms:
			args[perm] = 1

		doc.append("user_doctypes", args)


def update_select_perm_after_install():
	if not frappe.flags.update_select_perm_after_migrate:
		return

	frappe.flags.ignore_select_perm = False
	for row in frappe.get_all("User Type", filters={"is_standard": 0}):
		print("Updating user type :- ", row.name)
		doc = frappe.get_doc("User Type", row.name)
		doc.flags.ignore_links = True
		doc.save()

	frappe.flags.update_select_perm_after_migrate = False


def delete_custom_fields(custom_fields: dict):
	"""
	:param custom_fields: a dict like `{'Salary Slip': [{fieldname: 'loans', ...}]}`
	"""
	for doctype, fields in custom_fields.items():
		frappe.db.delete(
			"Custom Field",
			{
				"fieldname": ("in", [field["fieldname"] for field in fields]),
				"dt": doctype,
			},
		)

		frappe.clear_cache(doctype=doctype)


DEFAULT_ROLE_PROFILES = {
	"HR": [
		"HR User",
		"HR Manager",
		"Leave Approver",
		"Expense Approver",
	],
}


def get_salary_slip_loan_fields():
	return {
		"Salary Slip": [
			{
				"fieldname": "loan_repayment_sb_1",
				"fieldtype": "Section Break",
				"label": _("Loan Repayment"),
				"depends_on": "total_loan_repayment",
				"insert_after": "base_total_deduction",
			},
			{
				"fieldname": "loans",
				"fieldtype": "Table",
				"label": _("Employee Loan"),
				"options": "Salary Slip Loan",
				"print_hide": 1,
				"insert_after": "loan_repayment_sb_1",
			},
			{
				"fieldname": "loan_details_sb_1",
				"fieldtype": "Section Break",
				"depends_on": "eval:doc.docstatus != 0",
				"insert_after": "loans",
			},
			{
				"fieldname": "total_principal_amount",
				"fieldtype": "Currency",
				"label": _("Total Principal Amount"),
				"default": "0",
				"options": "Company:company:default_currency",
				"read_only": 1,
				"insert_after": "loan_details_sb_1",
			},
			{
				"fieldname": "total_interest_amount",
				"fieldtype": "Currency",
				"label": _("Total Interest Amount"),
				"default": "0",
				"options": "Company:company:default_currency",
				"read_only": 1,
				"insert_after": "total_principal_amount",
			},
			{
				"fieldname": "loan_cb_1",
				"fieldtype": "Column Break",
				"insert_after": "total_interest_amount",
			},
			{
				"fieldname": "total_loan_repayment",
				"fieldtype": "Currency",
				"label": _("Total Loan Repayment"),
				"default": "0",
				"options": "Company:company:default_currency",
				"read_only": 1,
				"insert_after": "loan_cb_1",
			},
		],
		"Loan": [
			{
				"default": "0",
				"depends_on": 'eval:doc.applicant_type=="Employee"',
				"fieldname": "repay_from_salary",
				"fieldtype": "Check",
				"label": _("Repay From Salary"),
				"insert_after": "status",
			},
		],
		"Loan Repayment": [
			{
				"default": "0",
				"fieldname": "repay_from_salary",
				"fieldtype": "Check",
				"label": _("Repay From Salary"),
				"insert_after": "is_term_loan",
			},
			{
				"depends_on": "eval:doc.repay_from_salary",
				"fieldname": "payroll_payable_account",
				"fieldtype": "Link",
				"label": _("Payroll Payable Account"),
				"mandatory_depends_on": "eval:doc.repay_from_salary",
				"options": "Account",
				"insert_after": "payment_account",
			},
			{
				"default": "0",
				"depends_on": 'eval:doc.applicant_type=="Employee"',
				"fieldname": "process_payroll_accounting_entry_based_on_employee",
				"hidden": 1,
				"fieldtype": "Check",
				"label": _("Process Payroll Accounting Entry based on Employee"),
				"insert_after": "repay_from_salary",
			},
		],
	}


# Project and Task perms are needed for the Employee Onboarding / Separation flow, which
# creates a Project and Tasks and assigns them to users. assign_to.add() does a read check
# on Task, and on_cancel deletes the Project and its Tasks.
_PROJECT_TASK_PERMS = {
	"Project": {"read": 1, "write": 1, "create": 1, "delete": 1},
	"Task": {"read": 1, "write": 1, "create": 1, "delete": 1},
}

# permissions this app grants on other apps' doctypes
HR_ROLE_PERMISSIONS = {
	"HR User": {
		"Role": {"read": 1},
		"Currency": {"read": 1},
		**_PROJECT_TASK_PERMS,
	},
	"HR Manager": {
		"Role": {"read": 1},
		"Currency": {"read": 1},
		"Email Account": {"read": 1},
		**_PROJECT_TASK_PERMS,
	},
}


def add_default_hr_permissions():
	for role, permissions in HR_ROLE_PERMISSIONS.items():
		for doctype, ptypes in permissions.items():
			add_permission(doctype, role)

			for ptype, value in ptypes.items():
				update_permission_property(doctype, role, permlevel=0, ptype=ptype, value=value)


def setup_repost_defaults():
	accounts_settings = frappe.get_doc("Accounts Settings")
	for x in frappe.get_hooks("repost_allowed_doctypes"):
		accounts_settings.append("repost_allowed_types", {"document_type": x})
	accounts_settings.save()
