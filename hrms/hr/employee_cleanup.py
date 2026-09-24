# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

"""Remove an agent and every record that blocks deletion."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

# Delete these first so Attendance and payroll docs are not blocked.
EMPLOYEE_LINKED_DOCTYPES: tuple[tuple[str, str, bool], ...] = (
	("Employee Checkin", "employee", False),
	("Time Clock Adjustment", "employee", True),
	("Attendance Request", "employee", True),
	("Attendance", "employee", True),
	("Leave Application", "employee", True),
	("Leave Allocation", "employee", True),
	("Leave Ledger Entry", "employee", False),
	("Leave Adjustment", "employee", True),
	("Leave Policy Assignment", "employee", True),
	("Leave Encashment", "employee", True),
	("Compensatory Leave Request", "employee", True),
	("Shift Assignment", "employee", True),
	("Shift Request", "employee", True),
	("Shift Schedule Assignment", "employee", True),
	("Holiday Work Election", "employee", False),
	("Overtime Slip", "employee", True),
	("Salary Slip", "employee", True),
	("Additional Salary", "employee", True),
	("Salary Structure Assignment", "employee", True),
	("Salary Withholding", "employee", True),
	("Employee Advance", "employee", True),
	("Expense Claim", "employee", True),
	("Employee Incentive", "employee", True),
	("Retention Bonus", "employee", True),
	("Payroll Correction", "employee", True),
	("Arrear", "employee", True),
	("Employee Benefit Application", "employee", True),
	("Employee Benefit Claim", "employee", True),
	("Employee Benefit Ledger", "employee", False),
	("Employee Other Income", "employee", True),
	("Employee Tax Exemption Declaration", "employee", True),
	("Employee Tax Exemption Proof Submission", "employee", True),
	("Gratuity", "employee", True),
	("Full and Final Statement", "employee", True),
	("Exit Interview", "employee", True),
	("Employee Transfer", "employee", True),
	("Employee Promotion", "employee", True),
	("Employee Grievance", "employee", True),
	("Employee Referral", "employee", False),
	("Appraisal", "employee", True),
	("Employee Performance Feedback", "employee", False),
	("Employee Onboarding", "employee", False),
	("Employee Separation", "employee", True),
	("Training Feedback", "employee", False),
	("HR Request", "employee", False),
	("Timesheet", "employee", True),
	("Goal", "employee", False),
	("Daily Work Summary", "employee", False),
)

# Masters that should keep existing — only clear the employee link.
CLEAR_ONLY_DOCTYPES = frozenset(
	{
		"Employee",
		"User",
		"Company",
		"Department",
		"Branch",
		"Designation",
		"Employee Grade",
		"Cubicle",
		"Job Applicant",
		"Job Requisition",
		"Job Opening",
		"Job Offer",
	}
)


# Leave Ledger Entry.on_cancel rejects anything that is not an expired allocation.
SKIP_CANCEL_DOCTYPES = frozenset({"Leave Ledger Entry"})

# Always drop these, even when Employee is not a required field.
ALWAYS_DELETE_DOCTYPES = frozenset(
	{
		"Leave Ledger Entry",
		"Leave Application",
		"Leave Allocation",
		"Leave Adjustment",
		"Leave Policy Assignment",
		"Leave Encashment",
		"Compensatory Leave Request",
	}
)


def _force_delete_doc(doctype, name):
	try:
		doc = frappe.get_doc(doctype, name)
		if cint(doc.docstatus) == 1:
			if doctype in SKIP_CANCEL_DOCTYPES:
				frappe.db.set_value(doctype, name, "docstatus", 2, update_modified=False)
			else:
				doc.flags.ignore_permissions = True
				doc.flags.ignore_links = True
				try:
					doc.cancel()
				except Exception:
					frappe.db.set_value(doctype, name, "docstatus", 2, update_modified=False)
		frappe.delete_doc(
			doctype,
			name,
			force=True,
			ignore_permissions=True,
			ignore_on_trash=True,
			delete_permanently=True,
		)
	except Exception:
		frappe.db.delete(doctype, {"name": name})


def _clear_link_field(doctype: str, fieldname: str, employee: str) -> None:
	if not frappe.db.exists("DocType", doctype):
		return
	if not frappe.db.table_exists(doctype):
		return
	if not frappe.get_meta(doctype).has_field(fieldname):
		return
	frappe.db.set_value(doctype, {fieldname: employee}, fieldname, None, update_modified=False)


def _clear_employee_references(employee: str) -> None:
	frappe.db.set_value("Employee", employee, "reports_to", None, update_modified=False)
	for fieldname in ("reports_to", "leave_approver", "expense_approver"):
		if frappe.get_meta("Employee").has_field(fieldname):
			frappe.db.set_value("Employee", {fieldname: employee}, fieldname, None, update_modified=False)
	_clear_link_field("Employee Transfer", "new_employee_id", employee)
	_clear_link_field("Cubicle", "employee", employee)
	_clear_link_field("Job Applicant", "employee", employee)
	_clear_link_field("Job Requisition", "requested_by", employee)


def _remove_from_child_tables(employee: str) -> None:
	child_tables = {
		"Payroll Entry": "Payroll Employee Detail",
		"Client Invoice": "Client Invoice Item",
		"Employee Tax Adjustment": "Employee Tax Adjustment Employee",
		"Training Event": "Training Event Employee",
		"Training Result": "Training Result Employee",
		"Appraisal": "Appraisee",
	}
	for doctype, child_table in child_tables.items():
		if not frappe.db.exists("DocType", doctype) or not frappe.db.exists("DocType", child_table):
			continue
		if not frappe.get_meta(child_table).has_field("employee"):
			continue
		parents = frappe.get_all(
			child_table,
			filters={"employee": employee, "parenttype": doctype},
			pluck="parent",
			distinct=True,
		)
		for parent in parents:
			frappe.db.delete(
				child_table,
				{"parent": parent, "parenttype": doctype, "employee": employee},
			)
			if doctype == "Appraisal":
				continue
			if not frappe.db.count(child_table, {"parent": parent, "parenttype": doctype}):
				_force_delete_doc(doctype, parent)


def _purge_attendance(employee: str) -> int:
	"""Drop attendance and records that point at those rows."""
	if not frappe.db.exists("DocType", "Attendance"):
		return 0

	names = frappe.get_all("Attendance", filters={"employee": employee}, pluck="name")
	if not names:
		return 0

	if frappe.db.exists("DocType", "Employee Checkin") and frappe.get_meta("Employee Checkin").has_field(
		"attendance"
	):
		frappe.db.set_value(
			"Employee Checkin", {"employee": employee}, "attendance", None, update_modified=False
		)
		frappe.db.sql(
			"update `tabEmployee Checkin` set attendance = null where attendance in %(names)s",
			{"names": names},
		)

	if frappe.db.exists("DocType", "Time Clock Adjustment"):
		meta = frappe.get_meta("Time Clock Adjustment")
		if meta.has_field("attendance"):
			frappe.db.delete("Time Clock Adjustment", {"attendance": ("in", names)})
		if meta.has_field("employee"):
			frappe.db.delete("Time Clock Adjustment", {"employee": employee})

	if frappe.db.exists("DocType", "Overtime Details"):
		frappe.db.delete("Overtime Details", {"reference_document": ("in", names)})

	frappe.db.delete("Attendance", {"employee": employee})
	return len(names)


def _purge_leave_ledger(employee: str) -> int:
	"""Drop ledger rows first so Frappe cannot block Employee delete/cancel."""
	if not frappe.db.exists("DocType", "Leave Ledger Entry"):
		return 0
	if not frappe.db.table_exists("Leave Ledger Entry"):
		return 0

	names = frappe.get_all(
		"Leave Ledger Entry",
		filters={"employee": employee},
		pluck="name",
		ignore_permissions=True,
	)
	if not names:
		return 0

	frappe.db.sql(
		"delete from `tabLeave Ledger Entry` where employee = %s",
		employee,
	)
	return len(names)


def _purge_holiday_list_assignments(employee: str) -> None:
	if not frappe.db.exists("DocType", "Holiday List Assignment"):
		return
	names = frappe.get_all(
		"Holiday List Assignment",
		filters={"applicable_for": "Employee", "assigned_to": employee},
		pluck="name",
	)
	for name in names:
		_force_delete_doc("Holiday List Assignment", name)


def _employee_link_fields() -> list[tuple[str, str]]:
	seen: set[tuple[str, str]] = set()
	rows = frappe.get_all(
		"DocField",
		filters={"fieldtype": "Link", "options": "Employee"},
		fields=["parent", "fieldname"],
	)
	if frappe.db.exists("DocType", "Custom Field"):
		rows += frappe.get_all(
			"Custom Field",
			filters={"fieldtype": "Link", "options": "Employee"},
			fields=["dt as parent", "fieldname"],
		)
	for row in rows:
		key = (row.parent, row.fieldname)
		if key[0] and key[1]:
			seen.add(key)
	return list(seen)


def _delete_or_clear_links(doctype: str, fieldname: str, employee: str) -> int:
	if doctype == "Employee" or not frappe.db.exists("DocType", doctype):
		return 0
	if not frappe.db.table_exists(doctype):
		return 0

	meta = frappe.get_meta(doctype)
	if not meta.has_field(fieldname):
		return 0

	if meta.istable:
		frappe.db.delete(doctype, {fieldname: employee})
		return 1

	names = frappe.get_all(
		doctype, filters={fieldname: employee}, pluck="name", ignore_permissions=True
	)
	if not names:
		return 0

	field = meta.get_field(fieldname)
	clear_optional = doctype in CLEAR_ONLY_DOCTYPES or (
		field and not field.reqd and doctype not in ALWAYS_DELETE_DOCTYPES
	)
	if clear_optional:
		frappe.db.set_value(doctype, {fieldname: employee}, fieldname, None, update_modified=False)
		return len(names)

	if doctype == "Leave Ledger Entry":
		frappe.db.sql("delete from `tabLeave Ledger Entry` where employee = %s", employee)
		return len(names)

	for name in names:
		_force_delete_doc(doctype, name)
	return len(names)


def unlink_employee_records(employee: str, skip_permission: bool = False) -> dict:
	"""Cancel/delete documents linked to one agent."""
	if not skip_permission:
		frappe.has_permission("Employee", "delete", employee, throw=True)

	deleted: dict[str, int] = {}
	was_cleanup = frappe.flags.get("in_employee_cleanup")
	frappe.flags.in_employee_cleanup = True
	try:
		_clear_employee_references(employee)
		_remove_from_child_tables(employee)
		_purge_holiday_list_assignments(employee)

		ledger_count = _purge_leave_ledger(employee)
		if ledger_count:
			deleted["Leave Ledger Entry"] = ledger_count

		attendance_count = _purge_attendance(employee)
		if attendance_count:
			deleted["Attendance"] = attendance_count

		handled = {
			("Attendance", "employee"),
			("Employee", "reports_to"),
			("Leave Ledger Entry", "employee"),
		}
		for doctype, fieldname, _cancel_submitted in EMPLOYEE_LINKED_DOCTYPES:
			if (doctype, fieldname) in handled:
				continue
			count = _delete_or_clear_links(doctype, fieldname, employee)
			handled.add((doctype, fieldname))
			if count:
				deleted[doctype] = deleted.get(doctype, 0) + count

		for doctype, fieldname in _employee_link_fields():
			if (doctype, fieldname) in handled:
				continue
			count = _delete_or_clear_links(doctype, fieldname, employee)
			if count:
				deleted[doctype] = deleted.get(doctype, 0) + count

		# Allocation cancel can recreate ledger rows; drop any leftovers.
		ledger_count = _purge_leave_ledger(employee)
		if ledger_count:
			deleted["Leave Ledger Entry"] = deleted.get("Leave Ledger Entry", 0) + ledger_count
	finally:
		frappe.flags.in_employee_cleanup = was_cleanup

	return deleted


def on_employee_delete(doc, method=None):
	"""Hook: strip attendance and other links before Frappe rejects the delete."""
	if not doc or not doc.name or doc.flags.get("employee_unlinked"):
		return
	doc.flags.employee_unlinked = True
	doc.flags.ignore_links = True
	unlink_employee_records(doc.name, skip_permission=True)


@frappe.whitelist()
def delete_employee_with_unlink(employee: str) -> dict:
	"""Delete one agent after removing attendance, payroll, and other linked records."""
	frappe.only_for(["System Manager", "HR Manager", "HR User"])
	if not employee or not frappe.db.exists("Employee", employee):
		frappe.throw(_("Employee {0} not found").format(employee))

	user_id = frappe.db.get_value("Employee", employee, "user_id")
	deleted = unlink_employee_records(employee)

	frappe.flags.in_employee_cleanup = True
	try:
		frappe.delete_doc(
			"Employee",
			employee,
			force=True,
			ignore_permissions=True,
			flags={"ignore_links": True},
		)
	finally:
		frappe.flags.in_employee_cleanup = False

	if user_id and frappe.db.exists("User", user_id):
		other = frappe.db.count("Employee", {"user_id": user_id, "name": ("!=", employee)})
		if not other:
			try:
				frappe.delete_doc("User", user_id, force=True, ignore_permissions=True)
			except Exception:
				frappe.log_error(title=f"Demo user delete failed {user_id}")

	if not frappe.flags.in_test:
		frappe.db.commit()

	return {"employee": employee, "deleted": deleted, "user_removed": user_id}


@frappe.whitelist()
def delete_employees_with_unlink(employees) -> dict:
	"""Delete multiple agents after unlinking related records."""
	frappe.only_for(["System Manager", "HR Manager", "HR User"])
	if isinstance(employees, str):
		employees = frappe.parse_json(employees)

	removed = []
	errors = []
	for employee in employees or []:
		try:
			delete_employee_with_unlink(employee)
			removed.append(employee)
		except Exception as exc:
			frappe.log_error(title=f"Employee delete failed {employee}")
			errors.append({"employee": employee, "error": str(exc)})

	return {"removed": removed, "errors": errors, "count": len(removed)}


@frappe.whitelist()
def delete_demo_employees(company: str | None = None) -> dict:
	"""Delete all seeded demo agents and their linked records."""
	from hrms.import_hr_demo_data import EMPLOYEES, _get_company, clear_payroll

	frappe.only_for("System Manager")
	company = company or _get_company()
	if not company:
		frappe.throw(_("No company found."))

	clear_payroll(company)

	removed = []
	errors = []
	for emp in EMPLOYEES:
		employee = frappe.db.get_value("Employee", {"company_email": emp["email"], "company": company})
		if not employee:
			continue
		try:
			delete_employee_with_unlink(employee)
			removed.append(employee)
		except Exception:
			if frappe.db.exists("Employee", employee):
				frappe.log_error(title=f"Demo employee delete failed {employee}")
				errors.append(employee)
			else:
				removed.append(employee)

	if not frappe.flags.in_test:
		frappe.db.commit()

	return {"removed": removed, "errors": errors, "count": len(removed)}


def install_employee_delete_patch() -> None:
	from hrms.hr.force_delete import install_force_delete_patch

	install_force_delete_patch()


try:
	install_employee_delete_patch()
except Exception:
	pass
