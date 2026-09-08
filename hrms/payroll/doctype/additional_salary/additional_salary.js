// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Additional Salary", {
	setup: function (frm) {
		frm.set_query("employee", function () {
			const filters = { status: ["!=", "Inactive"] };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});

		frm.set_query("bonus_type", function () {
			return { filters: { disabled: 0 } };
		});
	},

	onload: function (frm) {
		if (frm.is_new()) {
			if (!frm.doc.company) {
				frm.set_value("company", frappe.defaults.get_user_default("Company"));
			}
			if (!frm.doc.naming_series) {
				frm.set_value("naming_series", "HR-ADS-.YY.-.MM.-");
			}
		}
		frm.trigger("toggle_bonus_fields");
	},

	refresh: function (frm) {
		frm.set_df_property("naming_series", "hidden", 1);
		frm.set_df_property("company", "hidden", 1);
		frm.trigger("toggle_bonus_fields");
		frm.trigger("relabel_bonus_form");
		frm.trigger("hide_templates_button");
	},

	toggle_bonus_fields: function (frm) {
		const system_entry = Boolean(frm.doc.ref_doctype);
		frm.set_df_property("salary_component", "hidden", !system_entry);
		frm.set_df_property("type", "hidden", 1);
		frm.set_df_property("overwrite_salary_structure_amount", "hidden", 1);
		frm.set_df_property("bonus_type", "hidden", system_entry);
		frm.toggle_reqd("bonus_type", !system_entry);
	},

	relabel_bonus_form: function (frm) {
		if (!frm.page) return;
		if (frm.is_new()) {
			frm.page.set_title(__("New Bonus"));
		}
	},

	hide_templates_button: function (frm) {
		const hide = () => {
			frm.remove_custom_button(__("Templates"));
			frm.page?.remove_inner_button?.(__("Templates"));
			if (frm.page?.btn_secondary && (frm.page.btn_secondary.text() || "").trim() === __("Templates")) {
				frm.page.clear_secondary_action();
			}
			const $page = frm.page?.wrapper;
			if (!$page?.length) return;
			$page
				.find("button")
				.filter(function () {
					return ($(this).text() || "").trim() === __("Templates");
				})
				.hide();
		};
		hide();
		setTimeout(hide, 50);
		setTimeout(hide, 300);
	},

	employee: function (frm) {
		if (frm.doc.employee) {
			frappe.run_serially([
				() => frm.trigger("get_employee_currency"),
				() => frm.trigger("set_company"),
			]);
		} else {
			frm.set_value("company", null);
		}
	},

	set_company: function (frm) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Employee",
				fieldname: "company",
				filters: {
					name: frm.doc.employee,
				},
			},
			callback: function (data) {
				if (data.message) {
					frm.set_value("company", data.message.company);
				}
			},
		});
	},

	get_employee_currency: function (frm) {
		frappe.call({
			method: "hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment.get_employee_currency",
			args: {
				employee: frm.doc.employee,
			},
			callback: function (r) {
				if (r.message) {
					frm.set_value("currency", r.message);
					frm.refresh_fields();
				}
			},
		});
	},

	exclude_from_tax: function (frm) {
		if (frm.doc.exclude_from_tax) {
			frm.set_value("deduct_full_tax_on_selected_payroll_date", 0);
		}
	},
});
