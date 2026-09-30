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

function checkbox_value($input) {
	return (
		$input.attr("data-unit") ||
		$input.data("unit") ||
		$input.attr("data-value") ||
		$input.val() ||
		""
	).toString();
}

const ROLE_ORDER = [
	"HR Manager",
	"HR User",
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

function role_checkbox_rows($wrapper) {
	const allowlist = bpo_role_allowlist();
	const by_name = new Map();
	$wrapper.find("input[type=checkbox]").each(function () {
		const value = checkbox_value($(this));
		if (!value || (allowlist.size && !allowlist.has(value))) return;
		by_name.set(value, this);
	});
	const ordered = ROLE_ORDER.filter((role) => by_name.has(role));
	by_name.forEach((_input, role) => {
		if (!ordered.includes(role)) ordered.push(role);
	});
	return ordered.map((role) => ({
		id: role,
		label: role,
		description: ROLE_DESCRIPTIONS[role] || "",
		on: !!by_name.get(role).checked,
		input: by_name.get(role),
	}));
}

function mount_role_switches(frm) {
	const $wrapper = frm.fields_dict.roles_html?.$wrapper;
	if (!$wrapper?.length || !window.hrms?.role_access?.render_section) return;
	const rows = role_checkbox_rows($wrapper);
	if (!rows.length) return;

	$wrapper.children().not(".staff-pro-access-host").hide();
	hide_section_head("sb1");
	if (frm.fields_dict.role_profiles) {
		frm.set_df_property("role_profiles", "hidden", 1);
	}

	const signature = rows.map((row) => `${row.id}:${row.on ? 1 : 0}`).join("|");
	let $host = $wrapper.children(".staff-pro-access-host");
	if ($host.length && $host.attr("data-signature") === signature) return;
	if (!$host.length) {
		$host = $('<div class="staff-pro-access-host">').appendTo($wrapper);
	}
	$host.attr("data-signature", signature);
	window.hrms.role_access.render_section(
		$host,
		{
			title: __("Roles"),
			intro: __("What this person can sign in as."),
			rows,
		},
		(role, on) => {
			const input = rows.find((row) => row.id === role)?.input;
			if (!input || input.checked === !!on) return;
			input.checked = !!on;
			input.dispatchEvent(new Event("change", { bubbles: true }));
			$host.attr("data-signature", role_checkbox_rows($wrapper).map((row) => `${row.id}:${row.on ? 1 : 0}`).join("|"));
		},
	);
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

function hide_unused_user_settings(frm) {
	["app_section", "default_app", "third_party_authentication", "social_logins"].forEach(
		(fieldname) => {
			if (frm.fields_dict[fieldname]) {
				frm.set_df_property(fieldname, "hidden", 1);
			}
		}
	);
}

function strip_unused_user_actions(frm) {
	["Impersonate", "Create User Email"].forEach((label) => {
		frm.remove_custom_button(__(label));
		frm.page?.remove_inner_button?.(__(label));
	});
	window.hrms?.role_access?.strip_user_buttons?.(frm.page?.wrapper || frm.$wrapper);
}

function apply_bpo_user_form(frm) {
	hide_module_profile(frm);
	mount_role_switches(frm);
	install_bpo_module_editor(frm);
	lock_belize_user_timezone(frm);
	hide_unused_user_settings(frm);
	strip_unused_user_actions(frm);
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
});
