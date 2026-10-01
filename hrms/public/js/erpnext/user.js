// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

const DEFAULT_BPO_SIDEBARS = [
	{ value: "people", label: "People" },
	{ value: "time", label: "Time" },
	{ value: "pay", label: "Pay" },
	{ value: "talent", label: "Talent" },
	{ value: "floor", label: "Floor" },
	{ value: "ss and taxes", label: "SS and Taxes" },
	{ value: "finance", label: "Finance" },
	{ value: "admin", label: "Admin" },
];

function bpo_role_allowlist() {
	return new Set(frappe.boot?.staff_pro_bpo_roles || []);
}

function bpo_sidebar_modules() {
	const from_boot = frappe.boot?.staff_pro_bpo_modules;
	if (Array.isArray(from_boot) && from_boot.length && typeof from_boot[0] === "object") {
		return from_boot;
	}
	return DEFAULT_BPO_SIDEBARS;
}

function hide_module_profile(frm) {
	if (frm.fields_dict.module_profile) {
		frm.set_df_property("module_profile", "hidden", 1);
	}
}

const ROLE_ORDER = [
	"HR Manager",
	"HR User",
	"HR Assistant",
	"Leave Approver",
	"Payroll Manager",
	"Payroll User",
	"Accounts Manager",
	"Accounts User",
	"Interviewer",
	"Employee",
	"Employee Self Service",
	"Expense Approver",
	"Workspace Manager",
	"System Manager",
];

const ROLE_DESCRIPTIONS = {
	"HR Manager": "Runs people, hiring, time, and HR setup.",
	"HR User": "Day-to-day work on agents, attendance, and requests.",
	"HR Assistant": "Helps with agents, attendance, and day-to-day HR work.",
	"Leave Approver": "Approves time off and schedule changes.",
	"Payroll Manager": "Runs payroll and can see agent pay.",
	"Payroll User": "Views pay stubs and payroll records.",
	"Accounts Manager": "Clients, invoices, and payments.",
	"Accounts User": "Creates and updates client invoices.",
	Interviewer: "Interviews and candidate feedback.",
	Employee: "Ties this login to an agent record.",
	"Employee Self Service": "Clock in, request time off, and open pay stubs in the agent portal.",
	"Expense Approver": "Approves expense claims.",
	"Workspace Manager": "Can change how desk pages are laid out.",
	"System Manager": "Users, settings, and the rest of the app.",
};

const MODULE_DESCRIPTIONS = {
	people: "Agents, time off, onboarding, and requests.",
	time: "Attendance, schedules, overtime, and who is in.",
	pay: "Payroll, pay stubs, bonuses, and hourly rates.",
	talent: "Hiring, reviews, and workforce planning.",
	filesystem: "Agent documents and uploaded files.",
	floor: "The office map, cubicles, and floors.",
	"ss and taxes": "Social security, contributions, and tax filings.",
	finance: "Clients, invoices, and outstanding balances.",
	admin: "Users, settings, and the audit trail.",
};

function hide_section_head(fieldname) {
	$(`.form-section[data-fieldname="${fieldname}"]`)
		.children(".section-head, .section-head-container")
		.hide();
}

function attached_role_names(frm) {
	const allowlist = bpo_role_allowlist();
	const seen = new Set();
	(frm.doc.roles || []).forEach((row) => {
		const role = (row.role || "").toString();
		if (!role || seen.has(role)) return;
		if (allowlist.size && !allowlist.has(role)) return;
		seen.add(role);
	});
	const ordered = ROLE_ORDER.filter((role) => seen.has(role));
	seen.forEach((role) => {
		if (!ordered.includes(role)) ordered.push(role);
	});
	return ordered;
}

function attached_role_rows(frm) {
	return attached_role_names(frm).map((role) => ({
		id: role,
		label: role,
		description: ROLE_DESCRIPTIONS[role] || "",
		href: `/desk/role/${encodeURIComponent(role)}`,
		readonly: true,
	}));
}

