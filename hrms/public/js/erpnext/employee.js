// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const assignable_masters = {};

function get_assignment_actions() {
	return [
		{
			label: __("Holiday List"),
			doctype: "Holiday List Assignment",
			master_field: "holiday_list",
			prefill: (frm) => ({
				applicable_for: "Employee",
				assigned_to: frm.doc.name,
				employee_name: frm.doc.employee_name,
				employee_company: frm.doc.company,
			}),
			hide: ["naming_series"],
			on_change: {
				holiday_list: sync_holiday_list_range,
				from_date: flag_start_date_outside_range,
			},
		},
		{
			label: __("Leave Policy"),
			doctype: "Leave Policy Assignment",
			master: "Leave Policy",
			master_field: "leave_policy",
			prefill: (frm) => ({ employee: frm.doc.name }),
			queries: (frm) => ({
				leave_policy: { docstatus: 1 },
				leave_period: { is_active: 1, company: frm.doc.company },
			}),
			on_change: {
				assignment_based_on: set_leave_effective_dates,
				leave_period: set_leave_effective_dates,
			},
		},
		{
			label: __("Salary Structure"),
			doctype: "Salary Structure Assignment",
			master: "Salary Structure",
			prefill: (frm) => ({ employee: frm.doc.name, company: frm.doc.company }),
			redirect: true,
		},
		{
			label: __("Shift"),
			doctype: "Shift Assignment",
			prefill: (frm) => ({ employee: frm.doc.name, company: frm.doc.company }),
			redirect: true,
		},
		{
			label: __("Shift Schedule"),
			doctype: "Shift Schedule Assignment",
			master: "Shift Schedule",
			prefill: (frm) => ({ employee: frm.doc.name, company: frm.doc.company }),
			redirect: true,
		},
	];
}

function get_assignable_masters(company) {
	if (!assignable_masters[company]) {
		assignable_masters[company] = frappe
			.xcall("hrms.overrides.employee_master.get_assignable_masters", { company })
			.catch(() => {
				delete assignable_masters[company];
				return {};
			});
	}

	return assignable_masters[company];
}

function open_assignment(frm, action) {
	if (action.redirect) return frappe.new_doc(action.doctype, action.prefill(frm));

	frappe.model.with_doctype(action.doctype, () => {
		const doc = Object.assign(
			frappe.model.get_new_doc(action.doctype, null, null, true),
			action.prefill(frm),
		);

		frappe.ui.form.make_quick_entry(
			action.doctype,
			(created_doc) => notify_assignment_created(action, created_doc),
			(dialog) => setup_dialog(dialog, action, frm),
			doc,
			true,
		);
	});
}

function setup_dialog(dialog, action, frm) {
	for (const [fieldname, filters] of Object.entries(action.queries?.(frm) || {}))
		dialog.set_query(fieldname, () => ({ filters }));

	for (const fieldname of action.hide || []) {
		const control = dialog.fields_dict[fieldname];
		if (!control) continue;

		control.df = { ...control.df, hidden: 1 };
		control.refresh();
	}

	for (const [fieldname, handler] of Object.entries(action.on_change || {})) {
		const control = dialog.fields_dict[fieldname];
		if (!control) continue;

		control.df = { ...control.df, onchange: () => handler(dialog, frm) };
	}

	dialog.add_custom_action(__("Edit Full Form"), () => dialog.open_doc(false));
	keep_dialog_open_for_submit(dialog);
}

function keep_dialog_open_for_submit(dialog) {
	dialog.set_primary_action(__("Save"), () => {
		if (dialog.working || !dialog.get_values()) return;

		dialog.working = true;
		dialog.insert().finally(() => (dialog.working = false));
	});
}

function set_field_hint(dialog, fieldname, title) {
	dialog.modal_body.find(".assignment-hint").remove();
	if (!title) return;

	frappe.ui
		.alert({ title, theme: "blue", css_class: "assignment-hint" })
		.insertAfter(dialog.fields_dict[fieldname].$wrapper);
}

