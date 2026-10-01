// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const assignable_masters = {};

function staff_pro_can(flag) {
	const can = window.hrms?.role_access?.can;
	if (typeof can === "function") return can(flag);
	const access = frappe.boot?.staff_pro_access;
	if (!access || !(flag in access)) return true;
	return !!access[flag];
}

function hide_employee_access_fields(frm) {
	const hidden = [];
	if (!staff_pro_can("see_agent_salary")) {
		hidden.push(
			"ctc",
			"salary_currency",
			"salary_cb",
			"user_bonus",
			"user_bonus_period_months",
			"user_bonus_attendance_target",
			"user_bonus_if_below",
			"user_bonus_attendance",
			"user_bonus_missed_days",
			"user_bonus_status",
		);
	}
	if (!staff_pro_can("see_bill_to_client")) {
		hidden.push("billing_section", "bill_to_customer", "billing_rate", "billing_currency");
	}
	if (!staff_pro_can("see_bank_details")) {
		hidden.push("salary_mode", "bank_name", "bank_ac_no");
	}
	if (!staff_pro_can("see_social_security")) {
		hidden.push("social_security_number");
	}
	hidden.forEach((fieldname) => {
		if (frm.fields_dict[fieldname]) frm.set_df_property(fieldname, "hidden", 1);
	});
	if (!staff_pro_can("see_agent_salary")) {
		frm.remove_custom_button(__("Change Hourly Rate"));
		frm.remove_custom_button(__("Salary Structure"), __("Create Assignments"));
		frm.remove_custom_button(__("Add Bonus"));
	}
	if (!staff_pro_can("see_td4_forms")) {
		frm.remove_custom_button(__("Request TD4"));
	}
}

function get_assignment_actions() {
	return [
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
			"expense_approver",
		]) {
			frm.set_df_property(fieldname, "hidden", 1);
		}
		set_default_hr_approvers(frm);
		frm.set_df_property("grade", "label", __("Campaign"));
		lock_employee_salary_currency(frm);
		setup_employee_username_field(frm);
		setup_belize_bank_picker(frm);

		// hide naming series field based on hr settings
		frappe.db.get_single_value("HR Settings", "emp_created_by").then((value) => {
			frm.toggle_display("naming_series", value === "Naming Series");
		});

		frm.trigger("add_assignment_actions");
		frm.trigger("add_hourly_rate_action");
		setup_employee_form_chrome(frm);
		setup_employee_documents_tab(frm);
		setup_employee_password_panel(frm);
		setup_employee_profile_stats(frm);
		apply_staff_pro_employee_field_restrictions(frm);
		setup_employee_delete_action(frm);
		set_employee_salary_defaults(frm);
		set_working_day_defaults(frm);
		setup_floor_worker_form(frm);
		refresh_user_bonus_status(frm);
		setup_td4_request(frm);
		hide_employee_access_fields(frm);
		setTimeout(() => hide_employee_access_fields(frm), 250);
	},

	is_floor_worker(frm) {
		apply_floor_worker_group_days(frm);
		setup_floor_worker_form(frm, true);
	},

	user_bonus: function (frm) {
		refresh_user_bonus_status(frm);
	},

	user_bonus_period_months: function (frm) {
		refresh_user_bonus_status(frm);
	},

	user_bonus_attendance_target: function (frm) {
		refresh_user_bonus_status(frm);
	},

	user_bonus_if_below: function (frm) {
		refresh_user_bonus_status(frm);
	},

	company: function (frm) {
		lock_employee_salary_currency(frm);
	},

	salary_currency: function (frm) {
		lock_employee_salary_currency(frm);
	},

	add_hourly_rate_action: function (frm) {
		if (!staff_pro_can("see_agent_salary")) return;
		if (frm.is_new() || !frappe.model.can_write("Employee")) return;
		frm.add_custom_button(__("Change Hourly Rate"), () => open_apply_hourly_rate_dialog(frm));
	},

	ctc: function (frm) {
		if (!staff_pro_can("see_agent_salary")) return;
		if (frm._skip_hourly_prompt || !flt(frm.doc.ctc)) return;
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
			if (action.doctype === "Salary Structure Assignment" && !staff_pro_can("see_agent_salary")) continue;

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

	user_id(frm) {
		if (frm._applying_username) return;
		toggle_username_save(frm);
	},
});

function setup_employee_username_field(frm) {
	frm.set_df_property("user_id", "label", __("Username"));
	frm.set_df_property("user_id", "fieldtype", "Data");
	frm.set_df_property("user_id", "options", "");
	frm.set_df_property("user_id", "description", "");
	const suggested = suggested_username(frm);
	if (suggested) {
		frm.set_df_property("user_id", "placeholder", suggested);
	}
	frm.refresh_field("user_id");
	mount_username_save(frm);
	show_login_username(frm);
}

function username_field(frm) {
	return frm.get_field("user_id");
}

function typed_username(frm) {
	const field = username_field(frm);
	return String(field?.$input?.val() || frm.doc.user_id || "").trim();
}