function mount_role_switches(frm) {
	const $wrapper = frm.fields_dict.roles_html?.$wrapper;
	if (!$wrapper?.length || !window.hrms?.role_access?.render_section) return;
	const rows = attached_role_rows(frm);

	$wrapper.children().not(".staff-pro-access-host").hide();
	hide_section_head("sb1");
	if (frm.fields_dict.role_profiles) {
		frm.set_df_property("role_profiles", "hidden", 1);
	}

	const signature = rows.map((row) => row.id).join("|") || "empty";
	let $host = $wrapper.children(".staff-pro-access-host");
	if ($host.length && $host.attr("data-signature") === signature) return;
	if (!$host.length) {
		$host = $('<div class="staff-pro-access-host">').appendTo($wrapper);
	}
	$host.attr("data-signature", signature);
	window.hrms.role_access.render_section($host, {
		title: __("Roles"),
		intro: rows.length
			? __("Roles this person is attached to. Permissions and access come from those roles.")
			: __("No roles yet. Attach this user from the Role page."),
		rows,
	});
}

function parse_blocked_modules(raw) {
	if (!raw) return [];
	if (Array.isArray(raw)) return raw;
	try {
		const parsed = JSON.parse(raw);
		return Array.isArray(parsed) ? parsed : [];
	} catch (e) {
		return String(raw)
			.split(",")
			.map((part) => part.trim())
			.filter(Boolean);
	}
}

function set_blocked_bpo_modules(frm, blocked) {
	const value = JSON.stringify(blocked);
	if (frm.fields_dict.blocked_bpo_modules) {
		frm.set_value("blocked_bpo_modules", value);
		return;
	}
	frm.doc.blocked_bpo_modules = value;
	frm.dirty();
}

function hide_frappe_module_editor($wrap) {
	$wrap.children().each(function () {
		if (!$(this).hasClass("staff-pro-bpo-modules-wrap")) {
			$(this).hide();
		}
	});
}

function module_rows(frm) {
	const blocked = new Set(parse_blocked_modules(frm.doc.blocked_bpo_modules));
	return bpo_sidebar_modules().map((module) => ({
		id: module.value,
		label: __(module.label || module.value),
		description: MODULE_DESCRIPTIONS[module.value] || "",
		on: !blocked.has(module.value),
	}));
}

function install_bpo_module_editor(frm) {
	const $wrap = frm.fields_dict.modules_html?.$wrapper;
	if (!$wrap?.length || !window.hrms?.role_access?.render_section) return;

	hide_frappe_module_editor($wrap);
	hide_section_head("sb_allow_modules");
	const rows = module_rows(frm);
	const signature = rows.map((row) => `${row.id}:${row.on ? 1 : 0}`).join("|");
	let $host = $wrap.children(".staff-pro-access-host");
	if ($host.length && $host.attr("data-signature") === signature) return;
	if (!$host.length) {
		$host = $('<div class="staff-pro-access-host staff-pro-bpo-modules-wrap">').appendTo($wrap);
	}
	$host.attr("data-signature", signature);
	window.hrms.role_access.render_section(
		$host,
		{
			title: __("Modules"),
			intro: __("Parts of the app this person can open."),
			rows,
		},
		(_id, _on, access) => {
			const next_blocked = Object.keys(access).filter((key) => !access[key]);
			const signature = bpo_sidebar_modules()
				.map((module) => `${module.value}:${next_blocked.includes(module.value) ? 0 : 1}`)
				.join("|");
			$host.attr("data-signature", signature);
			set_blocked_bpo_modules(frm, next_blocked);
		},
	);
	frm._bpo_module_editor = true;
}

function lock_belize_user_timezone(frm) {
	if (!frm.fields_dict.time_zone) {
		return;
	}
	frm.set_df_property("time_zone", "read_only", 1);
	if (frm.doc.time_zone === "America/Belize") {
		return;
	}
	frm.doc.time_zone = "America/Belize";
	frm.refresh_field("time_zone");
}

const HIDDEN_USER_FIELDS = [
	"app_section",
	"default_app",
	"third_party_authentication",
	"social_logins",
	"role_profiles",
	"role_profile_name",
	"form_settings",
	"report_settings",
	"document_follow",
	"document_follow_notify",
	"follow_created_documents",
	"follow_commented_documents",
	"follow_liked_documents",
	"follow_assigned_documents",
	"follow_shared_documents",
	"email_settings",
	"thread_notify",
	"send_me_a_copy",
	"allowed_in_mentions",
	"email_signature",
	"workspace",
	"default_workspace",
	"connections_tab",
	"send_welcome_email",
	"search_bar",
	"notifications",
	"list_sidebar",
	"bulk_actions",
	"view_switcher",
	"form_sidebar",
	"timeline",
	"dashboard",
];

