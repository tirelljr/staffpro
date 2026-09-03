# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt, formatdate, get_year_ending, get_year_start, getdate

from hrms.hr.doctype.leave_application.leave_application import get_employee_leave_approver
from hrms.hr.report.employee_leave_balance.employee_leave_balance import get_data as get_leave_balance_data
from hrms.hr.utils import get_leave_period


HR_ROLES = ("HR Manager", "HR User", "System Manager", "Administrator")


def _ensure_hr():
	frappe.only_for(list(HR_ROLES))


def _active_employees() -> list[dict]:
	today = getdate()
	rows = frappe.get_list(
		"Employee",
		fields=["name", "employee_name", "company", "department", "image", "date_of_joining", "relieving_date"],
		filters={"status": "Active"},
		order_by="employee_name",
	)
	active = []
	for row in rows:
		if row.date_of_joining and getdate(row.date_of_joining) > today:
			continue
		if row.relieving_date and getdate(row.relieving_date) < today:
			continue
		active.append(
			{
				"name": row.name,
				"employee_name": row.employee_name or row.name,
				"company": row.company,
				"department": row.department,
				"image": row.image,
			}
		)
	return active


def _leave_types() -> list[dict]:
	return frappe.get_all(
		"Leave Type",
		fields=["name", "leave_type_name", "is_lwp"],
		order_by="leave_type_name",
	)


def _balance_period(company: str | None = None) -> tuple:
	today = getdate()
	if company:
		periods = get_leave_period(today, today, company) or []
		if periods:
			return getdate(periods[0].from_date), getdate(periods[0].to_date)
	return get_year_start(today), get_year_ending(today)


def _absence_status_class(status: str | None) -> str:
	status = str(status or "")
	if status == "Approved":
		return "approved"
	if status == "Open":
		return "open"
	if status == "Rejected":
		return "rejected"
	return "cancelled"


def _absence_status_label(status: str | None) -> str:
	status = str(status or "")
	if status == "Approved":
		return _("Approved")
	if status == "Open":
		return _("Pending")
	return status or _("—")


def _absence_date_label(from_date, to_date) -> str:
	if not from_date:
		return ""
	if from_date == to_date:
		return formatdate(from_date)
	return f"{formatdate(from_date)} – {formatdate(to_date)}"


def _employee_company(employee: str | None) -> str | None:
	if employee:
		return frappe.db.get_value("Employee", employee, "company")
	return frappe.defaults.get_user_default("Company")


def _balance_rows(employee: str | None = None) -> list[dict]:
	company = _employee_company(employee)
	from_date, to_date = _balance_period(company)
	filters = frappe._dict(
		{
			"from_date": from_date,
			"to_date": to_date,
			"consolidate_leave_types": 0,
			"employee_status": "Active",
		}
	)
	if company:
		filters.company = company
	if employee:
		filters.employee = employee

	rows = []
	for row in get_leave_balance_data(filters) or []:
		if not row.get("employee"):
			continue
		rows.append(
			{
				"leave_type": row.get("leave_type"),
				"employee": row.get("employee"),
				"employee_name": row.get("employee_name"),
				"opening_balance": flt(row.get("opening_balance")),
				"leaves_allocated": flt(row.get("leaves_allocated")),
				"leaves_taken": flt(row.get("leaves_taken")),
				"leaves_expired": flt(row.get("leaves_expired")),
				"closing_balance": flt(row.get("closing_balance")),
			}
		)
	return rows


