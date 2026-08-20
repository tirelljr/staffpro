// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Holiday List", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__("Get Belize Holidays"), () => {
			frappe.call({
				method: "hrms.hr.belize_holidays.get_belize_holidays_for_list",
				args: { holiday_list: frm.doc.name },
				freeze: true,
				callback(r) {
					frm.reload_doc();
					if (r.message && r.message.message) {
						frappe.show_alert({ message: r.message.message, indicator: "green" });
					}
				},
			});
		});
	},

	pay_time_and_a_half(frm) {
		if (frm.doc.pay_time_and_a_half && frm.doc.pay_double_time) {
			frm.set_value("pay_double_time", 0);
		}
	},

	pay_double_time(frm) {
		if (frm.doc.pay_double_time && frm.doc.pay_time_and_a_half) {
			frm.set_value("pay_time_and_a_half", 0);
		}
	},
});