const HIDDEN_USER_TABS = ["Connections"];
const HIDDEN_USER_SECTIONS = [
	"Form Settings",
	"Report Settings",
	"Document Follow",
	"Email",
	"Workspace",
	"Role Profiles",
];

function hide_unused_user_settings(frm) {
	HIDDEN_USER_FIELDS.forEach((fieldname) => {
		if (frm.fields_dict[fieldname]) {
			frm.set_df_property(fieldname, "hidden", 1);
		}
	});
	hide_form_tabs(frm, HIDDEN_USER_TABS);
	hide_form_sections(frm, HIDDEN_USER_SECTIONS);
	hide_user_sidebar_chrome(frm);
}

function hide_form_tabs(frm, labels) {
	const hidden = new Set(labels.map((label) => __(label)));
	labels.forEach((label) => hidden.add(label));
	$(frm.page?.wrapper || frm.$wrapper)
		.find("#form-tabs .nav-item, .form-tabs .nav-item, .form-tabs-list .nav-item")
		.each(function () {
			const text = ($(this).text() || "").replace(/\s+/g, " ").trim();
			if (hidden.has(text)) {
				$(this).addClass("hidden hide").hide();
			}
		});
}

function hide_form_sections(frm, labels) {
	const hidden = new Set(labels.map((label) => __(label)));
	labels.forEach((label) => hidden.add(label));
	$(frm.page?.wrapper || frm.$wrapper)
		.find(".form-section .section-head")
		.each(function () {
			const text = ($(this).text() || "").replace(/\s+/g, " ").trim();
			if (!hidden.has(text)) return;
			$(this).closest(".form-section").addClass("hidden hide").hide();
		});
}

function hide_user_sidebar_chrome(frm) {
	const $sidebar = $(frm.page?.wrapper || frm.$wrapper).find(".form-sidebar");
	if (!$sidebar.length) return;
	$sidebar
		.find(".form-print, .liked-by, .like-action, .form-assignments")
		.addClass("hidden hide")
		.hide();
	$sidebar.find(".sidebar-section.form-assignments, .sidebar-section:has(.form-print)").hide();
}

function strip_unused_user_actions(frm) {
	["Impersonate", "Create User Email", "Reset Password", "Set Password"].forEach((label) => {
		frm.remove_custom_button(__(label), __("Password"));
		frm.remove_custom_button(__(label), __("Permissions"));
		frm.remove_custom_button(__(label));
		frm.page?.remove_inner_button?.(__(label));
		frm.page?.remove_inner_button?.(__(label), __("Password"));
		frm.page?.remove_inner_button?.(__(label), __("Permissions"));
	});
	window.hrms?.role_access?.strip_user_buttons?.(frm.page?.wrapper || frm.$wrapper);
	$(frm.page?.wrapper || frm.$wrapper)
		.find(".inner-group-button")
		.each(function () {
			const text = ($(this).find("button").first().text() || "").replace(/\s+/g, " ").trim();
			if (text === __("Password") || text === "Password" || text === __("Permissions") || text === "Permissions") {
				$(this).addClass("hidden hide").hide();
			}
		});
}

const USER_PASSWORD_ADMIN_ROLES = ["System Manager", "HR Manager", "HR User", "Administrator"];

function is_user_password_admin() {
	return (frappe.user_roles || []).some((role) => USER_PASSWORD_ADMIN_ROLES.includes(role));
}

function can_change_user_password(frm) {
	const can_write =
		typeof frappe.model.can_write === "function" ? frappe.model.can_write("User") : true;
	return (
		can_write &&
		!frm.is_new() &&
		!!frm.doc?.name &&
		!["Administrator", "Guest"].includes(frm.doc.name) &&
		is_user_password_admin()
	);
}

