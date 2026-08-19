# Copyright (c) 2026, Staff Pro BPO and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.payroll.social_security import seed_default_ss_schedule


def get_social_security_custom_fields():
	return {
		"Employee": [
			{
				"fieldname": "social_security_section",
				"fieldtype": "Section Break",
				"label": "Social Security",
				"insert_after": "health_insurance_no",
				"collapsible": 1,
			},
			{
				"fieldname": "social_security_number",
				"fieldtype": "Data",
				"label": "Social Security Number",
				"insert_after": "social_security_section",
				"translatable": 0,
			},
			{
				"default": "0",
				"description": "Check if the employee (age 60-64) has received or is receiving a Social Security benefit. Triggers Employment Injury Only contributions.",
				"fieldname": "receiving_social_security_benefit",
				"fieldtype": "Check",
				"label": "Receiving Social Security Benefit",
				"insert_after": "social_security_number",
			},
		],
		"Company": [
			{
				"fieldname": "social_security_section",
				"fieldtype": "Section Break",
				"label": "Social Security",
				"insert_after": "default_payroll_payable_account",
				"collapsible": 1,
			},
			{
				"fieldname": "social_security_registration_no",
				"fieldtype": "Data",
				"label": "Social Security Registration No",
				"insert_after": "social_security_section",
				"translatable": 0,
			},
			{
				"fieldname": "social_security_schedule",
				"fieldtype": "Link",
				"label": "Social Security Contribution Schedule",
				"options": "Social Security Contribution Schedule",
				"insert_after": "social_security_registration_no",
				"description": "Leave blank to use the latest enabled global schedule.",
			},
		],
	}


def execute():
	create_custom_fields(get_social_security_custom_fields(), update=True)
	_ensure_component_type_field()
	seed_default_ss_schedule()


def _ensure_component_type_field():
	"""Create or extend Salary Component.component_type with SS options."""
	options = (
		"\nProvident Fund\nAdditional Provident Fund\nProvident Fund Loan\nProfessional Tax"
		"\nSocial Security\nEmployer Social Security"
	)
	existing = frappe.db.get_value(
		"Custom Field", {"dt": "Salary Component", "fieldname": "component_type"}, "name"
	)
	if existing:
		cf = frappe.get_doc("Custom Field", existing)
		needed = {"Social Security", "Employer Social Security"}
		current = set(filter(None, (cf.options or "").split("\n")))
		if not needed.issubset(current):
			ordered = [
				"Provident Fund",
				"Additional Provident Fund",
				"Provident Fund Loan",
				"Professional Tax",
				"Social Security",
				"Employer Social Security",
			]
			merged = [opt for opt in ordered if opt in current | needed]
			for opt in sorted(current - set(ordered)):
				merged.append(opt)
			cf.options = "\n" + "\n".join(merged)
			cf.depends_on = 'eval:doc.type == "Deduction" || doc.type == "Employer Contribution"'
			cf.save(ignore_permissions=True)
		return

	create_custom_fields(
		{
			"Salary Component": [
				{
					"depends_on": 'eval:doc.type == "Deduction" || doc.type == "Employer Contribution"',
					"fieldname": "component_type",
					"fieldtype": "Select",
					"insert_after": "description",
					"label": "Component Type",
					"options": options,
					"translatable": 0,
				},
			]
		},
		update=True,
	)
