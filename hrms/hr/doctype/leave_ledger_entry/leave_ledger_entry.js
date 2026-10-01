// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Leave Ledger Entry", {
	onload(frm) {
		frm.ignore_doctypes_on_cancel_all = [
			"Leave Allocation",
			"Leave Application",
			"Leave Encashment",
			"Leave Adjustment",
		];
	},
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;
		frm.page.clear_secondary_action();
		frm.page.btn_secondary?.hide();
	},
});