async function sync_holiday_list_range(dialog) {
	const holiday_list = dialog.get_value("holiday_list");
	dialog.holiday_list_range = null;

	if (holiday_list) {
		const response = await frappe.db.get_value("Holiday List", holiday_list, [
			"from_date",
			"to_date",
		]);
		dialog.holiday_list_range = response.message?.from_date ? response.message : null;
	}

	const range_start = dialog.holiday_list_range?.from_date;
	if (range_start && !dialog.get_value("from_date"))
		await dialog.set_value("from_date", range_start);

	flag_start_date_outside_range(dialog);
}

async function set_leave_effective_dates(dialog, frm) {
	const assignment_based_on = dialog.get_value("assignment_based_on");

	if (!assignment_based_on) {
		await dialog.set_value("effective_from", "");
		await dialog.set_value("effective_to", "");
		return;
	}

	if (assignment_based_on === "Joining Date") {
		await dialog.set_value("effective_from", frm.doc.date_of_joining);
		await dialog.set_value(
			"effective_to",
			frappe.datetime.add_months(frm.doc.date_of_joining, 12),
		);
		return;
	}

	const leave_period = dialog.get_value("leave_period");
	if (!leave_period) return;

	const response = await frappe.db.get_value("Leave Period", leave_period, [
		"from_date",
		"to_date",
	]);
	if (!response.message) return;

	await dialog.set_value("effective_from", response.message.from_date);
	await dialog.set_value("effective_to", response.message.to_date);
}

function flag_start_date_outside_range(dialog) {
	const range = dialog.holiday_list_range;
	const from_date = dialog.get_value("from_date");
	if (!range || !from_date) return set_field_hint(dialog, "from_date", null);

	const outside =
		frappe.datetime.get_diff(from_date, range.from_date) < 0 ||
		frappe.datetime.get_diff(from_date, range.to_date) > 0;

	set_field_hint(
		dialog,
		"from_date",
		outside &&
			__("Assignment must start between {0} and {1}", [
				frappe.datetime.str_to_user(range.from_date),
				frappe.datetime.str_to_user(range.to_date),
			]),
	);
}

function notify_assignment_created(action, doc) {
	frappe.quick_entry?.hide();

	const master_doctype = frappe.meta.get_docfield(action.doctype, action.master_field).options;

	frappe.show_alert({
		message: __("{0} was assigned {1}", [
			__(master_doctype),
			frappe.utils.get_form_link(action.doctype, doc.name, true),
		]),
		indicator: "green",
	});
}

