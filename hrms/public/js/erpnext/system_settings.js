// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

const STAFF_PRO_TIMEZONE = "America/Belize";

frappe.ui.form.on("System Settings", {
	refresh(frm) {
		lock_belize_timezone(frm);
		hide_system_settings_app_tab(frm);
		sync_ask_ai_provider_defaults(frm, false);
	},

	ask_ai_provider(frm) {
		sync_ask_ai_provider_defaults(frm, true);
	},

	scan_bpo_ipv4(frm) {
		scan_bpo_ipv4(frm);
	},
});

function ask_ai_provider_defaults() {
	return {
		DeepSeek: { model: "deepseek-chat", base: "https://api.deepseek.com", key: __("DeepSeek API Key") },
		OpenAI: { model: "gpt-4.1-mini", base: "https://api.openai.com/v1", key: __("OpenAI API Key") },
		Anthropic: { model: "claude-sonnet-4-5", base: "", key: __("Anthropic API Key") },
		Custom: { model: "", base: "", key: __("Provider API Key") },
	};
}

function sync_ask_ai_provider_defaults(frm, overwrite) {
	if (!frm.fields_dict.ask_ai_provider) {
		return;
	}
	const provider = frm.doc.ask_ai_provider || "DeepSeek";
	const defaults = ask_ai_provider_defaults()[provider] || ask_ai_provider_defaults().DeepSeek;
	frm.set_df_property("ask_ai_api_key", "label", defaults.key);
	if (!overwrite) {
		return;
	}
	if (defaults.model) {
		frm.set_value("ask_ai_model", defaults.model);
	}
	frm.set_value("ask_ai_api_base", defaults.base);
}

function lock_belize_timezone(frm) {
	if (!frm.fields_dict.time_zone) {
		return;
	}
	frm.set_df_property("time_zone", "read_only", 1);
	if (frm.doc.time_zone === STAFF_PRO_TIMEZONE) {
		return;
	}
	frm.doc.time_zone = STAFF_PRO_TIMEZONE;
	frm.refresh_field("time_zone");
}

function hide_system_settings_app_tab(frm) {
	["default_app", "app_tab"].forEach((fieldname) => {
		frm.set_df_property(fieldname, "hidden", 1);
	});

	frm.$wrapper?.find("#system-settings-app_tab").hide();
	frm.$wrapper
		?.find("#form-tabs .nav-item, .form-tabs .nav-item, .form-tabs-list .nav-item")
		.each(function () {
			const text = ($(this).text() || "").replace(/\s+/g, " ").trim();
			if (text === "App" || text === __("App")) {
				$(this).addClass("hidden hide").hide();
			}
		});
}

async function scan_bpo_ipv4(frm) {
	frappe.dom.freeze(__("Scanning your real network IPv4..."));
	let scanned = [];
	try {
		if (hrms.scanClientNetworkIpv4s) {
			scanned = await hrms.scanClientNetworkIpv4s();
		}
	} catch {
		scanned = [];
	}

	frappe.call({
		method: "hrms.hr.agent_access.scan_office_ipv4",
		args: {
			client_ip: scanned[0] || "",
			client_ips: scanned.join("\n"),
		},
		callback(r) {
			frappe.dom.unfreeze();
			apply_scanned_office_ipv4s(frm, r.message || {}, scanned);
		},
		error() {
			frappe.dom.unfreeze();
		},
	});
}

function apply_scanned_office_ipv4s(frm, result, scanned) {
	const ips = [];
	const add = (ip) => {
		if (ip && !ips.includes(ip)) {
			ips.push(ip);
		}
	};
	(result.ips || []).forEach(add);
	add(result.ip);
	(scanned || []).forEach(add);
	const current = (frm.doc.office_clockin_ipv4 || "").trim();
	if (current) {
		current.split(/[\s,;]+/).filter(Boolean).forEach(add);
	}

	if (!ips.length) {
		frappe.msgprint({
			title: __("No office hosts found"),
			indicator: "orange",
			message: __(
				"Could not detect a real network IPv4 address. Open System Settings from the office network and try again.",
			),
		});
		return;
	}

	frm.set_value("restrict_agent_clockin_to_office_ip", 1);
	frm.set_value("office_clockin_ipv4", ips.join("\n"));
	const applied = result.employees || 0;
	const methods = (result.methods || []).join(", ") || "client";
	frappe.show_alert({
		message: __(
			"Found {0} office IPv4 address(es) via {1}. Default agent IP is {2}. Updated {3} agent(s).",
			[ips.length, methods, result.default_ip || ips[0], applied],
		),
		indicator: "green",
	});
}