function mount_username_save(frm) {
	const field = username_field(frm);
	if (!field?.$wrapper) return;

	field.$wrapper.find(".help-box").remove();
	let $btn = field.$wrapper.find(".sp-username-save");
	if (!$btn.length) {
		$btn = $(
			`<button type="button" class="btn btn-sm sp-username-save">${frappe.utils.escape_html(
				__("Save"),
			)}</button>`,
		);
		const $host = field.$wrapper.find(".control-input-wrapper");
		($host.length ? $host : field.$wrapper).append($btn);
		$btn.on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			save_typed_username(frm);
		});
	}
	const $input = field.$input;
	if ($input?.length && !$input.data("sp-username-bound")) {
		$input.data("sp-username-bound", 1);
		$input.on("input.spUsername keyup.spUsername", () => toggle_username_save(frm));
	}
	toggle_username_save(frm);
}

function toggle_username_save(frm) {
	const field = username_field(frm);
	if (!field?.$wrapper) return;
	field.$wrapper.find(".help-box").remove();
	const typed = typed_username(frm);
	const dirty = Boolean(typed) && typed !== frm._displayed_username && !typed.includes("@");
	field.$wrapper.find(".sp-username-save").toggleClass("is-visible", dirty);
}

function show_login_username(frm) {
	if (frm.is_new()) {
		frm._linked_user = "";
		frm._displayed_username = "";
		toggle_username_save(frm);
		return;
	}

	frappe.call({
		method: "hrms.overrides.employee_master.get_employee_login_username",
		args: { employee: frm.doc.name },
	}).then((r) => {
		const user = r.message?.user || "";
		const username = r.message?.username || "";
		frm._linked_user = user;
		frm._displayed_username = username;
		const field = username_field(frm);
		frm._applying_username = true;
		if (field?.$input) {
			field.$input.val(username);
		}
		if (field && username) {
			field.value = username;
		}
		frm._applying_username = false;
		toggle_username_save(frm);
		setup_employee_password_panel(frm);
	});
}

function save_typed_username(frm) {
	const username = typed_username(frm);
	if (!username || frm.is_new() || !frappe.model.can_write("Employee")) return;
	if (username.includes("@")) {
		frappe.msgprint(__("Use a username, not an email address."));
		return;
	}

	frappe.call({
		method: "hrms.overrides.employee_master.set_employee_username",
		args: { employee: frm.doc.name, username },
		freeze: true,
		freeze_message: __("Saving username..."),
	}).then((r) => {
		frm._linked_user = r.message?.user || frm._linked_user;
		frm._displayed_username = r.message?.username || username;
		frm._applying_username = true;
		if (frm._linked_user) {
			frm.doc.user_id = frm._linked_user;
		}
		const field = username_field(frm);
		if (field?.$input) {
			field.$input.val(frm._displayed_username);
		}
		frm._applying_username = false;
		toggle_username_save(frm);
		setup_employee_password_panel(frm);
		frappe.show_alert({
			message: __("Username set to {0}", [frm._displayed_username]),
			indicator: "green",
		});
	});
}

function suggested_username(frm) {
	const first = String(frm.doc.first_name || "").replace(/[^A-Za-z0-9]/g, "");
	const last = String(frm.doc.last_name || "").replace(/[^A-Za-z0-9]/g, "");
	if (first && last) return `${first.charAt(0)}${last}`;
	return first || last || "";
}

function lock_employee_salary_currency(frm) {
	if (!frm.fields_dict.salary_currency) return;
	frm.set_df_property("salary_currency", "read_only", 1);
	frm.set_df_property(
		"salary_currency",
		"description",
		__("Agent salary is always Belize dollars (BZD)."),
	);
	if (frm.doc.salary_currency === "BZD") return;
	frm.set_value("salary_currency", "BZD");
}

const WORK_WEEKDAYS = ["work_monday", "work_tuesday", "work_wednesday", "work_thursday", "work_friday"];
const WORK_WEEKEND = ["work_saturday", "work_sunday"];
const EMPLOYEE_ROSTER_KEY = "staff_pro_employee_roster";

function floor_worker_badge_html() {
	return `<span class="sp-floor-worker-badge" style="display:inline-block;margin-left:6px;padding:0 6px;border-radius:999px;background:#e7f6ec;color:#146c43;font-size:11px;font-weight:600;line-height:18px;vertical-align:middle;">floorworkers</span>`;
}

function set_default_hr_approvers(frm) {
	if (frm.doc.leave_approver && frm.doc.shift_request_approver) return;
	if (frm._sp_hr_approver_pending) return;
	frm._sp_hr_approver_pending = true;
	frappe.call({
		method: "hrms.overrides.employee_master.get_default_hr_approver",
		callback(r) {
			frm._sp_hr_approver_pending = false;
			const approver = r.message;
			if (!approver) return;
			if (!frm.doc.leave_approver && frm.fields_dict.leave_approver) {
				frm.set_value("leave_approver", approver);
			}
			if (!frm.doc.shift_request_approver && frm.fields_dict.shift_request_approver) {
				frm.set_value("shift_request_approver", approver);
			}
		},
	});
}