def _absence_rows(employee: str | None = None, company: str | None = None) -> list[dict]:
	company = company or _employee_company(employee)
	if not company:
		return []

	today = getdate()
	LeaveApplication = frappe.qb.DocType("Leave Application")
	query = (
		frappe.qb.from_(LeaveApplication)
		.select(
			LeaveApplication.name,
			LeaveApplication.employee,
			LeaveApplication.employee_name,
			LeaveApplication.leave_type,
			LeaveApplication.from_date,
			LeaveApplication.to_date,
			LeaveApplication.description,
			LeaveApplication.status,
		)
		.where(LeaveApplication.company == company)
		.where(LeaveApplication.to_date >= today)
		.where(LeaveApplication.docstatus != 2)
		.where(LeaveApplication.status.isin(["Open", "Approved"]))
		.orderby(LeaveApplication.from_date)
		.orderby(LeaveApplication.employee_name)
	)
	if employee:
		query = query.where(LeaveApplication.employee == employee)

	rows = []
	for rec in query.run(as_dict=True):
		rows.append(
			{
				"leave_application": rec.name,
				"employee": rec.employee,
				"employee_name": rec.employee_name,
				"leave_type": rec.leave_type,
				"from_date": rec.from_date,
				"to_date": rec.to_date,
				"date_label": _absence_date_label(rec.from_date, rec.to_date),
				"description": rec.description or "",
				"status": rec.status,
				"status_label": _absence_status_label(rec.status),
				"status_class": _absence_status_class(rec.status),
			}
		)
	return rows


@frappe.whitelist()
def get_page_context(employee: str | None = None) -> dict:
	_ensure_hr()
	if employee:
		frappe.has_permission("Employee", "read", employee, throw=True)

	company = _employee_company(employee)
	from_date, to_date = _balance_period(company)
	return {
		"employees": _active_employees(),
		"leave_types": _leave_types(),
		"balances": _balance_rows(employee),
		"absences": _absence_rows(employee, company),
		"from_date": from_date,
		"to_date": to_date,
		"period_label": f"{formatdate(from_date)} – {formatdate(to_date)}",
	}


@frappe.whitelist()
def book_time_off(employee: str, leave_type: str, from_date: str, to_date: str | None = None) -> dict:
	_ensure_hr()
	frappe.has_permission("Leave Application", "create", throw=True)

	from_date = getdate(from_date)
	to_date = getdate(to_date or from_date)
	if to_date < from_date:
		frappe.throw(_("End date cannot be before start date."))

	approver = get_employee_leave_approver(employee) or frappe.session.user
	leave = frappe.get_doc(
		{
			"doctype": "Leave Application",
			"employee": employee,
			"leave_type": leave_type,
			"from_date": from_date,
			"to_date": to_date,
			"leave_approver": approver,
			"status": "Approved",
			"description": leave_type,
		}
	)
	leave.insert()
	if leave.status != "Approved":
		leave.status = "Approved"
	if leave.docstatus == 0:
		leave.submit()

	return {
		"name": leave.name,
		"message": _("Time off booked for {0}").format(leave.employee_name or employee),
	}


@frappe.whitelist()
def allocate_pto(employee: str, leave_type: str, days: float | str = 10) -> dict:
	_ensure_hr()
	frappe.has_permission("Leave Allocation", "create", throw=True)

	days = flt(days)
	if days <= 0:
		frappe.throw(_("Enter how many PTO days to allocate."))

	if frappe.db.get_value("Leave Type", leave_type, "is_lwp"):
		frappe.throw(_("{0} is unpaid and cannot be allocated.").format(leave_type))

	company = frappe.db.get_value("Employee", employee, "company")
	from_date, to_date = _balance_period(company)

	existing = frappe.db.get_value(
		"Leave Allocation",
		{
			"employee": employee,
			"leave_type": leave_type,
			"docstatus": 1,
			"from_date": ("<=", to_date),
			"to_date": (">=", from_date),
		},
		"name",
	)
	if existing:
		allocation = frappe.get_doc("Leave Allocation", existing)
		frappe.has_permission("Leave Allocation", "write", allocation, throw=True)
		allocation.new_leaves_allocated = flt(allocation.new_leaves_allocated) + days
		allocation.save()
		return {
			"name": allocation.name,
			"message": _("Added {0} day(s) of {1}").format(frappe.format_value(days, {"fieldtype": "Float"}), leave_type),
		}

	allocation = frappe.get_doc(
		{
			"doctype": "Leave Allocation",
			"employee": employee,
			"leave_type": leave_type,
			"from_date": from_date,
			"to_date": to_date,
			"new_leaves_allocated": days,
		}
	)
	allocation.insert()
	allocation.submit()
	return {
		"name": allocation.name,
		"message": _("Allocated {0} day(s) of {1}").format(frappe.format_value(days, {"fieldtype": "Float"}), leave_type),
	}
