// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bonus Type", {
	refresh: function (frm) {
		frm.trigger("toggle_auto_calculate_fields");
	},

	auto_calculate: function (frm) {
		frm.trigger("toggle_auto_calculate_fields");
	},

	toggle_auto_calculate_fields: function (frm) {
		const show = Boolean(cint(frm.doc.auto_calculate));
		["period_months", "attendance_target", "if_below", "bonus_amount"].forEach((field) => {
			frm.toggle_display(field, show);
		});
	},
});
