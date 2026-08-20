// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("System Settings", {
	refresh(frm) {
		hide_system_settings_app_tab(frm);
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
