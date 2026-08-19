// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payroll Period", {
	onload: function (frm) {
		frm.trigger("set_start_date");
	},

	set_start_date: function (frm) {
		if (!frm.doc.__islocal) return;

		frappe.db
			.get_list("Payroll Period", {
				fields: ["end_date"],
				order_by: "end_date desc",
				limit: 1,
			})
			.then((result) => {
				// set start date based on end date of the last payroll period if found
				// else set it based on the current fiscal year's start date
				if (result.length) {
					const last_end_date = result[0].end_date;
					frm.set_value("start_date", frappe.datetime.add_days(last_end_date, 1));
				} else {
					frm.set_value("start_date", frappe.defaults.get_default("year_start_date"));
				}
			});
	},

	start_date: function (frm) {
		frm.set_value(
			"end_date",
			frappe.datetime.add_days(frappe.datetime.add_months(frm.doc.start_date, 12), -1),
		);
	},

	refresh: function (frm) {
		if (frm.doc.__islocal) return;

		const open_adjustment = (adjustment_type) => {
			frappe.route_options = {
				company: frm.doc.company,
				payroll_period: frm.doc.name,
				adjustment_type,
				valid_from: frm.doc.start_date,
				valid_to: frm.doc.end_date,
			};
			frappe.new_doc("Employee Tax Adjustment");
		};

		frm.add_custom_button(__("Exclude Agents from Tax"), () => open_adjustment("Exclude from Tax Period"), __("Tax"));
		frm.add_custom_button(__("Include Agents in Tax"), () => open_adjustment("Include in Tax Period"), __("Tax"));
	},
});
