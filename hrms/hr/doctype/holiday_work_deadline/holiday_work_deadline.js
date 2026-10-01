// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Holiday Work Deadline", {
	holiday_date(frm) {
		if (!frm.doc.holiday_date && frm.doc.description) {
			frm.set_value("description", "");
		}
	},
});
