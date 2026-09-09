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

function filter_role_checkboxes(frm) {
	const allowlist = bpo_role_allowlist();
	const $wrapper = frm.fields_dict.roles_html?.$wrapper;
	if (!$wrapper?.length || !allowlist.size) return;

	$wrapper.find("input[type=checkbox]").each(function () {
		const value = checkbox_value($(this));
		if (value && !allowlist.has(value)) {
			$(this).closest(".checkbox, .checkbox-option, label, .unit-checkbox").hide();
		}
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

function install_bpo_module_editor(frm) {
	const $wrap = frm.fields_dict.modules_html?.$wrapper;
	if (!$wrap?.length) return;

	hide_frappe_module_editor($wrap);
	if (frm._bpo_module_editor) return;

	const blocked = new Set(parse_blocked_modules(frm.doc.blocked_bpo_modules));
	const $host = $('<div class="staff-pro-bpo-modules-wrap">').appendTo($wrap);
	const options = bpo_sidebar_modules().map((module) => ({
		label: __(module.label || module.value),
		value: module.value,
		checked: !blocked.has(module.value),
	}));

	const control = frappe.ui.form.make_control({
		parent: $host,
		df: {
			fieldname: "staff_pro_bpo_modules",
			fieldtype: "MultiCheck",
			select_all: true,
			columns: 2,
			options,
			on_change: () => {
				const next_blocked = [];
				$host.find("input[type=checkbox]").each(function () {
					const value = checkbox_value($(this));
					if (value && !this.checked) next_blocked.push(value);
				});
				set_blocked_bpo_modules(frm, next_blocked);
			},
		},
	});
	control.refresh();
	frm._bpo_module_editor = control;
}

function apply_bpo_user_form(frm) {
	hide_module_profile(frm);
	filter_role_checkboxes(frm);
	install_bpo_module_editor(frm);
}

function watch_user_pickers(frm) {
	const roles_el = frm.fields_dict.roles_html?.$wrapper?.get(0);
	if (roles_el && !roles_el._staffProBpoObserved) {
		roles_el._staffProBpoObserved = true;
		new MutationObserver(() => filter_role_checkboxes(frm)).observe(roles_el, {
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
