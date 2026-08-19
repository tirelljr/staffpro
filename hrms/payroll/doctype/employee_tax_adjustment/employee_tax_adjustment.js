// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Employee Tax Adjustment", {
	setup: function (frm) {
		frm.set_query("payroll_period", function () {
			return {
				filters: {
					company: frm.doc.company,
				},
			};
		});
		frm.set_query("employee", "employees", function () {
			return {
				filters: {
					company: frm.doc.company,
					status: ["!=", "Inactive"],
				},
			};
		});
		frm.set_query("salary_component", "excluded_components", function () {
			return {
				filters: {
					type: "Earning",
					disabled: 0,
				},
			};
		});
		frm.set_query("income_tax_slab", function () {
			return {
				filters: {
					disabled: 0,
					docstatus: 1,
				},
			};
		});
	},

	company: function (frm) {
		if (frm.doc.payroll_period) {
			frm.set_value("payroll_period", null);
		}
	},

	payroll_period: function (frm) {
		if (!frm.doc.payroll_period) return;
		frappe.db.get_value("Payroll Period", frm.doc.payroll_period, ["start_date", "end_date", "company"]).then(
			(r) => {
				if (!r.message) return;
				if (r.message.company && !frm.doc.company) {
					frm.set_value("company", r.message.company);
				}
				if (!frm.doc.valid_from) {
					frm.set_value("valid_from", r.message.start_date);
				}
				if (!frm.doc.valid_to) {
					frm.set_value("valid_to", r.message.end_date);
				}
			},
		);
	},
});