function setup_user_password_panel(frm) {
	const $page = frm.page?.wrapper || frm.$wrapper;
	if (!$page?.length) return;

	if (!can_change_user_password(frm)) {
		$page.find(".sp-user-password").remove();
		return;
	}

	const mount = () => {
		const $section = $page.find('.form-section[data-fieldname="section_break_3"]').first();
		if (!$section.length) return false;
		const $body = $section.children(".section-body");
		const $host = $body.length ? $body : $section;
		$page.find(".sp-user-password").not($host.children(".sp-user-password")).remove();
		if ($host.children(".sp-user-password").length) return true;

		const $panel = $(`
			<div class="sp-user-password sp-emp-password" style="clear:both;width:100%;flex:0 0 100%;max-width:100%;margin-top:12px">
				<div class="sp-emp-password__title">${frappe.utils.escape_html(__("Password"))}</div>
				<p class="sp-emp-password__help">${frappe.utils.escape_html(
					__("Set or change this person's login password."),
				)}</p>
				<label class="sp-emp-password__label">
					<span>${frappe.utils.escape_html(__("Current password"))}</span>
					<div class="sp-emp-password__reveal">
						<input type="password" class="form-control sp-user-password__current" readonly autocomplete="off" placeholder="${frappe.utils.escape_html(__("Hidden"))}" />
						<button type="button" class="btn btn-default btn-sm sp-user-password__toggle">${frappe.utils.escape_html(__("Show"))}</button>
					</div>
					<div class="sp-user-password__note text-muted"></div>
				</label>
				<label class="sp-emp-password__label">
					<span>${frappe.utils.escape_html(__("New password"))}</span>
					<input type="password" class="form-control sp-user-password__input" autocomplete="new-password" />
				</label>
				<label class="sp-emp-password__label">
					<span>${frappe.utils.escape_html(__("Confirm password"))}</span>
					<input type="password" class="form-control sp-user-password__confirm" autocomplete="new-password" />
				</label>
				<label class="sp-emp-password__check">
					<input type="checkbox" class="sp-user-password__logout" />
					<span>${frappe.utils.escape_html(__("Log out of all sessions"))}</span>
				</label>
				<button type="button" class="btn btn-primary btn-sm sp-emp-password__save sp-user-password__save">${frappe.utils.escape_html(
					__("Update Password"),
				)}</button>
			</div>
		`).appendTo($host);

		$panel.on("click", ".sp-user-password__toggle", () => {
			const $input = $panel.find(".sp-user-password__current");
			const $note = $panel.find(".sp-user-password__note");
			const $button = $panel.find(".sp-user-password__toggle");
			if ($input.attr("type") === "text") {
				$input.attr("type", "password").val("");
				$note.text("");
				$button.text(__("Show"));
				return;
			}
			frappe.call({
				method: "hrms.overrides.employee_master.get_user_password",
				args: { user: frm.doc.name },
				freeze: true,
				freeze_message: __("Loading password..."),
			}).then((r) => {
				const password = r.message?.password || "";
				if (!password) {
					$input.attr("type", "password").val("");
					$note.text(
						__(
							"No saved password yet. It is stored when you set one here, or the next time this person signs in.",
						),
					);
					return;
				}
				$input.attr("type", "text").val(password);
				$note.text("");
				$button.text(__("Hide"));
			});
		});

		$panel.on("click", ".sp-user-password__save", () => {
			const password = String($panel.find(".sp-user-password__input").val() || "");
			const confirm = String($panel.find(".sp-user-password__confirm").val() || "");
			if (password.length < 8) {
				frappe.msgprint(__("Password must be at least 8 characters."));
				return;
			}
			if (password !== confirm) {
				frappe.msgprint(__("Passwords do not match."));
				return;
			}
			const $save = $panel.find(".sp-user-password__save").prop("disabled", true);
			frappe.call({
				method: "hrms.overrides.employee_master.set_user_password",
				args: {
					user: frm.doc.name,
					new_password: password,
					logout_all_sessions: $panel.find(".sp-user-password__logout").is(":checked") ? 1 : 0,
				},
				freeze: true,
				freeze_message: __("Updating password..."),
				callback(r) {
					$save.prop("disabled", false);
					if (!r?.message) return;
					$panel.find(".sp-user-password__input, .sp-user-password__confirm").val("");
					$panel.find(".sp-user-password__logout").prop("checked", false);
					$panel.find(".sp-user-password__current").attr("type", "password").val("");
					$panel.find(".sp-user-password__note").text("");
					$panel.find(".sp-user-password__toggle").text(__("Show"));
					frappe.show_alert({
						message: __("Password updated"),
						indicator: "green",
					});
				},
				error() {
					$save.prop("disabled", false);
				},
			});
		});
		return true;
	};

	if (mount() || frm._user_password_waiting) return;
	frm._user_password_waiting = true;
	let tries = 0;
	const timer = setInterval(() => {
		tries += 1;
		if (mount() || tries > 20) {
			clearInterval(timer);
			frm._user_password_waiting = false;
		}
	}, 150);
}

