// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

var in_progress = false;

frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Payroll Entry", {
	onload: function (frm) {
		frm.ignore_doctypes_on_cancel_all = [
			"Salary Slip",
			"Journal Entry",
			"Client Invoice",
			"Payroll Settings",
		];

		if (!frm.doc.posting_date) {
			frm.doc.posting_date = frappe.datetime.nowdate();
		}
		frm.toggle_reqd(["payroll_frequency"], 1);
		frm.toggle_reqd("customer", 0);
		frm.set_df_property("customer", "hidden", 1);
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
		frm.toggle_reqd(["payroll_frequency"], 1);
		frm.toggle_reqd("customer", 0);
		frm.set_df_property("customer", "hidden", 1);
		if (hrms.relabel_payroll_frequency) {
			hrms.relabel_payroll_frequency(frm);
		}
		frm.trigger("set_default_bank_account");

		if (frm.doc.status === "Queued") frm.page.btn_secondary.hide();

		if (frm.doc.docstatus === 0 && !cint(frm.doc.salary_slips_created)) {
			if (!frm.is_new()) {
				frm.page.clear_primary_action();
			}
			if (frm.doc.company) {
				frm.add_custom_button(__("Get Agents"), function () {
					frm.events.get_employee_details(frm);
				}).toggleClass("btn-primary", !frm.is_new() && !(frm.doc.employees || []).length);
			}
			if (frm.doc.company && !(frm.doc.employees || []).length) {
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

		hide_payroll_entry_menu(frm);
		setup_payroll_excel_views(frm);

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
		} else if (frm.doc.error_message) {
			frm.dashboard.set_headline(frappe.utils.escape_html(frm.doc.error_message));
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
		if (!frm.doc.company) {
			return;
		}

		const fill_key = [
			frm.doc.customer || "all-agents",
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
				freeze_message: __("Fetching agents"),
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
		} else if (
			!frm.doc.salary_slips_created &&
			(frm.doc.status === "Failed" || frm.doc.status === "Submitted")
		) {
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

		frm.set_query("customer", function () {
			return {
				query: "hrms.payroll.doctype.payroll_entry.payroll_entry.payroll_client_query",
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
			let mandatory_fields = ["company", "payroll_frequency", "start_date", "end_date"];

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

const PAYROLL_EXCEL_MONEY_FIELDS = [
	"holiday_pay",
	"hourly_rate",
	"bonus",
	"gross_pay",
	"income_tax_wh",
	"weekly_insurable_earnings",
	"employee_social_security",
	"employer_social_security",
	"pay_period_ee_social",
	"pay_period_er_social",
	"net_pay",
];

function inject_payroll_excel_styles() {
	let style = document.getElementById("staff-pro-payroll-excel-styles");
	if (!style) {
		style = document.createElement("style");
		style.id = "staff-pro-payroll-excel-styles";
		document.head.appendChild(style);
	}
	style.textContent = `
		body.payroll-excel-fs-open {
			overflow: hidden;
		}
		.payroll-excel-wrap .dt-cell__content--header {
			white-space: nowrap;
		}
		.payroll-excel-wrap .dt-freeze {
			display: none !important;
		}
		.payroll-excel-wrap:not(.is-fullscreen) .dt-scrollable {
			max-height: 480px;
			overflow: auto !important;
		}
		.payroll-excel-wrap.is-fullscreen {
			position: fixed;
			inset: 0;
			z-index: 1050;
			box-sizing: border-box;
			background: var(--bg-color, #f5f7fa);
			padding: 16px 20px;
			display: flex;
			flex-direction: column;
			overflow: hidden;
		}
		.payroll-excel-wrap.is-fullscreen > :first-child {
			flex: 0 0 auto;
		}
		.payroll-excel-wrap.is-fullscreen .payroll-excel-grid {
			flex: 1 1 auto;
			min-height: 0;
			min-width: 0;
			width: 100%;
			overflow: auto;
			background: var(--fg-color, #fff);
		}
		.payroll-excel-wrap.is-fullscreen .datatable {
			position: relative;
			width: max-content;
			min-width: 100%;
			min-height: 100%;
			background: var(--fg-color, #fff);
		}
		.payroll-excel-wrap.is-fullscreen .dt-header,
		.payroll-excel-wrap.is-fullscreen .dt-footer {
			overflow: visible;
			transform: none !important;
			width: max-content;
			min-width: 100%;
			background: transparent;
		}
		.payroll-excel-wrap.is-fullscreen .dt-scrollable {
			width: max-content !important;
			min-width: 100%;
			height: auto !important;
			max-height: none !important;
			overflow: visible !important;
			background: var(--fg-color, #fff);
		}
	`;
}

function payroll_excel_header_width(label) {
	const text = String(label || "");
	const canvas = payroll_excel_header_width._canvas || (payroll_excel_header_width._canvas = document.createElement("canvas"));
	const ctx = canvas.getContext("2d");
	ctx.font = "600 12px Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
	return Math.ceil(ctx.measureText(text).width);
}

function payroll_excel_column_width(col) {
	const id = col.id;
	const labelWidth = payroll_excel_header_width(col.name) + 48;
	const valueMin = {
		agent_name: 180,
		pay_period: 210,
		regular_hours: 128,
		overtime_hours: 140,
		holiday_pay: 120,
		hourly_rate: 120,
		bonus: 90,
		gross_pay: 110,
		income_tax_wh: 140,
		wage_band: 110,
		weekly_insurable_earnings: 220,
		employee_social_security: 210,
		employer_social_security: 210,
		pay_period_ee_social: 180,
		pay_period_er_social: 180,
		net_pay: 110,
	};
	return Math.max(valueMin[id] || 120, labelWidth);
}

function hide_payroll_entry_menu(frm) {
	const page = frm?.page;
	if (!page) return;
	if (typeof page.hide_menu === "function") {
		page.hide_menu();
	}
	page.menu_btn_group?.addClass("hidden hide").hide();
	page.wrapper?.find(".menu-btn-group, .menu-more-button").addClass("hidden hide").hide();
}

function setup_payroll_excel_views(frm) {
	frm._payroll_excel_view = "excel";
	const $wrapper = frm.get_field("payroll_excel_html")?.$wrapper;
	$wrapper?.show();
	$wrapper?.find(".control-label, .grid-heading-level").hide();
	place_payroll_excel_under_overview(frm);
	load_payroll_excel_grid(frm);
}

function place_payroll_excel_under_overview(frm) {
	const $excel = frm.get_field("payroll_excel_html")?.$wrapper;
	const $overview = frm.fields_dict.status?.$wrapper?.closest(".form-section");
	if (!$excel?.length || !$overview?.length) return;
	if ($overview.next().find("[data-fieldname='payroll_excel_html']").length) return;

	const $section = $excel.closest(".form-section");
	const onlyExcelInSection =
		$section?.length &&
		$section[0] !== $overview[0] &&
		$section.find(".frappe-control[data-fieldname]").length <= 1;

	if (onlyExcelInSection) {
		$section.insertAfter($overview);
		return;
	}
	$excel.insertAfter($overview);
}

function load_payroll_excel_grid(frm) {
	const $wrapper = frm.get_field("payroll_excel_html")?.$wrapper;
	if (!$wrapper?.length) return;

	const notice = (text) => $wrapper.html(`<div class="text-muted">${text}</div>`);
	if (frm.is_new()) {
		notice(__("Save this payroll entry to see the spreadsheet."));
		return;
	}

	notice(__("Loading payroll spreadsheet..."));
	frappe
		.call({
			method: "hrms.payroll.doctype.payroll_entry.payroll_entry.get_payroll_excel_data",
			args: { name: frm.doc.name },
		})
		.then((r) => {
			if (frm._payroll_excel_view !== "excel") return;
			mount_payroll_spreadsheet(frm, r.message || { columns: [], rows: [] });
		});
}

function mount_payroll_spreadsheet(frm, payload) {
	const $wrapper = frm.get_field("payroll_excel_html")?.$wrapper;
	if (!$wrapper?.length) return;

	inject_payroll_excel_styles();
	$("body > .payroll-excel-wrap").remove();
	$(document.body).removeClass("payroll-excel-fs-open");
	frm._payroll_excel_payload = payload;

	const period = payload.meta?.pay_period || "";
	const currency = payload.meta?.currency;
	$wrapper.empty().append(
		$(`
		<div class="payroll-excel-wrap">
			<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;overflow:visible;">
				<div class="text-muted"></div>
				<div class="payroll-excel-toolbar-actions" style="display:flex;gap:6px;align-items:center;">
					<div class="sp-report-export payroll-excel-export">
						<button type="button" class="sp-report-export__btn" aria-expanded="false" aria-haspopup="menu">
							<span>${frappe.utils.escape_html(__("Export"))}</span>
						</button>
						<div class="sp-report-export__menu" role="menu" hidden>
							<button type="button" class="sp-report-export__item" data-format="xlsx" role="menuitem">${frappe.utils.escape_html(
								__("Excel"),
							)}</button>
							<button type="button" class="sp-report-export__item" data-format="pdf" role="menuitem">${frappe.utils.escape_html(
								__("PDF"),
							)}</button>
						</div>
					</div>
					<button type="button" class="btn btn-xs btn-default payroll-excel-copy">${__("Copy")}</button>
					<button type="button" class="btn btn-xs btn-primary payroll-excel-bank">${__("Bank Payroll")}</button>
					<button type="button" class="btn btn-xs btn-default payroll-excel-fullscreen">${__("Full Screen")}</button>
				</div>
			</div>
			<div class="payroll-excel-grid"></div>
		</div>
	`),
	);
	$wrapper.find(".text-muted").text([period, currency].filter(Boolean).join(" · "));
	$wrapper.find(".payroll-excel-copy").on("click", () => copy_payroll_excel(payload));
	$wrapper.find(".payroll-excel-bank").on("click", () => download_bank_payroll(frm));
	$wrapper.find(".payroll-excel-fullscreen").on("click", () => toggle_payroll_excel_fullscreen(frm));
	bind_payroll_excel_export($wrapper.find(".payroll-excel-export"), frm);

	const container = $wrapper.find(".payroll-excel-grid").get(0);
	if (!frappe.DataTable) {
		container.innerHTML = render_payroll_excel_fallback_table(payload);
		return;
	}

	const row_data = payload.rows || [];
	const columns = (payload.columns || []).map((col) => ({
		id: col.id,
		name: col.name,
		editable: !!col.editable,
		align: col.align || "left",
		width: payroll_excel_column_width(col),
		resizable: true,
		format: (value) => format_payroll_excel_cell(col.id, value, payload.meta),
	}));

	frm._payroll_excel_datatable = new frappe.DataTable(container, {
		columns,
		data: row_data.map((row) => columns.map((col) => row[col.id] ?? "")),
		layout: "fixed",
		serialNoColumn: false,
		checkboxColumn: false,
		inlineFilters: false,
		disableReorderColumn: true,
		cellHeight: 32,
		noDataMessage: __("No payroll rows yet. Create salary slips to populate this view."),
		getEditor: (colIndex, rowIndex, value, parent, column) =>
			payroll_excel_cell_editor(frm, payload, row_data, column, rowIndex, value, parent),
	});
	if ($wrapper.find(".payroll-excel-wrap").hasClass("is-fullscreen")) {
		size_payroll_excel_fullscreen(frm);
	}
}

function get_payroll_excel_wrap(frm) {
	const $on_body = $("body > .payroll-excel-wrap");
	if ($on_body.length) return $on_body;
	return frm.get_field("payroll_excel_html")?.$wrapper?.find(".payroll-excel-wrap") || $();
}

function toggle_payroll_excel_fullscreen(frm, force) {
	const $wrap = get_payroll_excel_wrap(frm);
	if (!$wrap?.length) return;
	const fullscreen = force == null ? !$wrap.hasClass("is-fullscreen") : !!force;
	if (fullscreen) {
		if (!$wrap.data("payroll-excel-home")) {
			$wrap.data("payroll-excel-home", $wrap.parent()[0]);
		}
		$wrap.appendTo(document.body);
		$(document)
			.off("keydown.payroll-excel-fs")
			.on("keydown.payroll-excel-fs", (event) => {
				if (event.key === "Escape") {
					event.preventDefault();
					event.stopPropagation();
					toggle_payroll_excel_fullscreen(frm, false);
				}
			});
	} else {
		const home = $wrap.data("payroll-excel-home");
		if (home) {
			$wrap.appendTo(home);
		}
		$(document).off("keydown.payroll-excel-fs");
	}
	$wrap.toggleClass("is-fullscreen", fullscreen);
	$(document.body).toggleClass("payroll-excel-fs-open", fullscreen);
	$wrap.find(".payroll-excel-fullscreen").text(fullscreen ? __("Exit Full Screen") : __("Full Screen"));
	size_payroll_excel_fullscreen(frm);
}

function refresh_payroll_excel_dimensions(frm) {
	const dt = frm._payroll_excel_datatable;
	if (!dt) return;
	dt.unfreeze?.();
	if (typeof dt.setDimensions === "function") {
		dt.setDimensions();
	} else {
		dt.style?.setDimensions?.();
		dt.datatable?.setDimensions?.();
	}
}

function size_payroll_excel_fullscreen(frm) {
	const $wrap = get_payroll_excel_wrap(frm);
	if (!$wrap?.length) return;

	const $grid = $wrap.find(".payroll-excel-grid");
	const $scrollable = $wrap.find(".dt-scrollable");
	const $header = $wrap.find(".dt-header, .dt-footer");
	const dt = frm._payroll_excel_datatable;

	$(window).off("resize.payroll-excel-fs");
	if ($wrap.hasClass("is-fullscreen")) {
		$header.css("transform", "none");
		$scrollable.css({ width: "", height: "", maxHeight: "none", overflow: "visible" });
		$(window).on("resize.payroll-excel-fs", () => size_payroll_excel_fullscreen(frm));
	} else {
		$grid.css({ height: "", width: "" });
		$scrollable.css({ height: "", maxHeight: "", width: "", overflow: "" });
		$header.css("transform", "");
	}

	requestAnimationFrame(() => {
		refresh_payroll_excel_dimensions(frm);
		if ($wrap.hasClass("is-fullscreen")) {
			$header.css("transform", "none");
			$scrollable.css({ width: "", height: "", maxHeight: "none", overflow: "visible" });
			dt?.unfreeze?.();
		}
	});
}

// Returns HTML: DataTable inserts custom formatter output without escaping it.
function format_payroll_excel_cell(field, value, meta) {
	if (value == null || value === "") return "";
	if (PAYROLL_EXCEL_MONEY_FIELDS.includes(field)) {
		return format_currency(value, meta?.currency);
	}
	if (field === "regular_hours" || field === "overtime_hours") {
		return format_number(value, null, 2);
	}
	return frappe.utils.escape_html(String(value));
}

function payroll_excel_cell_editor(frm, payload, row_data, column, rowIndex, value, parent) {
	if (!column?.editable) return false;

	const $input = $('<input class="dt-input" type="text">').appendTo(parent);
	return {
		initValue(initial) {
			$input.val(initial ?? value ?? "").focus().select();
		},
		getValue() {
			return $input.val();
		},
		setValue(nextValue) {
			const row = row_data[rowIndex];
			if (!row?.employee || nextValue === value) return;

			return frappe
				.call({
					method: "hrms.payroll.doctype.payroll_entry.payroll_entry.save_payroll_excel_cell",
					args: {
						name: frm.doc.name,
						employee: row.employee,
						field: column.id,
						value: nextValue,
					},
					freeze: true,
					freeze_message: __("Saving..."),
				})
				.then((r) => {
					const updated = r.message || payload;
					const $wrap = frm.get_field("payroll_excel_html")?.$wrapper;
					const wasFullscreen = $wrap?.find(".payroll-excel-wrap").hasClass("is-fullscreen");
					frm._payroll_excel_payload = updated;
					mount_payroll_spreadsheet(frm, updated);
					if (wasFullscreen) {
						toggle_payroll_excel_fullscreen(frm, true);
					}
				});
		},
	};
}

function render_payroll_excel_fallback_table(payload) {
	const columns = payload.columns || [];
	const rows = payload.rows || [];
	const empty_message = __("No payroll rows yet. Create salary slips to populate this view.");

	const cell = (col, row) => {
		const value = format_payroll_excel_cell(col.id, row[col.id], payload.meta);
		return `<td style="text-align:${col.align || "left"};">${value}</td>`;
	};
	const header = columns
		.map((col) => `<th>${frappe.utils.escape_html(col.name)}</th>`)
		.join("");
	const body = rows.length
		? rows.map((row) => `<tr>${columns.map((col) => cell(col, row)).join("")}</tr>`).join("")
		: `<tr><td colspan="${columns.length || 1}" class="text-muted">${empty_message}</td></tr>`;

	return `<div style="overflow:auto;max-height:480px;">
		<table class="table table-bordered" style="margin:0;white-space:nowrap;">
			<thead><tr>${header}</tr></thead><tbody>${body}</tbody>
		</table>
	</div>`;
}

function bind_payroll_excel_export($wrap, frm) {
	if (!$wrap?.length) return;
	const $btn = $wrap.find(".sp-report-export__btn");
	const $menu = $wrap.find(".sp-report-export__menu");

	const close = () => {
		$wrap.removeClass("is-open");
		$btn.attr("aria-expanded", "false");
		$menu.attr("hidden", true);
	};
	const open = () => {
		$wrap.addClass("is-open");
		$btn.attr("aria-expanded", "true");
		$menu.removeAttr("hidden");
	};

	$btn.on("click", (event) => {
		event.preventDefault();
		event.stopPropagation();
		if ($wrap.hasClass("is-open")) close();
		else open();
	});
	$wrap.on("click", ".sp-report-export__item", (event) => {
		event.preventDefault();
		event.stopPropagation();
		const format = $(event.currentTarget).data("format");
		close();
		export_payroll_excel(frm, format);
	});
	$(document)
		.off("click.payroll-excel-export")
		.on("click.payroll-excel-export", (event) => {
			if (!$wrap.hasClass("is-open")) return;
			if (!$.contains($wrap.get(0), event.target)) close();
		});
}

function download_bank_payroll(frm) {
	if (!frm?.doc?.name || frm.is_new()) {
		frappe.msgprint(__("Save this payroll entry before downloading bank payroll."));
		return;
	}
	open_url_post("/api/method/hrms.payroll.doctype.payroll_entry.payroll_entry.download_bank_payroll", {
		name: frm.doc.name,
	});
}

function export_payroll_excel(frm, format) {
	if (!frm?.doc?.name || frm.is_new()) {
		frappe.msgprint(__("Save this payroll entry before exporting."));
		return;
	}
	const method =
		format === "pdf"
			? "hrms.payroll.doctype.payroll_entry.payroll_entry.download_payroll_excel_pdf"
			: "hrms.payroll.doctype.payroll_entry.payroll_entry.download_payroll_excel";
	open_url_post(`/api/method/${method}`, { name: frm.doc.name });
}

function copy_payroll_excel(payload) {
	const columns = payload.columns || [];
	const rows = payload.rows || [];
	const header = columns.map((col) => col.name).join("\t");
	const lines = rows.map((row) => columns.map((col) => row[col.id] ?? "").join("\t"));
	const text = [header, ...lines].join("\n");
	if (navigator.clipboard?.writeText) {
		navigator.clipboard.writeText(text).then(() => {
			frappe.show_alert({ message: __("Copied spreadsheet rows"), indicator: "green" });
		});
		return;
	}
	frappe.msgprint(text);
}

let render_employee_attendance = function (frm, data) {
	frm.fields_dict.attendance_detail_html.html(
		frappe.render_template("employees_with_unmarked_attendance", {
			data: data,
		}),
	);
};

