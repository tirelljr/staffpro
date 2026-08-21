// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings["Payroll Entry"] = {
	has_indicator_for_draft: 1,
	formatters: {
		payroll_frequency: function (value) {
			return hrms.payroll_frequency_label ? hrms.payroll_frequency_label(value) : __(value);
		},
	},
	get_indicator: function (doc) {
		var status_color = {
			Draft: "red",
			Submitted: "blue",
			Queued: "orange",
			Failed: "red",
			Cancelled: "red",
		};
		return [__(doc.status), status_color[doc.status], "status,=," + doc.status];
	},

	onload: function (listview) {
		hide_payroll_view_switcher(listview);
		place_payroll_days_button(listview);
		refresh_automatic_payroll_ui(listview);
	},

	refresh: function (listview) {
		hide_payroll_view_switcher(listview);
		place_payroll_days_button(listview);
		refresh_automatic_payroll_ui(listview);
	},
};

function hide_payroll_view_switcher(listview) {
	const $wrapper = listview?.page?.wrapper;
	if (!$wrapper) return;
	$wrapper
		.find(".view-switcher, .views-switcher")
		.addClass("hidden hide")
		.hide();
}

function place_payroll_days_button(listview) {
	const page = listview?.page;
	const $host = page?.custom_actions?.length
		? page.custom_actions
		: page?.wrapper?.find(".custom-actions").first();
	if (!$host?.length) return;
	if ($host.find(".staff-pro-payroll-days-btn").length) return;
	if (!frappe.perm.has_perm("Payroll Settings", 0, "write")) return;

	const $btn = $(
		`<div class="custom-btn-group staff-pro-payroll-days-wrap">
			<button type="button" class="es-button ellipsis staff-pro-payroll-days-btn">${frappe.utils.escape_html(
				__("Payroll Days"),
			)}</button>
		</div>`,
	);
	$btn.on("click", () => open_payroll_days_dialog(listview));
	$host.prepend($btn);
}

function refresh_automatic_payroll_ui(listview) {
	frappe.call({
		method: "hrms.payroll.auto_payroll.get_automatic_payroll_status",
		callback: function (r) {
			const status = r.message || {};
			apply_automatic_payroll_indicator(listview, status);
			if (status.enabled && frappe.perm.has_perm("Payroll Entry", 0, "create")) {
				if (!listview._staff_pro_run_payroll_btn) {
					listview._staff_pro_run_payroll_btn = true;
					listview.page.add_inner_button(__("Run Payroll Now"), () => run_payroll_now(listview));
				}
			}
		},
		error: function () {
			// Optional status widget; missing Payroll Settings fields must not block this list.
		},
	});
}

function apply_automatic_payroll_indicator(listview, status) {
	if (!status.enabled) {
		if (typeof listview.page.clear_indicator === "function") {
			listview.page.clear_indicator();
		}
		return;
	}
	show_automatic_payroll_indicator(listview, status);
}

function show_automatic_payroll_indicator(listview, status) {
	const period_end = status.period_end || status.next_end;
	if (!period_end) {
		listview.page.set_indicator(__("Auto payroll enabled"), "blue");
		return;
	}

	const today = frappe.datetime.get_today();
	const days =
		status.days_until == null ? frappe.datetime.get_diff(period_end, today) : cint(status.days_until);
	const period_label = frappe.datetime.str_to_user(period_end);
	let text;
	let color = "blue";

	if (days > 1) {
		text = __("Auto payroll in {0} days (period ends {1})", [days, period_label]);
		color = days <= 3 ? "orange" : "blue";
	} else if (days === 1) {
		text = __("Auto payroll in 1 day (period ends {0})", [period_label]);
		color = "orange";
	} else if (days === 0) {
		text = __("Auto payroll today (period ends {0})", [period_label]);
		color = "green";
	} else {
		text = __("Auto payroll due (period ends {0})", [period_label]);
		color = "green";
	}

	listview.page.set_indicator(text, color);
}

function open_payroll_days_dialog(listview) {
	frappe.call({
		method: "hrms.payroll.auto_payroll.get_automatic_payroll_status",
		callback: function (r) {
			show_payroll_days_dialog(listview, r.message || {});
		},
		error: function () {
			show_payroll_days_dialog(listview, {});
		},
	});
}

function show_payroll_days_dialog(listview, status) {
	const dialog = new frappe.ui.Dialog({
		title: __("Set Payroll Days"),
		fields: [
			{
				fieldname: "enable_automatic_payroll",
				label: __("Run Payroll Automatically"),
				fieldtype: "Check",
				default: status.enabled ? 1 : 0,
			},
			{
				fieldname: "weekly_days",
				label: __("Weekly"),
				fieldtype: "Int",
				default: cint(status.weekly_days),
				description: __("Working days (Mon–Fri) in a weekly pay period. Set 0 to skip this template."),
			},
			{
				fieldname: "fortnightly_days",
				label: __("2-weeks"),
				fieldtype: "Int",
				default: cint(status.fortnightly_days),
				description: __("Working days (Mon–Fri) in a 2-week pay period. Set 0 to skip this template."),
			},
			{
				fieldname: "monthly_days",
				label: __("Monthly"),
				fieldtype: "Int",
				default: cint(status.monthly_days),
				description: __("Working days (Mon–Fri) in a monthly pay period. Set 0 to skip this template."),
			},
		],
		primary_action_label: __("Save"),
		primary_action(values) {
			const weekly = cint(values.weekly_days);
			const fortnightly = cint(values.fortnightly_days);
			const monthly = cint(values.monthly_days);
			if (values.enable_automatic_payroll && weekly < 1 && fortnightly < 1 && monthly < 1) {
				frappe.msgprint(__("Set days for Weekly, 2-weeks, or Monthly."));
				return;
			}
			dialog.hide();
			frappe.call({
				method: "hrms.payroll.auto_payroll.set_automatic_payroll_interval",
				args: {
					weekly_days: weekly,
					fortnightly_days: fortnightly,
					monthly_days: monthly,
					enable: values.enable_automatic_payroll ? 1 : 0,
				},
				freeze: true,
				freeze_message: __("Saving payroll schedule..."),
				callback: function (r) {
					apply_automatic_payroll_indicator(listview, r.message || {});
					listview.refresh();
					frappe.show_alert({
						message: __("Payroll schedule saved"),
						indicator: "green",
					});
				},
			});
		},
	});
	dialog.show();
}

function run_payroll_now(listview) {
	frappe.call({
		method: "hrms.payroll.auto_payroll.run_automatic_payroll_now",
		freeze: true,
		freeze_message: __("Running payroll..."),
		callback: function (r) {
			listview.refresh();
			if (r.message && r.message.message) {
				frappe.msgprint(r.message.message);
			}
		},
	});
}
