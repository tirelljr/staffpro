// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payroll Settings", {
	refresh: function (frm) {
		frm.set_query("sender", () => {
			return {
				filters: {
					enable_outgoing: 1,
				},
			};
		});

		hide_payroll_settings_menu(frm);

		if (frm.doc.enable_automatic_payroll && !frm.is_new()) {
			frm.add_custom_button(__("Run Payroll Now"), () => {
				frappe.call({
					method: "hrms.payroll.auto_payroll.run_automatic_payroll_now",
					freeze: true,
					freeze_message: __("Running payroll..."),
					callback: function (r) {
						frm.reload_doc();
						if (r.message && r.message.message) {
							frappe.msgprint(r.message.message);
						}
					},
				});
			});
			show_automatic_payroll_intro(frm);
		}
	},

	encrypt_salary_slips_in_emails: function (frm) {
		let encrypt_state = frm.doc.encrypt_salary_slips_in_emails;
		frm.set_df_property("password_policy", "reqd", encrypt_state);
	},

	validate: function (frm) {
		let policy = frm.doc.password_policy;
		if (policy) {
			if (policy.includes(" ") || policy.includes("--")) {
				frappe.msgprint(
					__(
						"Password policy cannot contain spaces or simultaneous hyphens. The format will be restructured automatically",
					),
				);
			}
			frm.set_value(
				"password_policy",
				policy
					.split(new RegExp(" |-", "g"))
					.filter((token) => token)
					.join("-"),
			);
		}
	},
});

function hide_payroll_settings_menu(frm) {
	const page = frm?.page;
	if (!page) return;
	if (typeof page.hide_menu === "function") {
		page.hide_menu();
	}
	page.menu_btn_group?.addClass("hidden hide").hide();
	page.wrapper?.find(".menu-btn-group").addClass("hidden hide").hide();
}

function show_automatic_payroll_intro(frm) {
	const parts = [];
	if (cint(frm.doc.automatic_payroll_weekly_days)) {
		parts.push(__("Weekly every {0} days", [frm.doc.automatic_payroll_weekly_days]));
	}
	if (cint(frm.doc.automatic_payroll_fortnightly_days)) {
		parts.push(__("2-weeks every {0} days", [frm.doc.automatic_payroll_fortnightly_days]));
	}
	if (cint(frm.doc.automatic_payroll_monthly_days)) {
		parts.push(__("Monthly every {0} days", [frm.doc.automatic_payroll_monthly_days]));
	}
	const schedule = parts.length ? parts.join(", ") : __("set days on each pay template");
	frm.set_intro(
		__("Payroll runs by itself after each pay period ends: {0}. Use Run Payroll Now to process a completed period immediately.", [
			schedule,
		]),
		"blue",
	);
}