frappe.ui.form.on("Employee", {
	onload: function (frm) {
		set_employee_salary_defaults(frm);
	},

	refresh: function (frm) {
		frm.set_query("payroll_cost_center", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});

		// filter advance account based on salary currency
		if (frm.doc.salary_currency) {
			frm.set_query("employee_advance_account", function () {
				return {
					filters: {
						root_type: "Asset",
						is_group: 0,
						company: frm.doc.company,
						account_currency: frm.doc.salary_currency,
						account_type: "Receivable",
					},
				};
			});
		}
		for (const fieldname of [
			"salutation",
			"prefered_contact_email",
			"unsubscribed",
			"attendance_device_id",
			"provident_fund_account",
			"employee_advance_account",
			"payroll_cost_center",
			"health_insurance_section",
			"health_insurance_provider",
			"health_insurance_no",
			"holiday_list",
			"iban",
		]) {
			frm.set_df_property(fieldname, "hidden", 1);
		}
		frm.set_df_property("grade", "label", __("Campaign"));
		setup_belize_bank_picker(frm);

		// hide naming series field based on hr settings
		frappe.db.get_single_value("HR Settings", "emp_created_by").then((value) => {
			frm.toggle_display("naming_series", value === "Naming Series");
		});

		frm.trigger("add_assignment_actions");
		frm.trigger("add_hourly_rate_action");
		setup_employee_form_chrome(frm);
		set_employee_salary_defaults(frm);
	},

	add_hourly_rate_action: function (frm) {
		if (!flt(frm.doc.ctc)) return;
		frm.add_custom_button(__("Apply Hourly Rate"), () => open_apply_hourly_rate_dialog(frm));
	},

	ctc: function (frm) {
		if (!flt(frm.doc.ctc)) return;
		frappe.confirm(
			__("Apply this hourly rate to other agents, a branch, campaign, or team?"),
			() => open_apply_hourly_rate_dialog(frm),
		);
	},

	add_assignment_actions: async function (frm) {
		if (frm.is_new() || frm.doc.status !== "Active") return;

		const available_masters = await get_assignable_masters(frm.doc.company);

		for (const action of get_assignment_actions()) {
			if (action.master && !available_masters[action.master]) continue;
			if (!frappe.model.can_create(action.doctype)) continue;

			frm.add_custom_button(
				action.label,
				() => open_assignment(frm, action),
				__("Create Assignments"),
			);
		}
	},

	date_of_birth(frm) {
		frm.call({
			method: "hrms.overrides.employee_master.get_retirement_date",
			args: {
				date_of_birth: frm.doc.date_of_birth,
			},
		}).then((r) => {
			if (r && r.message) frm.set_value("date_of_retirement", r.message);
		});
	},

	salary_mode(frm) {
		setup_belize_bank_picker(frm);
	},

	bank_name(frm) {
		setup_belize_bank_picker(frm);
	},
});

function set_employee_salary_defaults(frm) {
	if (!frm.is_new()) return;
	if (!frm.doc.salary_currency) {
		frm.set_value("salary_currency", "BZD");
	}
	if (!frm.doc.salary_mode) {
		frm.set_value("salary_mode", "Bank");
	}
}

function hourly_rate_dialog_values(d) {
	const employees = (d.get_value("employees") || [])
		.map((row) => row.employee)
		.filter(Boolean);
	const branches = d.get_value("branch") ? [d.get_value("branch")] : [];
	const campaigns = d.get_value("campaign") ? [d.get_value("campaign")] : [];
	const teams = d.get_value("team") ? [d.get_value("team")] : [];
	return { employees, branches, campaigns, teams };
}

