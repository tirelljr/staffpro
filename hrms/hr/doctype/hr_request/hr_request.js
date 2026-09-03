// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("HR Request", {
	refresh(frm) {
		if (frm.doc.request_type === "Job Letter") {
			frm.add_custom_button(__("Print Job Letter"), () => {
				frm.print_doc("Job Letter");
			});
		}
	},

	request_type(frm) {
		if (frm.doc.request_type === "Job Letter" && !frm.doc.subject) {
			frm.set_value("subject", __("Job Letter Request"));
		}
	},
});
