// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Attendance", {
	onload(frm) {
		if (hrms.time?.redirect_new_attendance_form?.(frm)) {
			return;
		}
	},

	refresh(frm) {
		if (hrms.time?.redirect_new_attendance_form?.(frm)) {
			return;
		}

		if (frm.doc.__islocal && !frm.doc.attendance_date) {
			frm.set_value("attendance_date", frappe.datetime.get_today());
		}

		frm.trigger("set_working_hours");

		frm.set_query("employee", () => {
			return {
				query: "erpnext.controllers.queries.employee_query",
			};
		});

		if (frm.doc.docstatus === 1 && frm.doc.status === "Absent") {
			frm.add_custom_button(
				__("Attendance Request"),
				() => {
					frappe.new_doc("Attendance Request", {
						employee: frm.doc.employee,
						from_date: frm.doc.attendance_date,
						to_date: frm.doc.attendance_date,
					});
				},
				__("Create"),
			);
		}
	},

	employee(frm) {
		if (frm.doc.employee && frm.doc.attendance_date && !frm.doc.shift) {
			frm.trigger("set_employee_shift");
		}
	},

	attendance_date(frm) {
		if (frm.doc.employee && frm.doc.attendance_date && !frm.doc.shift) {
			frm.trigger("set_employee_shift");
		}
	},

	in_time(frm) {
		frm.trigger("set_working_hours");
	},

	out_time(frm) {
		frm.trigger("set_working_hours");
	},

	set_working_hours(frm) {
		if (!frm.doc.in_time || !frm.doc.out_time) return;
		if (["Absent", "On Leave"].includes(frm.doc.status)) return;
		const hours = hrms.time?.hours_between
			? hrms.time.hours_between(frm.doc.in_time, frm.doc.out_time)
			: 0;
		if (hours && !flt(frm.doc.working_hours)) {
			frm.set_value("working_hours", hours);
		}
	},

	set_employee_shift(frm) {
		if (!frm.doc.employee || !frm.doc.attendance_date) return;

		frappe.call({
			method: "hrms.hr.doctype.attendance.attendance.get_employee_shift",
			args: {
				employee: frm.doc.employee,
				for_date: frm.doc.attendance_date || frappe.datetime.get_today(),
				consider_default_shift: true,
			},
			callback(r) {
				if (r.message && !frm.doc.shift) {
					frm.set_value("shift", r.message);
				}
			},
		});
	},
});