function open_apply_hourly_rate_dialog(frm) {
	const rate = flt(frm.doc.ctc);
	if (!rate) {
		frappe.msgprint(__("Set Agent Hourly first."));
		frm.scroll_to_field("ctc");
		return;
	}

	const currency = frm.doc.salary_currency || "BZD";
	const dialog = new frappe.ui.Dialog({
		title: __("Apply Hourly Rate"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "rate_html",
				options: `<p>${__("Apply {0}/hr to other agents, a branch, campaign, or team.", [
					format_currency(rate, currency),
				])}</p>`,
			},
			{
				fieldtype: "Table",
				fieldname: "employees",
				label: __("Other Agents"),
				cannot_add_rows: false,
				in_place_edit: true,
				data: [],
				fields: [
					{
						fieldtype: "Link",
						fieldname: "employee",
						options: "Employee",
						in_list_view: 1,
						reqd: 1,
						label: __("Agent"),
						get_query: () => ({
							filters: {
								status: "Active",
								company: frm.doc.company,
								name: ["!=", frm.doc.name],
							},
						}),
					},
				],
			},
			{
				fieldtype: "Section Break",
				label: __("Or by group"),
			},
			{
				fieldtype: "Link",
				fieldname: "branch",
				label: __("Branch"),
				options: "Branch",
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Link",
				fieldname: "campaign",
				label: __("Campaign"),
				options: "Employee Grade",
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Link",
				fieldname: "team",
				label: __("Team"),
				options: "Department",
				get_query: () => ({
					filters: { company: frm.doc.company },
				}),
			},
		],
		primary_action_label: __("Apply"),
		primary_action: () => {
			const args = hourly_rate_dialog_values(dialog);
			if (
				!args.employees.length &&
				!args.branches.length &&
				!args.campaigns.length &&
				!args.teams.length
			) {
				frappe.msgprint(__("Select other agents, a branch, campaign, or team."));
				return;
			}

			frappe.call({
				method: "hrms.hr.bpo_hourly_rate.preview_hourly_rate_targets",
				args: { source_employee: frm.doc.name, company: frm.doc.company, ...args },
			}).then((preview) => {
				const count = preview.message?.count || 0;
				if (!count) {
					frappe.msgprint(__("No other active agents match that selection."));
					return;
				}
				frappe.confirm(
					__("Update Agent Hourly to {0}/hr for {1} agent(s)?", [
						format_currency(rate, currency),
						count,
					]),
					() => {
						frappe.call({
							method: "hrms.hr.bpo_hourly_rate.apply_hourly_rate",
							args: {
								source_employee: frm.doc.name,
								hourly_rate: rate,
								company: frm.doc.company,
								...args,
							},
							freeze: true,
							freeze_message: __("Updating hourly rates..."),
						}).then((r) => {
							const updated = r.message?.updated || 0;
							frappe.show_alert({
								message: __("Updated Agent Hourly for {0} agent(s).", [updated]),
								indicator: "green",
							});
							dialog.hide();
						});
					},
				);
			});
		},
	});
	dialog.show();
	const employee_field = dialog.fields_dict.employees?.grid?.get_field("employee");
	if (employee_field) {
		employee_field.get_query = () => ({
			filters: {
				status: "Active",
				company: frm.doc.company,
				name: ["!=", frm.doc.name || ""],
			},
		});
	}
}

function setup_employee_form_chrome(frm) {
	const $page = frm.page?.wrapper || frm.$wrapper;
	if (!$page?.length) {
		return;
	}

	$page.find(".form-sidebar .modified-by, .form-sidebar .created-by").each(function () {
		$(this).closest(".sidebar-section").hide();
	});
}

const BELIZE_BANKS = [
	{
		name: "Heritage Bank",
		logo: "/assets/hrms/images/banks/heritage-bank.svg",
		remote: "https://www.google.com/s2/favicons?sz=128&domain=www.heritageibt.com",
	},
	{
		name: "Belize Bank",
		logo: "/assets/hrms/images/banks/belize-bank.svg",
		remote: "https://upload.wikimedia.org/wikipedia/commons/d/dd/The_Belize_Bank_Limited.png",
	},
	{
		name: "Atlantic Bank",
		logo: "/assets/hrms/images/banks/atlantic-bank.svg",
		remote: "https://www.atlabank.com/images/logo.jpg",
	},
	{
		name: "National Bank of Belize",
		logo: "/assets/hrms/images/banks/national-bank-of-belize.svg",
		remote: "https://www.nbbl.bz/wp-content/uploads/2022/07/National-Bank-of-Belize-Logo.png",
	},
];

function belize_bank_choices(current) {
	const choices = BELIZE_BANKS.map((bank) => ({ ...bank }));
	if (current && !choices.some((bank) => bank.name === current)) {
		choices.unshift({ name: current, logo: "", remote: "" });
	}
	return choices;
}

function belize_bank_by_name(name) {
	return BELIZE_BANKS.find((bank) => bank.name === name) || null;
}

function bank_logo_html(bank, extra_class) {
	if (!bank?.name) return "";
	const cls = extra_class || "sp-bank-picker__logo";
	const local = frappe.utils.escape_html(bank.logo || "");
	const remote = frappe.utils.escape_html(bank.remote || "");
	const alt = frappe.utils.escape_html(bank.name);
	const src = remote || local;
	if (!src) return "";
	const fallback = local && remote ? ` onerror="this.onerror=null;this.src='${local}'"` : "";
	return `<img class="${cls}" src="${src}" alt="${alt}" referrerpolicy="no-referrer"${fallback}>`;
}