function set_working_day_defaults(frm) {
	if (!frm.is_new() || frm._sp_working_days_ready) return;
	frm._sp_working_days_ready = true;
	const fields = [...WORK_WEEKDAYS, ...WORK_WEEKEND].filter((fieldname) => frm.fields_dict[fieldname]);
	if (!fields.length) return;
	const any_checked = fields.some((fieldname) => cint(frm.doc[fieldname]));
	if (any_checked) return;
	WORK_WEEKDAYS.forEach((fieldname) => {
		if (frm.fields_dict[fieldname]) frm.set_value(fieldname, 1);
	});
}

function working_days_are_default(frm) {
	return WORK_WEEKDAYS.every((fieldname) => !frm.fields_dict[fieldname] || cint(frm.doc[fieldname]))
		&& WORK_WEEKEND.every((fieldname) => !frm.fields_dict[fieldname] || !cint(frm.doc[fieldname]));
}

function apply_floor_worker_group_days(frm) {
	if (!cint(frm.doc.is_floor_worker) || !working_days_are_default(frm)) return;
	frappe.xcall("hrms.hr.floor_workers.get_floor_worker_group_defaults").then((defaults) => {
		const days = defaults?.working_days || {};
		Object.entries(days).forEach(([fieldname, value]) => {
			if (frm.fields_dict[fieldname] && cint(frm.doc[fieldname]) !== cint(value)) {
				frm.set_value(fieldname, cint(value));
			}
		});
	});
}

function setup_floor_worker_form(frm, clear_shift) {
	const is_floor = cint(frm.doc.is_floor_worker);
	if (frm.is_new() && !frm._sp_floor_worker_default) {
		frm._sp_floor_worker_default = true;
		try {
			if (!is_floor && sessionStorage.getItem(EMPLOYEE_ROSTER_KEY) === "floor") {
				frm.set_value("is_floor_worker", 1);
				return;
			}
		} catch (err) {
			/* ignore */
		}
	}

	["billing_section", "bill_to_customer", "billing_rate", "default_shift"].forEach((fieldname) => {
		if (frm.fields_dict[fieldname]) {
			frm.toggle_display(fieldname, !cint(frm.doc.is_floor_worker));
		}
	});
	if (clear_shift && cint(frm.doc.is_floor_worker) && frm.doc.default_shift) {
		frm.set_value("default_shift", "");
	}

	const $page = frm.page?.wrapper || frm.$wrapper;
	$page?.find(".sp-floor-worker-badge").remove();
	if (!cint(frm.doc.is_floor_worker) || !$page?.length) return;
	const $title = $page.find(".page-title .title-text").first();
	if ($title.length) {
		$title.append(floor_worker_badge_html());
	}
}

function set_employee_salary_defaults(frm) {
	lock_employee_salary_currency(frm);
	if (!frm.is_new()) return;
	if (!frm.doc.salary_mode) {
		frm.set_value("salary_mode", "Bank");
	}
	if (!cint(frm.doc.user_bonus_period_months)) {
		frm.set_value("user_bonus_period_months", 3);
	}
	if (!flt(frm.doc.user_bonus_attendance_target)) {
		frm.set_value("user_bonus_attendance_target", 90);
	}
	if (!frm.doc.user_bonus_if_below) {
		frm.set_value("user_bonus_if_below", "No Bonus");
	}
}

function refresh_user_bonus_status(frm) {
	if (!staff_pro_can("see_agent_salary")) return;
	if (frm.is_new() || !frm.doc.name || !frm.fields_dict.user_bonus) return;
	frappe.call({
		method: "hrms.payroll.user_bonus.get_user_bonus",
		args: {
			employee: frm.doc.name,
			user_bonus: frm.doc.user_bonus,
			period_months: frm.doc.user_bonus_period_months,
			attendance_target: frm.doc.user_bonus_attendance_target,
			if_below: frm.doc.user_bonus_if_below,
		},
		callback: function (r) {
			if (!r.message) return;
			const result = r.message;
			frm.doc.user_bonus_attendance = result.attendance_pct;
			frm.doc.user_bonus_missed_days = result.missed_days;
			frm.doc.user_bonus_status = result.status;
			["user_bonus_attendance", "user_bonus_missed_days", "user_bonus_status"].forEach((field) => {
				frm.refresh_field(field);
			});
			if (result.bonus_type && frappe.model.can_create("Additional Salary")) {
				frm.add_custom_button(__("Add Bonus"), () => {
					frappe.new_doc("Additional Salary", {
						employee: frm.doc.name,
						bonus_type: result.bonus_type,
						amount: result.amount,
						payroll_date: frappe.datetime.get_today(),
					});
				});
			}
		},
	});
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

function sync_employee_hourly_rate(frm, rate) {
	if (frm.is_dirty()) {
		frm._skip_hourly_prompt = true;
		frm.set_value("ctc", rate).then(() => {
			frm._skip_hourly_prompt = false;
		});
		return;
	}
	frm.reload_doc();
}

function apply_hourly_rate_from_dialog(frm, dialog, rate, args) {
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
		sync_employee_hourly_rate(frm, rate);
	});
}

