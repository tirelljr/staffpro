// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Office Floor", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__("Generate Layout"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Generate Cubicle Rows"),
				fields: [
					{
						fieldname: "row_count",
						fieldtype: "Int",
						label: __("Number of Rows"),
						reqd: 1,
						default: 4,
					},
					{
						fieldname: "seats_per_row",
						fieldtype: "Int",
						label: __("Seats per Row"),
						reqd: 1,
						default: 8,
					},
				],
				primary_action_label: __("Generate"),
				primary_action(values) {
					frappe.call({
						method: "hrms.hr.doctype.office_floor.office_floor.generate_layout",
						args: {
							office_floor: frm.doc.name,
							row_count: values.row_count,
							seats_per_row: values.seats_per_row,
						},
						freeze: true,
						callback(r) {
							const created = r.message?.created || 0;
							frappe.show_alert({
								message: __("Added {0} cubicle(s)", [created]),
								indicator: created ? "green" : "orange",
							});
							dialog.hide();
							frm.refresh();
						},
					});
				},
			});
			dialog.show();
		});
	},
});