function setup_belize_bank_picker(frm) {
	frm.set_df_property("iban", "hidden", 1);
	frm.set_df_property("bank_name", "options", ["", ...BELIZE_BANKS.map((bank) => bank.name)].join("\n"));

	const field = frm.get_field("bank_name");
	if (!field?.$wrapper?.length) return;

	const $input_area = field.$wrapper.find(".control-input").first();
	const $disp = field.$wrapper.find(".control-value").first();
	if ($input_area.length) {
		render_bank_picker(frm, field, $input_area);
	}
	if ($disp.length) {
		render_bank_display($disp, frm.doc.bank_name);
	}
}

function render_bank_picker(frm, field, $input_area) {
	let $picker = $input_area.find(".sp-bank-picker");
	if (!$picker.length) {
		$picker = $(`
			<div class="sp-bank-picker">
				<button type="button" class="sp-bank-picker__toggle input-with-feedback form-control">
					<span class="sp-bank-picker__mark"></span>
					<span class="sp-bank-picker__label is-placeholder">${__("Select bank")}</span>
					<span class="sp-bank-picker__caret"></span>
				</button>
				<div class="sp-bank-picker__menu" role="listbox"></div>
			</div>
		`).appendTo($input_area);

		const $toggle = $picker.find(".sp-bank-picker__toggle");
		$toggle.on("click", (event) => {
			event.preventDefault();
			event.stopPropagation();
			if ($toggle.prop("disabled")) return;
			$picker.toggleClass("is-open");
		});

		$picker.on("click", (event) => {
			event.stopPropagation();
		});

		$picker.on("click", ".sp-bank-picker__option", (event) => {
			event.preventDefault();
			const name = $(event.currentTarget).attr("data-bank") || "";
			$picker.removeClass("is-open");
			frm.set_value("bank_name", name);
		});

		$(document).off("click.spBankPicker").on("click.spBankPicker", () => {
			$(".sp-bank-picker").removeClass("is-open");
		});
	}

	const current = frm.doc.bank_name || "";
	const $toggle = $picker.find(".sp-bank-picker__toggle");
	const $label = $picker.find(".sp-bank-picker__label");
	const $mark = $picker.find(".sp-bank-picker__mark");
	const selected = belize_bank_by_name(current) || (current ? { name: current, logo: "", remote: "" } : null);

	$toggle.prop("disabled", Boolean(field.df.read_only));
	$mark.html(selected ? bank_logo_html(selected) : "");
	$label.text(selected ? selected.name : __("Select bank"));
	$label.toggleClass("is-placeholder", !selected);

	const $menu = $picker.find(".sp-bank-picker__menu");
	$menu.empty();
	belize_bank_choices(current).forEach((bank) => {
		const selected_cls = bank.name === current ? " is-selected" : "";
		$menu.append(`
			<button type="button" class="sp-bank-picker__option${selected_cls}" data-bank="${frappe.utils.escape_html(
				bank.name,
			)}" role="option">
				${bank_logo_html(bank)}
				<span>${frappe.utils.escape_html(bank.name)}</span>
			</button>
		`);
	});
}

function render_bank_display($disp, bank_name) {
	if (!$disp.length) return;
	$disp.find(".sp-bank-value").remove();
	if (!bank_name) return;

	const bank = belize_bank_by_name(bank_name) || { name: bank_name, logo: "", remote: "" };
	const $value = $(`
		<span class="sp-bank-value">
			${bank_logo_html(bank, "sp-bank-value__logo")}
			<span>${frappe.utils.escape_html(bank.name)}</span>
		</span>
	`);
	$disp.append($value);
	$disp.contents().filter(function () {
		return this.nodeType === 3 && String(this.nodeValue || "").trim() === bank_name;
	}).remove();
}
