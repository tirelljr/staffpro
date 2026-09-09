// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Holiday Work Election", {
	employee(frm) {
		if (!frm.doc.employee) {
			frm.set_value("employee_name", "");
		}
	},
});
