// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("System Settings", {
	refresh(frm) {
		hide_system_settings_app_tab(frm);
	},

	scan_bpo_ipv4(frm) {
		scan_bpo_ipv4(frm);
	},
});

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
