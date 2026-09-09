// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Time Clock Adjustment", {
	employee(frm) {
		if (!frm.doc.employee) {
			frm.set_value("employee_name", "");
			frm.set_value("department", "");
			frm.set_value("company", "");
		}
	},
});