function open_apply_hourly_rate_dialog(frm) {
	const current_rate = flt(frm.doc.ctc);
	const currency = frm.doc.salary_currency || "BZD";
	const dialog = new frappe.ui.Dialog({
		title: __("Change Hourly Rate"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "currency",
				options: "Currency",
				hidden: 1,
				default: currency,
			},
			{
				fieldtype: "Currency",
				fieldname: "hourly_rate",
				label: __("Agent Hourly"),
				options: "currency",
				reqd: 1,
				default: current_rate || "",
				description: __(
					"Hourly pay for this agent. Optionally apply the same rate to other agents, a branch, campaign, or team.",
				),
			},
			{
				fieldtype: "Section Break",
				label: __("Also apply to"),
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
		primary_action_label: __("Save"),
		primary_action: () => {
			const rate = flt(dialog.get_value("hourly_rate"));
			if (rate <= 0) {
				frappe.msgprint(__("Enter an Agent Hourly greater than zero."));
				return;
			}

			const args = hourly_rate_dialog_values(dialog);
			const has_others =
				args.employees.length || args.branches.length || args.campaigns.length || args.teams.length;
			if (!has_others) {
				apply_hourly_rate_from_dialog(frm, dialog, rate, args);
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
					__("Update Agent Hourly to {0}/hr for this agent and {1} other agent(s)?", [
						format_currency(rate, currency),
						count,
					]),
					() => apply_hourly_rate_from_dialog(frm, dialog, rate, args),
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

function setup_employee_delete_action(frm) {
	if (frm.is_new() || !frappe.model.can_delete("Employee")) return;

	frm.page.add_inner_button(
		__("Delete Agent"),
		() => {
			const label = frm.doc.employee_name || frm.doc.name;
			frappe.confirm(
				__(
					"Delete {0} and remove all linked attendance, payroll, leave, and related records? This cannot be undone.",
					[label],
				),
				() => {
					frappe.call({
						method: "hrms.hr.employee_cleanup.delete_employee_with_unlink",
						args: { employee: frm.doc.name },
						freeze: true,
						freeze_message: __("Removing linked records..."),
						callback(r) {
							if (r.exc) return;
							frappe.show_alert({
								message: __("Agent deleted"),
								indicator: "green",
							});
							frappe.set_route("List", "Employee");
						},
					});
				},
			);
		},
		__("Actions"),
	);
}

function place_documents_tab_before_profile(frm) {
	const $nav = $(frm.page?.wrapper || frm.$wrapper).find("#form-tabs");
	if (!$nav.length) return;

	const tab_label = (el) => ($(el).text() || "").replace(/\s+/g, " ").trim();
	const $items = $nav.find("li.nav-item, .nav-item");
	const $profile = $items.filter((_, el) => tab_label(el) === __("Profile") || tab_label(el) === "Profile").first();
	const $docs = $items
		.filter((_, el) => tab_label(el) === __("Documents") || tab_label(el) === "Documents")
		.first();
	if ($profile.length && $docs.length && !$docs.next().is($profile)) {
		$docs.insertBefore($profile);
	}
}

function open_document_viewer(filename, url) {
	if (!url) return;
	const name = filename || __("Document");
	const is_image = /\.(gif|jpg|jpeg|png|svg|webp)$/i.test(name);
	const dialog = new frappe.ui.Dialog({
		title: name,
		size: "extra-large",
	});
	const safe_url = frappe.utils.escape_html(url);
	dialog.$body.html(
		is_image
			? `<img src="${safe_url}" style="max-width:100%;height:auto" alt="">`
			: `<iframe src="${safe_url}" title="${frappe.utils.escape_html(name)}" style="width:100%;height:70vh;border:0"></iframe>`,
	);
	dialog.show();
}

function setup_employee_documents_tab(frm) {
	place_documents_tab_before_profile(frm);
	const field = frm.get_field("agent_documents_html");
	if (!field?.$wrapper?.length) return;

	field.$wrapper.addClass("sp-emp-docs-field");
	frm.set_df_property("agent_documents_html", "label", "");

	if (frm.is_new()) {
		field.$wrapper.html(
			`<div class="sp-emp-docs"><p class="sp-emp-docs__empty">${frappe.utils.escape_html(
				__("Save this agent to attach documents."),
			)}</p></div>`,
		);
		return;
	}

	const state = (frm._agent_docs = frm._agent_docs || {
		employee: frm.doc.name,
		categories: [],
		files: {},
		open: "",
		loading: false,
	});
	state.employee = frm.doc.name;

	const escape = (value) => frappe.utils.escape_html(value == null ? "" : String(value));
	const file_count = (count) => {
		const total = cint(count);
		return total === 1 ? __("{0} file", [total]) : __("{0} files", [total]);
	};

	const $host = field.$wrapper;
	$host.off(".spEmpDocs");

	const render = () => {
		if (state.loading && !state.categories.length) {
			$host.html(
				`<div class="sp-emp-docs"><p class="sp-emp-docs__empty">${escape(__("Loading..."))}</p></div>`,
			);
			return;
		}
		const cards = (state.categories || [])
			.map((category) => {
				const open = state.open === category.name;
				const files = state.files[category.name] || [];
				const file_rows = files.length
					? `<ul class="sp-emp-docs__files">${files
							.map((file) => {
								const when = file.uploaded_on ? frappe.datetime.str_to_user(file.uploaded_on) : "";
								const view = file.file_url
									? `<button type="button" class="sp-emp-docs__link" data-view="${escape(file.file_url)}" data-file-name="${escape(file.file_name || file.name)}">${escape(__("View"))}</button>`
									: "";
								const download = file.file_url
									? `<a class="sp-emp-docs__link" href="${escape(file.file_url)}" target="_blank" rel="noopener">${escape(__("Download"))}</a>`
									: "";
								const remove = file.can_delete
									? `<button type="button" class="sp-emp-docs__link is-danger" data-delete="${escape(file.name)}" data-file-name="${escape(file.file_name)}">${escape(__("Delete"))}</button>`
									: "";
								return `<li class="sp-emp-docs__file">
									<div>
										<div class="sp-emp-docs__file-name">${escape(file.file_name || file.name)}</div>
										<div class="sp-emp-docs__file-meta">${escape(when)}${file.uploaded_by_name ? ` · ${escape(file.uploaded_by_name)}` : ""}</div>
									</div>
									<div class="sp-emp-docs__actions">${view}${download}${remove}</div>
								</li>`;
							})
							.join("")}</ul>`
					: `<p class="sp-emp-docs__empty">${escape(__("No files in this folder yet."))}</p>`;
				return `<section class="sp-emp-docs__folder${open ? " is-open" : ""}">
					<button type="button" class="sp-emp-docs__folder-head" data-category="${escape(category.name)}">
						<span class="sp-emp-docs__folder-name">${escape(category.category_name || category.name)}</span>
						<span class="sp-emp-docs__folder-count">${escape(file_count(category.file_count))}</span>
					</button>
					${
						open
							? `<div class="sp-emp-docs__folder-body">
								<div class="sp-emp-docs__upload">
									<button type="button" class="btn btn-primary btn-sm" data-upload="${escape(category.name)}">${escape(__("Upload"))}</button>
									<input type="file" multiple hidden data-file-input="${escape(category.name)}" />
								</div>
								${file_rows}
							</div>`
							: ""
					}
				</section>`;
			})
			.join("");

		$host.html(`
			<div class="sp-emp-docs">
				<p class="sp-emp-docs__help">${escape(__("Social security, job letters, bank declarations, IDs, writeups, and other files for this agent."))}</p>
				${cards || `<p class="sp-emp-docs__empty">${escape(__("No document categories yet."))}</p>`}
			</div>
		`);
	};

	const load_files = (category, then_render = true) =>
		frappe
			.call({
				method: "hrms.hr.agent_filesystem.list_files",
				args: { employee: state.employee, category },
			})
			.then((response) => {
				state.files[category] = response.message || [];
				if (then_render) render();
			});

	const load = () => {
		state.loading = true;
		render();
		frappe
			.call({
				method: "hrms.hr.agent_filesystem.list_categories",
				args: { employee: state.employee },
			})
			.then((response) => {
				state.categories = response.message || [];
				state.loading = false;
				const open = state.open;
				const after = open ? load_files(open, false) : Promise.resolve();
				return after.then(render);
			})
			.catch(() => {
				state.loading = false;
				$host.html(
					`<div class="sp-emp-docs"><p class="sp-emp-docs__empty">${escape(__("Documents could not be loaded."))}</p></div>`,
				);
			});
	};

	const upload_files = (category, file_list) => {
		const files = Array.from(file_list || []);
		if (!files.length) return;
		let pending = files.length;
		files.forEach((file) => {
			const reader = new FileReader();
			reader.onload = () => {
				const done = () => {
					pending -= 1;
					if (!pending) load();
				};
				frappe
					.call({
						method: "hrms.hr.agent_filesystem.upload_file",
						args: {
							employee: state.employee,
							category,
							filename: file.name,
							content: String(reader.result || "").split(",")[1] || "",
						},
					})
					.then(done, done);
			};
			reader.readAsDataURL(file);
		});
	};

	$host.on("click.spEmpDocs", "[data-view]", function (event) {
		event.preventDefault();
		event.stopPropagation();
		open_document_viewer($(this).attr("data-file-name"), $(this).attr("data-view"));
	});

	$host.on("click.spEmpDocs", "[data-category]", function () {
		const category = $(this).attr("data-category");
		state.open = state.open === category ? "" : category;
		if (state.open) {
			load_files(state.open);
		} else {
			render();
		}
	});

	$host.on("click.spEmpDocs", "[data-upload]", function () {
		$host.find(`[data-file-input="${$(this).attr("data-upload")}"]`).trigger("click");
	});

	$host.on("change.spEmpDocs", "[data-file-input]", function () {
		const category = $(this).attr("data-file-input");
		upload_files(category, this.files);
		this.value = "";
	});

	$host.on("click.spEmpDocs", "[data-delete]", function () {
		const name = $(this).attr("data-delete");
		const label = $(this).attr("data-file-name") || name;
		frappe.confirm(__("Delete {0}?", [label]), () => {
			frappe.call({
				method: "hrms.hr.agent_filesystem.delete_file",
				args: { name },
				callback: () => load(),
			});
		});
	});

	load();
}

function setup_employee_form_chrome(frm) {
	const $page = frm.page?.wrapper || frm.$wrapper;
	if (!$page?.length) {
		return;
	}

	$page.addClass("sp-employee-form");
	$page.find(".menu-btn-group, .menu-more-button").addClass("hide").hide();
	$page.find(".form-sidebar .form-attachments, .form-sidebar .form-tags, .form-sidebar .form-shared").hide();
	$page.find(".form-sidebar .modified-by, .form-sidebar .created-by").each(function () {
		$(this).closest(".sidebar-section").hide();
	});
}

function password_panel_host(frm) {
	const $page = frm.page?.wrapper || frm.$wrapper;
	if (!$page?.length) return $();

	let $host = $page.find('.form-column[data-fieldname="column_break_xwnm"]').first();
	if ($host.length) return $host;

	const field = frm.get_field("column_break_xwnm");
	if (field?.$wrapper?.length) {
		const $column = field.$wrapper.closest(".form-column");
		if ($column.length) return $column;
		return field.$wrapper;
	}

	const section = frm.fields_dict?.erpnext_user?.section
		|| frm.layout?.sections?.find?.((s) => s.df?.fieldname === "erpnext_user");
	const $section = section?.$wrapper || $page.find('[data-fieldname="erpnext_user"]').closest(".form-section");
	if ($section?.length) {
		$host = $section.find(".form-column").eq(1);
		if ($host.length) return $host;
	}

	return $();
}

function expand_user_details_section(frm) {
	const section = frm.fields_dict?.erpnext_user?.section
		|| frm.layout?.sections?.find?.((s) => s.df?.fieldname === "erpnext_user");
	if (section?.collapse && section.collapsed) {
		section.collapse(false);
	}
	const $page = frm.page?.wrapper || frm.$wrapper;
	const $section = $page?.find('[data-fieldname="erpnext_user"]').closest(".form-section");
	if ($section?.hasClass("hide") || $section?.find(".section-body").is(":hidden")) {
		$section.find(".section-head").trigger("click");
	}
}

function setup_employee_password_panel(frm) {
	const $page = frm.page?.wrapper || frm.$wrapper;
	if (!$page?.length) return;

	if (frm.is_new()) {
		$page.find(".sp-emp-password").remove();
		return;
	}

	expand_user_details_section(frm);

	const mount = () => {
		const $host = password_panel_host(frm);
		if (!$host.length) return false;

		$page.find(".sp-emp-password").not($host.find(".sp-emp-password")).remove();

		let $panel = $host.children(".sp-emp-password");
		const canViewPassword = (frappe.user_roles || []).some((role) =>
			["System Manager", "HR Manager", "HR User", "Administrator"].includes(role),
		);
		if (!$panel.length) {
			const currentPassword = canViewPassword
				? `<label class="sp-emp-password__label">
						<span>${frappe.utils.escape_html(__("Current password"))}</span>
						<div class="sp-emp-password__reveal" style="display:flex;gap:8px;align-items:center">
							<input type="password" class="form-control sp-emp-password__current" readonly autocomplete="off" placeholder="${frappe.utils.escape_html(__("Hidden"))}" />
							<button type="button" class="btn btn-default btn-sm sp-emp-password__toggle">${frappe.utils.escape_html(__("Show"))}</button>
						</div>
						<div class="sp-emp-password__current-note text-muted"></div>
					</label>`
				: "";
			$panel = $(`
				<div class="sp-emp-password">
					<div class="sp-emp-password__title">${frappe.utils.escape_html(__("HRMS Password"))}</div>
					<p class="sp-emp-password__help">${frappe.utils.escape_html(
						__("Set or change this agent's login password for Staff Pro."),
					)}</p>
					${currentPassword}
					<label class="sp-emp-password__label">
						<span>${frappe.utils.escape_html(__("New password"))}</span>
						<input type="password" class="form-control sp-emp-password__input" autocomplete="new-password" />
					</label>
					<label class="sp-emp-password__label">
						<span>${frappe.utils.escape_html(__("Confirm password"))}</span>
						<input type="password" class="form-control sp-emp-password__confirm" autocomplete="new-password" />
					</label>
					<label class="sp-emp-password__check">
						<input type="checkbox" class="sp-emp-password__logout" />
						<span>${frappe.utils.escape_html(__("Log out of all sessions"))}</span>
					</label>
					<button type="button" class="btn btn-primary btn-sm sp-emp-password__save">${frappe.utils.escape_html(
						__("Update Password"),
					)}</button>
					<div class="sp-emp-password__user text-muted"></div>
				</div>
			`).appendTo($host);

			$panel.on("click", ".sp-emp-password__toggle", () => {
				const $input = $panel.find(".sp-emp-password__current");
				const $note = $panel.find(".sp-emp-password__current-note");
				const $button = $panel.find(".sp-emp-password__toggle");
				if ($input.attr("type") === "text") {
					$input.attr("type", "password").val("");
					$note.text("");
					$button.text(__("Show"));
					return;
				}
				frappe.call({
					method: "hrms.overrides.employee_profile.get_employee_user_password",
					args: { employee: frm.doc.name },
					freeze: true,
					freeze_message: __("Loading password..."),
				}).then((r) => {
					const password = r.message?.password || "";
					if (!password) {
						$input.attr("type", "password").val("");
						$note.text(__("No saved password yet. It is stored when you set one here, or the next time this agent signs in."));
						return;
					}
					$input.attr("type", "text").val(password);
					$note.text("");
					$button.text(__("Hide"));
				});
			});

			$panel.on("click", ".sp-emp-password__save", () => {
				const password = String($panel.find(".sp-emp-password__input").val() || "");
				const confirm = String($panel.find(".sp-emp-password__confirm").val() || "");
				if (!(frm._linked_user || frm.doc.user_id)) {
					frappe.msgprint(__("Link a Username first, or create a username for this employee."));
					return;
				}
				if (password.length < 8) {
					frappe.msgprint(__("Password must be at least 8 characters."));
					return;
				}
				if (password !== confirm) {
					frappe.msgprint(__("Passwords do not match."));
					return;
				}
				frappe.call({
					method: "hrms.overrides.employee_profile.update_employee_user_password",
					args: {
						employee: frm.doc.name,
						new_password: password,
						logout_all_sessions: $panel.find(".sp-emp-password__logout").is(":checked") ? 1 : 0,
					},
					freeze: true,
					freeze_message: __("Updating password..."),
				}).then(() => {
					$panel.find(".sp-emp-password__input, .sp-emp-password__confirm").val("");
					$panel.find(".sp-emp-password__logout").prop("checked", false);
					$panel.find(".sp-emp-password__current").attr("type", "password").val("");
					$panel.find(".sp-emp-password__current-note").text("");
					$panel.find(".sp-emp-password__toggle").text(__("Show"));
					frappe.show_alert({
						message: __("Password updated for {0}", [frm._displayed_username || frm.doc.user_id]),
						indicator: "green",
					});
				});
			});
		}

		const linked = frm._linked_user || (String(frm.doc.user_id || "").includes("@") ? frm.doc.user_id : "");
		const username = frm._displayed_username || "";
		$panel
			.find(".sp-emp-password__user")
			.text(username ? __("Username: {0}", [username]) : __("No username linked yet."));
		$panel.find(".sp-emp-password__save").prop("disabled", !linked);
		return true;
	};

	if (mount()) return;

	let tries = 0;
	const timer = setInterval(() => {
		tries += 1;
		expand_user_details_section(frm);
		if (mount() || tries > 20) {
			clearInterval(timer);
		}
	}, 150);

	$page.off("click.spEmpPassword").on("click.spEmpPassword", ".section-head", () => {
		setTimeout(mount, 50);
	});
}

function staff_pro_profile_visibility() {
	return frappe.boot?.staff_pro_profile_stats || {};
}

function apply_staff_pro_employee_field_restrictions(frm) {
	const vis = staff_pro_profile_visibility();
	const hideBilling =
		vis.total_billed === false && vis.agent_profit === false && !frappe.user.has_role("Administrator");
	for (const fieldname of [
		"billing_section",
		"bill_to_customer",
		"billing_currency",
		"billing_rate",
	]) {
		if (frm.fields_dict[fieldname]) {
			frm.toggle_display(fieldname, !hideBilling);
		}
	}
	if (vis.payroll_totals === false && !frappe.user.has_role("Administrator")) {
		for (const fieldname of ["user_bonus", "user_bonus_period_months", "user_bonus_attendance_target", "user_bonus_if_below", "user_bonus_attendance", "user_bonus_missed_days", "user_bonus_status"]) {
			if (frm.fields_dict[fieldname]) {
				frm.toggle_display(fieldname, false);
			}
		}
	}
}

function setup_employee_profile_stats(frm) {
	const $sidebar = (frm.page?.wrapper || frm.$wrapper)?.find(".form-sidebar");
	if (!$sidebar?.length || frm.is_new()) {
		$sidebar?.find(".sp-emp-stats").remove();
		return;
	}

	let $stats = $sidebar.find(".sp-emp-stats");
	if (!$stats.length) {
		$stats = $(`
			<div class="sidebar-section sp-emp-stats">
				<div class="sp-emp-stats__title">${frappe.utils.escape_html(__("Totals"))}</div>
				<div class="sp-emp-stats__list is-loading">
					<div class="sp-emp-stats__empty">${frappe.utils.escape_html(__("Loading..."))}</div>
				</div>
			</div>
		`);
		const $assign = $sidebar.find(".form-assignments").closest(".sidebar-section");
		if ($assign.length) {
			$stats.insertAfter($assign);
		} else {
			$sidebar.prepend($stats);
		}
	}

	const request_id = `${frm.doc.name}:${Date.now()}`;
	$stats.data("request-id", request_id);
	$stats.find(".sp-emp-stats__list").addClass("is-loading").html(
		`<div class="sp-emp-stats__empty">${frappe.utils.escape_html(__("Loading..."))}</div>`,
	);

	frappe.call({
		method: "hrms.overrides.employee_profile.get_employee_profile_stats",
		args: { employee: frm.doc.name },
	}).then((r) => {
		if ($stats.data("request-id") !== request_id) return;
		const stats = r.message || {};
		const visibility = stats.visibility || staff_pro_profile_visibility();
		const company_currency = stats.company_currency || "BZD";
		const billing_currency = stats.billing_currency || "USD";
		const money = (value, currency) => {
			if (value == null || value === "") return "—";
			if (typeof format_currency === "function") {
				return format_currency(value, currency);
			}
			return `${Number(value).toLocaleString(undefined, {
				minimumFractionDigits: 2,
				maximumFractionDigits: 2,
			})} ${currency}`;
		};
		const hours = Number(stats.total_hours || 0);
		const leave_remaining = Number(stats.leave_remaining || 0);
		const sees_billing = staff_pro_can("see_bill_to_client") || staff_pro_can("see_client_invoices");
		const rows = [
			{
				label: __("Total SS contributions"),
				value: money(stats.total_ss, company_currency),
				show: visibility.payroll_totals !== false && staff_pro_can("see_social_security"),
			},
			{
				label: __("Total income"),
				value: money(stats.total_income, company_currency),
				show: visibility.payroll_totals !== false && staff_pro_can("see_agent_salary"),
			},
			{
				label: __("Total Billed to Client"),
				value: money(stats.total_billed, billing_currency),
				show: visibility.total_billed !== false && sees_billing,
			},
			{
				label: __("Agent Profit"),
				value: money(stats.agent_profit, company_currency),
				show: visibility.agent_profit !== false && staff_pro_can("see_agent_salary") && sees_billing,
			},
			{
				label: __("Tax total"),
				value: money(stats.total_tax, company_currency),
				show: visibility.payroll_totals !== false && staff_pro_can("see_social_security"),
			},
			{
				label: __("Total hours worked"),
				value: hours ? `${hours.toLocaleString(undefined, { maximumFractionDigits: 1 })}h` : "—",
				show: visibility.total_hours !== false,
			},
			{
				label: __("Leave remaining"),
				value: `${leave_remaining.toLocaleString(undefined, { maximumFractionDigits: 1 })} days`,
				show: visibility.leave_remaining !== false,
			},
			{
				label: __("Leave Money Value remaining"),
				value: money(stats.leave_money_remaining, company_currency),
				show: visibility.payroll_totals !== false && staff_pro_can("see_agent_salary"),
			},
		].filter((row) => row.show);
		if (!rows.length) {
			$stats.find(".sp-emp-stats__list").removeClass("is-loading").html(
				`<div class="sp-emp-stats__empty">${frappe.utils.escape_html(__("No totals available for your access level."))}</div>`,
			);
			return;
		}
		$stats.find(".sp-emp-stats__list").removeClass("is-loading").html(
			rows
				.map(
					(row) => `
				<div class="sp-emp-stats__row">
					<span class="sp-emp-stats__label">${frappe.utils.escape_html(row.label)}</span>
					<span class="sp-emp-stats__value">${frappe.utils.escape_html(row.value)}</span>
				</div>`,
				)
				.join(""),
		);
	}).catch(() => {
		if ($stats.data("request-id") !== request_id) return;
		$stats
			.find(".sp-emp-stats__list")
			.removeClass("is-loading")
			.html(`<div class="sp-emp-stats__empty">${frappe.utils.escape_html(__("Could not load totals."))}</div>`);
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

function setup_td4_request(frm) {
	if (!staff_pro_can("see_td4_forms")) return;
	if (frm.is_new() || !frappe.model.can_create("TD4 Form")) return;
	frm.add_custom_button(__("Request TD4"), () => {
		frappe.call({
			method: "hrms.hr.doctype.td4_form.td4_form.request_td4",
			args: { employee: frm.doc.name },
			freeze: true,
			freeze_message: __("Sending TD4 request..."),
			callback(response) {
				const message = response.message || {};
				if (!message.name) return;
				frappe.show_alert({
					message: message.created
						? __("TD4 request sent")
						: __("This agent already has an open TD4 request"),
					indicator: message.created ? "green" : "blue",
				});
				frappe.set_route("Form", "TD4 Form", message.name);
			},
		});
	});
}
