// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Salary Structure Assignment", {
	setup: function (frm) {
		frm.set_query("employee", function () {
			return {
				query: "erpnext.controllers.queries.employee_query",
				filters: { company: frm.doc.company },
			};
		});
		frm.set_query("salary_structure", function () {
			return {
				filters: {
					company: frm.doc.company,
					docstatus: 1,
					is_active: "Yes",
				},
			};
		});

		frm.set_query("income_tax_slab", function () {
			return {
				filters: {
					company: frm.doc.company,
					docstatus: 1,
					disabled: 0,
					currency: frm.doc.currency,
				},
			};
		});

		frm.set_query("payroll_payable_account", function () {
			var company_currency = erpnext.get_currency(frm.doc.company);
			return {
				filters: {
					company: frm.doc.company,
					root_type: "Liability",
					is_group: 0,
					account_currency: ["in", [frm.doc.currency, company_currency]],
				},
			};
		});

		frm.set_query("cost_center", "payroll_cost_centers", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});
	},

	refresh: function (frm) {
		hide_salary_structure_assignment_menu(frm);
		frm.trigger("toggle_opening_balances_section");
		frm.trigger("display_agent_hourly_rate");

		if (frm.doc.docstatus != 1) return;

		frm.add_custom_button(
			__("Payroll Entry"),
			() => {
				frappe.model.with_doctype("Payroll Entry", () => {
					const doc = frappe.model.get_new_doc("Payroll Entry");
					frappe.set_route("Form", "Payroll Entry", doc.name);
				});
			},
			__("Create"),
		);
		frm.page.set_inner_btn_group_as_primary(__("Create"));

		frm.add_custom_button(
			__("See Agent Hourly Breakdown"),
			function () {
				const hourly = flt(frm._agent_hourly_rate ?? frm.doc.ctc);
				if (!hourly) {
					frm.scroll_to_field("ctc");
					frappe.throw(__("Please set Agent Hourly to see the breakdown."));
				}
				frappe.set_route("query-report", "Employee CTC Break-up", {
					employee: frm.doc.employee,
					salary_structure_assignment: frm.doc.name,
				});
			},
			__("Actions"),
		);
		frm.add_custom_button(
			__("Preview Salary Slip"),
			function () {
				frm.trigger("preview_salary_slip");
			},
			__("Actions"),
		);
	},

	employee: function (frm) {
		if (frm.doc.employee) {
			frm.trigger("set_payroll_cost_centers");
			frm.trigger("toggle_opening_balances_section");
			frm.trigger("display_agent_hourly_rate");
		} else {
			frm.set_value("payroll_cost_centers", []);
			frm.trigger("display_agent_hourly_rate");
		}
	},

	display_agent_hourly_rate: function (frm) {
		show_employee_hourly_rate(frm);
	},

	company: function (frm) {
		// Payroll Payable is unused for BPO direct Bank/Cash payments.
	},

	salary_structure: (frm) => {
		if (frm.doc.salary_structure) {
			frappe.db.get_doc("Salary Structure", frm.doc.salary_structure).then((doc) => {
				frm.clear_table("employee_benefits");
				doc.employee_benefits.forEach((benefit) => {
					const row = frm.add_child("employee_benefits");
					row.salary_component = benefit.salary_component;
					row.amount = benefit.amount;
				});
				refresh_field("employee_benefits");
				calculate_max_benefit_amount(frm.doc);
			});
		}
	},

	preview_salary_slip: function (frm) {
		frappe.db.get_value(
			"Salary Structure",
			frm.doc.salary_structure,
			"salary_slip_based_on_timesheet",
			(r) => {
				const print_format = r.salary_slip_based_on_timesheet
					? "Salary Slip based on Timesheet"
					: "Salary Slip Standard";
				frappe.call({
					method: "hrms.payroll.doctype.salary_structure.salary_structure.make_salary_slip",
					args: {
						source_name: frm.doc.salary_structure,
						employee: frm.doc.employee,
						posting_date: frm.doc.from_date,
						as_print: 1,
						print_format: print_format,
						for_preview: 1,
					},
					callback: function (r) {
						const new_window = window.open();
						new_window.document.write(r.message);
					},
				});
			},
		);
	},

	set_payroll_cost_centers: function (frm) {
		if (frm.doc.payroll_cost_centers && frm.doc.payroll_cost_centers.length < 1) {
			frappe.call({
				method: "set_payroll_cost_centers",
				doc: frm.doc,
				callback: function (data) {
					refresh_field("payroll_cost_centers");
				},
			});
		}
	},

	toggle_opening_balances_section: function (frm) {
		if (!frm.doc.from_date || !frm.doc.employee || !frm.doc.salary_structure) return;

		frm.call("are_opening_entries_required").then((data) => {
			if (data.message) {
				frm.set_df_property("opening_balances_section", "hidden", 0);
			} else {
				frm.set_df_property("opening_balances_section", "hidden", 1);
			}
		});
	},

	from_date: function (frm) {
		if (frm.doc.from_date) {
			frm.trigger("toggle_opening_balances_section");
		}
	},
});

frappe.ui.form.on("Employee Benefit Detail", {
	amount: (frm) => calculate_max_benefit_amount(frm.doc),
});

function hide_salary_structure_assignment_menu(frm) {
	const page = frm?.page;
	if (!page) return;
	if (typeof page.hide_menu === "function") {
		page.hide_menu();
	}
	page.menu_btn_group?.addClass("hidden hide").hide();
	page.wrapper?.find(".menu-btn-group, .menu-more-button").addClass("hidden hide").hide();
}

function show_employee_hourly_rate(frm) {
	const field = frm.get_field("ctc");
	if (!field) return;

	if (!field._agent_hourly_patched) {
		field._agent_hourly_patched = true;
		const original_refresh = field.refresh.bind(field);
		field.refresh = function () {
			original_refresh();
			render_agent_hourly_value(frm, field);
		};
	}

	if (!frm.doc.employee) {
		frm._agent_hourly_rate = 0;
		frm._agent_hourly_employee = null;
		render_agent_hourly_value(frm, field);
		return;
	}

	if (frm._agent_hourly_employee === frm.doc.employee && frm._agent_hourly_rate != null) {
		render_agent_hourly_value(frm, field);
		return;
	}

	frappe.db.get_value("Employee", frm.doc.employee, "ctc").then((r) => {
		frm._agent_hourly_rate = flt(r?.message?.ctc);
		frm._agent_hourly_employee = frm.doc.employee;
		render_agent_hourly_value(frm, field);
	});
}

function render_agent_hourly_value(frm, field) {
	const rate = flt(frm._agent_hourly_rate);
	const formatted = format_currency(rate, frm.doc.currency);
	const $value = field.$wrapper?.find(".control-value");
	if ($value?.length) {
		$value.text(formatted);
	}
	if (field.$input?.length) {
		field.$input.val(rate);
	}
}

let calculate_max_benefit_amount = (doc) => {
	let employee_benefits = doc.employee_benefits || [];
	let max_benefits = 0;
	if (employee_benefits.length > 0) {
		for (let i = 0; i < employee_benefits.length; i++) {
			max_benefits += flt(employee_benefits[i].amount) || 0;
		}
	}
	doc.max_benefits = max_benefits;
	refresh_field("max_benefits");
};
