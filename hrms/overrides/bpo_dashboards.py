# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Keep Desk dashboards, charts, and KPI cards on HRM / payroll / call-center work."""

import json
from pathlib import Path

import frappe

BPO_DASHBOARD_MODULES = ("HR", "Payroll", "Accounts")

# ERPNext manufacturing / projects / stock charts that do not belong in this product.
BLOCKED_CHART_DOCTYPES = frozenset(
	{
		"Quality Inspection",
		"Quality Inspection Reading",
		"Project",
		"Task",
		"BOM",
		"Work Order",
		"Job Card",
		"Production Plan",
		"Sales Order",
		"Sales Invoice",
		"Purchase Order",
		"Purchase Invoice",
		"Delivery Note",
		"Purchase Receipt",
		"Stock Entry",
		"Stock Reconciliation",
		"Lead",
		"Opportunity",
		"Quotation",
		"Issue",
		"Warranty Claim",
		"Maintenance Visit",
		"Asset",
		"Asset Repair",
		"Item",
		"Warehouse",
		"Batch",
		"Serial No",
		"Customer",
		"Supplier",
		"Campaign",
		"Newsletter",
		"Material Request",
		"Packing Slip",
		"Pick List",
		"Subcontracting Order",
		"POS Invoice",
	}
)

CHART_LABELS = {
	"Appraisal Overview": "Review Overview",
	"Attendance Count": "Monthly Attendance",
	"Claims by Type": "Reimbursements by Type",
	"Department Wise Employee Count": "Agents by Team",
	"Department Wise Openings": "Openings by Team",
	"Department Wise Salary(Last Month)": "Pay by Team (Last Month)",
	"Department wise Expense Claims": "Reimbursements by Team",
	"Designation Wise Employee Count": "Agents by Role",
	"Designation Wise Openings": "Openings by Role",
	"Designation Wise Salary(Last Month)": "Pay by Role (Last Month)",
	"Employee Advance Status": "Cash Advance Status",
	"Employees by Age": "Agents by Age",
	"Employees by Branch": "Agents by Site",
	"Employees by Grade": "Agents by Campaign",
	"Employees by Type": "Agents by Type",
	"Expense Claims": "Reimbursements",
	"Gender Diversity Ratio": "Gender Mix",
	"Grievance Type": "Concern Types",
	"Hiring vs Attrition Count": "Hiring vs Attrition",
	"Job Applicant Pipeline": "Candidate Pipeline",
	"Job Applicant Source": "Candidate Source",
	"Job Applicants by Country": "Candidates by Country",
	"Job Application Frequency": "Applications Over Time",
	"Job Application Status": "Application Status",
	"Job Offer Status": "Offer Status",
	"Outgoing Salary": "Payroll Payouts",
	"Shift Assignment Breakup": "Shift Coverage",
	"Training Type": "Training Types",
	"Timesheet Activity Breakup": "Timesheet by Activity",
	"Department wise Timesheet Hours": "Hours by Team",
	"Department Wise Timesheet Hours": "Hours by Team",
	"Y-O-Y Promotions": "Promotions",
	"Y-O-Y Transfers": "Transfers",
}

NUMBER_CARD_LABELS = {
	"Total Employees": "Active Agents",
	"Total Outgoing Salary(Last month)": "Payroll Payouts (Last Month)",
	"Total Present (This Month)": "Present (This Month)",
	"Total Absent (This Month)": "Absent (This Month)",
	"Number of Employees on Leave (Today)": "Agents on Time Off (Today)",
	"Number of Employees on Leave (This Month)": "Agents on Time Off (This Month)",
}


def get_chart_permission_query_conditions(user=None):
	return _module_query("Dashboard Chart")


def get_card_permission_query_conditions(user=None):
	return _module_query("Number Card")


def get_dashboard_permission_query_conditions(user=None):
	return _module_query("Dashboard")


def _module_query(doctype: str) -> str:
	table = f"`tab{doctype}`"
	modules = ", ".join(f"'{m}'" for m in BPO_DASHBOARD_MODULES)
	query = (
		f"(IFNULL({table}.is_standard, 0) = 0"
		f" OR IFNULL({table}.module, '') in ({modules}))"
	)
	if frappe.db.has_column(doctype, "document_type") and BLOCKED_CHART_DOCTYPES:
		blocked = ", ".join(f"'{d}'" for d in sorted(BLOCKED_CHART_DOCTYPES))
		query += f" AND IFNULL({table}.document_type, '') not in ({blocked})"
	return query


def hide_non_bpo_dashboard_records():
	"""Unpublish ERPNext manufacturing/project charts so they are not Desk defaults."""
	_relabel_charts()
	_relabel_number_cards()
	_unpublish_blocked("Dashboard Chart")
	_unpublish_blocked("Number Card")
	_unpublish_blocked("Dashboard")


def _relabel_charts():
	if not frappe.db.table_exists("Dashboard Chart"):
		return
	for name, label in CHART_LABELS.items():
		if frappe.db.exists("Dashboard Chart", name):
			frappe.db.set_value("Dashboard Chart", name, "chart_name", label, update_modified=False)


def _relabel_number_cards():
	if not frappe.db.table_exists("Number Card"):
		return
	for name, label in NUMBER_CARD_LABELS.items():
		if frappe.db.exists("Number Card", name):
			frappe.db.set_value("Number Card", name, "label", label, update_modified=False)


def _unpublish_blocked(doctype: str):
	if not frappe.db.table_exists(doctype):
		return

	filters = {"is_standard": 1}
	if frappe.db.has_column(doctype, "is_public"):
		filters["is_public"] = 1
	fields = ["name", "module"]
	if frappe.db.has_column(doctype, "document_type"):
		fields.append("document_type")

	for row in frappe.get_all(doctype, filters=filters, fields=fields):
		if _is_bpo_record(row):
			continue
		values = {}
		if frappe.db.has_column(doctype, "is_public"):
			values["is_public"] = 0
		if values:
			frappe.db.set_value(doctype, row.name, values, update_modified=False)


def _is_bpo_record(row) -> bool:
	module = (row.get("module") or "").strip()
	if module in BPO_DASHBOARD_MODULES:
		return True
	document_type = (row.get("document_type") or "").strip()
	if document_type and document_type in BLOCKED_CHART_DOCTYPES:
		return False
	if not module:
		return True
	return False


def import_fixture(relative_path: str):
	data = json.loads(Path(frappe.get_app_path("hrms", *relative_path.split("/"))).read_text(encoding="utf-8"))
	doctype = data["doctype"]
	name = data["name"]
	for key in ("creation", "modified", "modified_by", "owner", "docstatus"):
		data.pop(key, None)

	children = {}
	for key in ("roles", "y_axis", "cards", "charts"):
		if key in data:
			children[key] = list(data.pop(key) or [])

	if frappe.db.exists(doctype, name):
		doc = frappe.get_doc(doctype, name)
		doc.update(data)
	else:
		doc = frappe.new_doc(doctype)
		doc.update(data)

	for key, rows in children.items():
		if not hasattr(doc, key):
			continue
		doc.set(key, [])
		for row in rows:
			doc.append(key, row)

	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.save(ignore_permissions=True)
	return doc
