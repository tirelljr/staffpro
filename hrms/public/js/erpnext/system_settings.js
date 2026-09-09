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

function scan_bpo_ipv4(frm) {
	frappe.call({
		method: "hrms.hr.agent_access.scan_office_ipv4",
		freeze: true,
		freeze_message: __("Scanning the office network for IPv4 hosts..."),
		callback(r) {
			const ips = (r.message?.ips || []).filter(Boolean);
			const fallback = r.message?.ip;
			if (fallback && !ips.includes(fallback)) {
				ips.unshift(fallback);
			}
			if (!ips.length) {
				return;
			}

			const current = (frm.doc.office_clockin_ipv4 || "").trim();
			const parts = current ? current.split(/[\s,;]+/).filter(Boolean) : [];
			ips.forEach((ip) => {
				if (!parts.includes(ip)) {
					parts.push(ip);
				}
			});

			frm.set_value("restrict_agent_clockin_to_office_ip", 1);
			frm.set_value("office_clockin_ipv4", parts.join("\n"));
			const applied = r.message?.employees || 0;
			frappe.show_alert({
				message: __(
					"Found {0} office IPv4 address(es). Default agent IP is {1}. Updated {2} agent(s).",
					[ips.length, r.message?.default_ip || ips[0], applied],
				),
				indicator: "green",
			});
		},
	});
}
