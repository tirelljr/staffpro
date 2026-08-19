// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Social Security Contribution Table", {
	refresh: function (frm) {
		frm.set_query("company", function () {
			return {};
		});
	},
});
