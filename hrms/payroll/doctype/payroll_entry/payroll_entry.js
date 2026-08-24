// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

var in_progress = false;

frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Payroll Entry", {
	onload: function (frm) {
		frm.ignore_doctypes_on_cancel_all = ["Salary Slip", "Journal Entry", "Client Invoice"];

		if (!frm.doc.posting_date) {
			frm.doc.posting_date = frappe.datetime.nowdate();
		}
		frm.toggle_reqd(["payroll_frequency", "customer"], 1);
		if (frm.is_new()) {
			if (!cint(frm.doc.salary_slip_based_on_timesheet)) {
				frm.set_value("salary_slip_based_on_timesheet", 1);
			}
			if (!frm.doc.payroll_frequency) {
				frm.set_value("payroll_frequency", "Fortnightly");
			}
			frm.set_value("deduct_social_security", 1);
		}

		if (frm.is_new() && !frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_user_default("Company"));
		}
		if (frm.doc.company && !frm.doc.currency) {
			frm.trigger("set_payable_account_and_currency");
		}
		frm.trigger("set_default_bank_account");

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
		frm.events.department_filters(frm);
		frm.events.payroll_payable_account_filters(frm);

		frappe.realtime.off("completed_overtime_slip_creation");
		frappe.realtime.on("completed_overtime_slip_creation", function () {
			frm.reload_doc();
		});

		frappe.realtime.off("completed_overtime_slip_submission");
		frappe.realtime.on("completed_overtime_slip_submission", function () {
			frm.reload_doc();
		});

		frappe.realtime.off("completed_salary_slip_creation");
		frappe.realtime.on("completed_salary_slip_creation", function () {
			frm.reload_doc();
		});

		frappe.realtime.off("completed_salary_slip_submission");
		frappe.realtime.on("completed_salary_slip_submission", function () {
			frm.reload_doc();
		});
	},

	department_filters: function (frm) {
		frm.set_query("department", function () {
			return {
				filters: {
					company: frm.doc.company,
				},
			};
		});
	},

	payroll_payable_account_filters: function (frm) {
		frm.set_query("payroll_payable_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					root_type: "Liability",
					is_group: 0,
				},
			};
		});
	},

	refresh: (frm) => {
		frm.set_df_property("deduct_social_security", "read_only", 1);
		frm.set_df_property("grade", "label", __("Campaign"));
		frm.set_df_property("company", "hidden", 1);
		frm.set_df_property("cost_center", "hidden", 1);
		frm.set_df_property("project", "hidden", 1);
		frm.set_df_property("accounting_dimensions_section", "hidden", 1);
		frm.set_df_property("accounting_dimensions_tab", "hidden", 1);
		frm.set_df_property("payment_account", "hidden", 1);
		frm.set_df_property("overtime_step", "hidden", 1);
		frm.toggle_reqd(["payroll_frequency", "customer"], 1);
		if (hrms.relabel_payroll_frequency) {
			hrms.relabel_payroll_frequency(frm);
		}
		frm.trigger("set_default_bank_account");

		if (frm.doc.status === "Queued") frm.page.btn_secondary.hide();

		if (frm.doc.docstatus === 0 && !cint(frm.doc.salary_slips_created)) {
			if (!frm.is_new()) {
				frm.page.clear_primary_action();
			}
			if (frm.doc.customer) {
				frm.add_custom_button(__("Get Agents"), function () {
					frm.events.get_employee_details(frm);
				}).toggleClass("btn-primary", !frm.is_new() && !(frm.doc.employees || []).length);
			}
			if (frm.doc.customer && !(frm.doc.employees || []).length) {
				frm.events.queue_fill_employees(frm);
			}
		}

		if (
			(frm.doc.employees || []).length &&
			!frappe.model.has_workflow(frm.doctype) &&
			!cint(frm.doc.salary_slips_created) &&
			frm.doc.docstatus != 2
		) {
			if (frm.doc.docstatus == 0 && !frm.is_new()) {
				frm.page.clear_primary_action();
				if (frm.doc.overtime_step === "Create") {
					frm.add_custom_button(__("Create Overtime Slips"), () => {
						frm.call({
							doc: frm.doc,
							method: "create_overtime_slips",
						});
					});
				} else if (frm.doc.overtime_step === "Submit") {
					frm.add_custom_button(__("Submit Overtime Slips"), () => {
						frm.call({
							doc: frm.doc,
							method: "submit_overtime_slips",
						});
					});
				} else {
					frm.page.set_primary_action(__("Create Salary Slips"), () => {
						frm.save("Submit").then(() => {
							frm.page.clear_primary_action();
							frm.refresh();
						});
					});
				}
			}
		}

		if (frm.doc.docstatus == 1) {
			if (frm.custom_buttons) frm.clear_custom_buttons();
			frm.events.add_context_buttons(frm);
		}

		if (frm.doc.status == "Failed" && frm.doc.error_message) {
			const issue = `<a id="jump_to_error" style="text-decoration: underline;">issue</a>`;
			let process = cint(frm.doc.salary_slips_created) ? "submission" : "creation";

			frm.dashboard.set_headline(
				__("Salary Slip {0} failed. You can resolve the {1} and retry {0}.", [
					process,
					issue,
				]),
			);

			$("#jump_to_error").on("click", (e) => {
				e.preventDefault();
				frm.scroll_to_field("error_message");
			});
		}
	},

	queue_fill_employees: function (frm, opts) {
		if (frm._fill_employees_timeout) {
			clearTimeout(frm._fill_employees_timeout);
		}
		frm._fill_employees_timeout = setTimeout(() => {
			frm.events.maybe_fill_employees(frm, opts);
		}, 300);
	},

	maybe_fill_employees: function (frm, opts) {
		opts = opts || {};
		if (frm.doc.docstatus !== 0 || cint(frm.doc.salary_slips_created) || frm._filling_employees) {
			return;
		}
		if (!frm.doc.customer || !frm.doc.company) {
			return;
		}

		const fill_key = [
			frm.doc.customer,
			frm.doc.branch || "",
			frm.doc.department || "",
			frm.doc.designation || "",
			frm.doc.grade || "",
		].join("|");
		if (frm._auto_filled_key === fill_key) {
			return;
		}
		if ((frm.doc.employees || []).length && !opts.force) {
			frm._auto_filled_key = fill_key;
			return;
		}

		frm._auto_filled_key = fill_key;
		return frm.events.get_employee_details(frm, {
			raise_if_empty: 0,
			auto_save: !frm.is_new(),
			scroll: Boolean(opts.scroll),
		});
	},

	reload_employees: function (frm, opts) {
		frm._auto_filled_key = null;
		frm.events.clear_employee_table(frm);
		frm.events.queue_fill_employees(frm, opts);
	},

	get_employee_details: function (frm, opts) {
		opts = Object.assign({ raise_if_empty: 1, scroll: true }, opts || {});
		const auto_save = opts.auto_save !== undefined ? opts.auto_save : !frm.is_new();
		frm._filling_employees = true;

		return Promise.resolve(
			frappe.call({
				method: "hrms.payroll.doctype.payroll_entry.payroll_entry.fill_employee_details",
				args: {
					raise_if_empty: opts.raise_if_empty,
					docs: frm.doc,
					name: frm.doc.name,
				},
				freeze: true,
				freeze_message: __("Fetching agents for this client"),
			}),
		)
			.then((r) => {
				const updated = r.docs?.[0];
				if (updated) {
					frm.doc.employees = updated.employees || [];
					frm.doc.number_of_employees = updated.number_of_employees;
					frm.refresh_field("employees");
					frm.refresh_field("number_of_employees");
				}
				if (updated?.employees?.length && auto_save) {
					frm.dirty();
					return frm.save().then(() => r);
				}
				frm.refresh();
				return r;
			})
			.then((r) => {
				if (r?.docs?.[0]?.validate_attendance) {
					render_employee_attendance(frm, r.message);
				}
				if (opts.scroll) {
					frm.scroll_to_field("employees");
				}
			})
			.finally(() => {
				frm._filling_employees = false;
			});
	},

	create_salary_slip: function (frm) {
		frappe.call({
			method: "run_doc_method",
			args: {
				method: "create_salary_slips",
				dt: "Payroll Entry",
				dn: frm.doc.name,
			},
		});
	},

	add_context_buttons: function (frm) {
		if (
			frm.doc.salary_slips_submitted ||
			(frm.doc.__onload && frm.doc.__onload.submitted_ss)
		) {
			// Payment is booked directly on salary slip submit (Bank/Cash).
			// Keep withheld-salary release only when needed.
			frm.events.add_bank_entry_button(frm);
		} else if (frm.doc.salary_slips_created && frm.doc.status !== "Queued") {
			frm.add_custom_button(__("Submit Salary Slip"), function () {
				submit_salary_slip(frm);
			}).addClass("btn-primary");
		} else if (!frm.doc.salary_slips_created && frm.doc.status === "Failed") {
			frm.add_custom_button(__("Create Salary Slips"), function () {
				frm.trigger("create_salary_slip");
			}).addClass("btn-primary");
		}
	},

	add_bank_entry_button: function (frm) {
		frm.call("has_bank_entries").then((r) => {
			// Direct payment already creates Bank/Cash Entry on slip submit.
			if (r.message.has_bank_entries) {
				return;
			}
			if (!r.message.has_bank_entries_for_withheld_salaries) {
				frm.add_custom_button(__("Release Withheld Salaries"), function () {
					make_bank_entry(frm, (for_withheld_salaries = 1));
				}).addClass("btn-primary");
			}
		});
	},

	setup: function (frm) {
		frm.add_fetch("company", "cost_center", "cost_center");

		frm.set_query("payment_account", function () {
			var account_types = ["Bank", "Cash"];
			return {
				filters: {
					account_type: ["in", account_types],
					is_group: 0,
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("bank_account", function () {
			return {
				query: "hrms.hr.belize_banks.payroll_bank_account_query",
				filters: {
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("employee", "employees", () => {
			let error_fields = [];
			let mandatory_fields = ["customer", "company", "payroll_frequency", "start_date", "end_date"];

			let message = __("Mandatory fields required in {0}", [__(frm.doc.doctype)]);

			mandatory_fields.forEach((field) => {
				if (!frm.doc[field]) {
					error_fields.push(frappe.unscrub(field));
				}
			});

			if (error_fields && error_fields.length) {
				message = message + "<br><br><ul><li>" + error_fields.join("</li><li>") + "</ul>";
				frappe.throw({
					message: message,
					indicator: "red",
					title: __("Missing Fields"),
				});
			}

			return {
				query: "hrms.payroll.doctype.payroll_entry.payroll_entry.employee_query",
				filters: frm.events.get_employee_filters(frm),
			};
		});
	},

	get_employee_filters: function (frm) {
		let filters = {};

		let fields = ["company", "customer", "department", "branch", "designation", "grade"];

		fields.forEach((field) => {
			if (frm.doc[field] || frm.doc[field] === 0) {
				filters[field] = frm.doc[field];
			}
		});

		if (frm.doc.employees) {
			let employees = frm.doc.employees.filter((d) => d.employee).map((d) => d.employee);
			if (employees && employees.length) {
				filters["employees"] = employees;
			}
		}
		return filters;
	},

	payroll_frequency: function (frm) {
		frm.trigger("set_start_end_dates");
	},

	company: function (frm) {
		frm.events.reload_employees(frm);
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
		frm.set_df_property("cost_center", "hidden", 1);
		frm.set_df_property("project", "hidden", 1);
		frm.set_df_property("accounting_dimensions_section", "hidden", 1);
		frm.set_df_property("accounting_dimensions_tab", "hidden", 1);
		frm.set_df_property("payment_account", "hidden", 1);
		frm.set_df_property("overtime_step", "hidden", 1);
		frm.trigger("set_payable_account_and_currency");
		if (frm.doc.docstatus === 0) {
			frm.set_value("bank_account", "");
			frm.trigger("set_default_bank_account");
		}
	},

	set_default_bank_account: function (frm) {
		if (frm.doc.bank_account || !frm.doc.company || frm.doc.docstatus !== 0) {
			return;
		}
		frappe.call({
			method: "hrms.hr.belize_banks.get_default_payroll_bank_account",
			args: { company: frm.doc.company },
			callback: function (r) {
				if (r.message && !frm.doc.bank_account && frm.doc.docstatus === 0) {
					frm.set_value("bank_account", r.message);
				}
			},
		});
	},

	customer: function (frm) {
		frm.events.reload_employees(frm, { scroll: true });
	},

	set_payable_account_and_currency: function (frm) {
		frappe.db.get_value("Company", { name: frm.doc.company }, "default_currency", (r) => {
			frm.set_value("currency", r.default_currency);
		});
	},

	currency: function (frm) {
		var company_currency;
		if (!frm.doc.company) {
			company_currency = erpnext.get_currency(frappe.defaults.get_default("Company"));
		} else {
			company_currency = erpnext.get_currency(frm.doc.company);
		}
		if (frm.doc.currency) {
			if (company_currency != frm.doc.currency) {
				frappe.call({
					method: "erpnext.setup.utils.get_exchange_rate",
					args: {
						from_currency: frm.doc.currency,
						to_currency: company_currency,
					},
					callback: function (r) {
						frm.set_value("exchange_rate", flt(r.message));
						frm.set_df_property("exchange_rate", "hidden", 0);
						frm.set_df_property(
							"exchange_rate",
							"description",
							"1 " + frm.doc.currency + " = [?] " + company_currency,
						);
					},
				});
			} else {
				frm.set_value("exchange_rate", 1.0);
				frm.set_df_property("exchange_rate", "hidden", 1);
				frm.set_df_property("exchange_rate", "description", "");
			}
		}
	},

	department: function (frm) {
		frm.events.reload_employees(frm);
	},
	grade: function (frm) {
		frm.events.reload_employees(frm);
	},
	designation: function (frm) {
		frm.events.reload_employees(frm);
	},

	branch: function (frm) {
		frm.events.reload_employees(frm);
	},

	start_date: function (frm) {
		if (!in_progress && frm.doc.start_date) {
			frm.trigger("set_end_date");
		} else {
			// reset flag
			in_progress = false;
		}
	},

	project: function (frm) {
		frm.events.reload_employees(frm);
	},

	salary_slip_based_on_timesheet: function (frm) {
		frm.toggle_reqd(["payroll_frequency"], 1);
		if (!frm.doc.payroll_frequency) {
			frm.set_value("payroll_frequency", "Fortnightly");
		}
	},

	set_start_end_dates: function (frm) {
		if (frm.doc.payroll_frequency) {
			frappe.call({
				method: "hrms.payroll.doctype.payroll_entry.payroll_entry.get_start_end_dates",
				args: {
					payroll_frequency: frm.doc.payroll_frequency,
					start_date: frm.doc.posting_date,
				},
				callback: function (r) {
					if (r.message) {
						in_progress = true;
						frm.set_value("start_date", r.message.start_date);
						frm.set_value("end_date", r.message.end_date);
					}
				},
			});
		}
	},

	set_end_date: function (frm) {
		frappe.call({
			method: "hrms.payroll.doctype.payroll_entry.payroll_entry.get_end_date",
			args: {
				frequency: frm.doc.payroll_frequency,
				start_date: frm.doc.start_date,
			},
			callback: function (r) {
				if (r.message) {
					frm.set_value("end_date", r.message.end_date);
				}
			},
		});
	},

	validate_attendance: function (frm) {
		if (frm.doc.validate_attendance && frm.doc.employees?.length > 0) {
			frappe.call({
				method: "get_employees_with_unmarked_attendance",
				args: {},
				callback: function (r) {
					render_employee_attendance(frm, r.message);
				},
				doc: frm.doc,
				freeze: true,
				freeze_message: __("Validating Employee Attendance..."),
			});
		} else {
			frm.fields_dict.attendance_detail_html.html("");
		}
	},

	clear_employee_table: function (frm) {
		frm.clear_table("employees");
		frm.refresh_field("employees");
	},
});

// Submit salary slips

const submit_salary_slip = function (frm) {
	frappe.confirm(
		__(
			"This will submit Salary Slips and create accrual Journal Entry. Do you want to proceed?",
		),
		function () {
			frappe.call({
				method: "submit_salary_slips",
				args: {},
				doc: frm.doc,
				freeze: true,
				freeze_message: __("Submitting Salary Slips and creating Journal Entry..."),
			});
		},
		function () {
			if (frappe.dom.freeze_count) {
				frappe.dom.unfreeze();
			}
		},
	);
};

let make_bank_entry = function (frm, for_withheld_salaries = 0) {
	const doc = frm.doc;
	if (doc.bank_account || doc.payment_account) {
		return frappe.call({
			method: "run_doc_method",
			args: {
				method: "make_bank_entry",
				dt: "Payroll Entry",
				dn: frm.doc.name,
				args: { for_withheld_salaries: for_withheld_salaries },
			},
			callback: function () {
				frappe.set_route("List", "Journal Entry", {
					"Journal Entry Account.reference_name": frm.doc.name,
				});
			},
			freeze: true,
			freeze_message: __("Creating Payment Entries......"),
		});
	} else {
		frappe.msgprint(__("Select the bank account this payroll will be wired from"));
		frm.scroll_to_field("bank_account");
	}
};

let render_employee_attendance = function (frm, data) {
	frm.fields_dict.attendance_detail_html.html(
		frappe.render_template("employees_with_unmarked_attendance", {
			data: data,
		}),
	);
};