function use_username_for_new_user(frm) {
	if (frm.fields_dict.username) {
		frm.set_df_property("username", "hidden", 0);
		frm.set_df_property("username", "reqd", frm.is_new() ? 1 : 0);
	}
	if (frm.is_new() && frm.fields_dict.email) {
		if (frm.fields_dict.username) {
			frm.set_df_property("email", "hidden", 1);
			frm.set_df_property("email", "reqd", 0);
			frm.set_df_property("email", "options", "");
		} else {
			frm.set_df_property("email", "label", __("Username"));
			frm.set_df_property("email", "options", "");
			frm.set_df_property("email", "reqd", 1);
			frm.fields_dict.email.df.options = "";
			frm.refresh_field("email");
		}
	}
	if (frm.fields_dict.send_welcome_email) {
		frm.set_df_property("send_welcome_email", "hidden", 1);
		if (frm.is_new()) {
			frm.doc.send_welcome_email = 0;
		}
	}
}

function apply_bpo_user_form(frm) {
	hide_module_profile(frm);
	use_username_for_new_user(frm);
	mount_role_switches(frm);
	install_bpo_module_editor(frm);
	lock_belize_user_timezone(frm);
	hide_unused_user_settings(frm);
	strip_unused_user_actions(frm);
	setup_user_password_panel(frm);
}

function watch_user_pickers(frm) {
	const roles_el = frm.fields_dict.roles_html?.$wrapper?.get(0);
	if (roles_el && !roles_el._staffProBpoObserved) {
		roles_el._staffProBpoObserved = true;
		new MutationObserver(() => mount_role_switches(frm)).observe(roles_el, {
			childList: true,
			subtree: true,
		});
	}

	const modules_el = frm.fields_dict.modules_html?.$wrapper?.get(0);
	if (modules_el && !modules_el._staffProBpoObserved) {
		modules_el._staffProBpoObserved = true;
		new MutationObserver(() => hide_frappe_module_editor($(modules_el))).observe(modules_el, {
			childList: true,
		});
	}

	const actions = frm.page?.wrapper?.find(".page-actions, .custom-actions").get(0);
	if (actions && !actions._staffProUserActions) {
		actions._staffProUserActions = true;
		new MutationObserver(() => strip_unused_user_actions(frm)).observe(actions, {
			childList: true,
			subtree: true,
		});
	}

	const tabs = frm.page?.wrapper?.find("#form-tabs").get(0);
	if (tabs && !tabs._staffProUserTabs) {
		tabs._staffProUserTabs = true;
		new MutationObserver(() => hide_unused_user_settings(frm)).observe(tabs, {
			childList: true,
			subtree: true,
		});
	}
}

frappe.ui.form.on("User", {
	onload(frm) {
		frm._bpo_module_editor = null;
		apply_bpo_user_form(frm);
		watch_user_pickers(frm);
	},
	refresh(frm) {
		apply_bpo_user_form(frm);
		watch_user_pickers(frm);
	},
	before_save(frm) {
		if (!frm.is_new()) return;
		const typed = (frm.doc.username || frm.doc.email || "").trim();
		if (!typed || typed.includes("@")) return;
		frm.doc.username = typed;
		frm.doc.email = `${typed.toLowerCase()}@users.staffpro.local`;
		frm.doc.send_welcome_email = 0;
	},
});
