// Copyright (c) 2026, Staff Pro BPO and contributors
// For license information, please see license.txt

frappe.ui.form.on("Social Security Contribution Schedule", {
	refresh(frm) {
		frm.set_query("company", () => ({
			filters: { is_group: 0 },
		}));
	},
});
