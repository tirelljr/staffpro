// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings["Client Invoice"] = {
	has_indicator_for_draft: 1,
	get_indicator: function (doc) {
		const status_color = {
			Draft: "red",
			Submitted: "blue",
			Cancelled: "red",
		};
		return [__(doc.status), status_color[doc.status] || "gray", "status,=," + doc.status];
	},

	onload: function (listview) {
		hide_client_invoice_list_chrome(listview);
		set_add_client_invoice_action(listview);
		place_invoice_days_button(listview);
		refresh_automatic_invoice_ui(listview);
	},

	refresh: function (listview) {
		hide_client_invoice_list_chrome(listview);
		set_add_client_invoice_action(listview);
		place_invoice_days_button(listview);
		refresh_automatic_invoice_ui(listview);
	},
};

function hide_client_invoice_list_chrome(listview) {
	const page = listview?.page;
	if (!page) return;
	if (typeof page.hide_menu === "function") {
		page.hide_menu();
	}
	page.menu_btn_group?.addClass("hidden hide").hide();
	page.wrapper
		?.find(".menu-btn-group, .view-switcher, .views-switcher")
		.addClass("hidden hide")
		.hide();
}

function open_client_invoice() {
	frappe.new_doc("Client Invoice");
}

function set_add_client_invoice_action(listview) {
	if (!listview?.page) return;

	const can_add =
		!frappe.boot?.read_only &&
		(frappe.model.can_create("Client Invoice") || listview.can_create);

	listview.set_primary_action = () => {
		if (can_add) {
			listview.page.set_primary_action(__("Add Client Invoice"), open_client_invoice);
		} else {
			listview.page.clear_primary_action();
		}
	};
	listview.make_new_doc = open_client_invoice;
	listview.set_primary_action();
}

function place_invoice_days_button(listview) {
	const page = listview?.page;
	const $host = page?.custom_actions?.length
		? page.custom_actions
		: page?.wrapper?.find(".custom-actions").first();
	if (!$host?.length) return;
	if ($host.find(".staff-pro-invoice-days-btn").length) return;
	if (!frappe.perm.has_perm("Payroll Settings", 0, "write")) return;

	const $btn = $(
		`<div class="custom-btn-group staff-pro-invoice-days-wrap">
			<button type="button" class="es-button ellipsis staff-pro-invoice-days-btn">${frappe.utils.escape_html(
				__("Invoice Days"),
			)}</button>
		</div>`,
	);
	$btn.on("click", () => open_invoice_days_dialog(listview));
	$host.prepend($btn);
}

function refresh_automatic_invoice_ui(listview) {
	frappe.call({
		method: "hrms.payroll.auto_client_invoice.get_automatic_invoice_status",
		callback: function (r) {
			const status = r.message || {};
			apply_automatic_invoice_indicator(listview, status);
			if (status.enabled && frappe.perm.has_perm("Client Invoice", 0, "create")) {
				if (!listview._staff_pro_run_invoice_btn) {
					listview._staff_pro_run_invoice_btn = true;
					listview.page.add_inner_button(__("Run Auto Client Invoice"), () =>
						run_client_invoices_now(listview),
					);
				}
			}
		},
		error: function () {
			// Optional status widget; missing settings fields must not block this list.
		},
	});
}

function apply_automatic_invoice_indicator(listview, status) {
	if (!status.enabled) {
		if (typeof listview.page.clear_indicator === "function") {
			listview.page.clear_indicator();
		}
		return;
	}
	show_automatic_invoice_indicator(listview, status);
}

function show_automatic_invoice_indicator(listview, status) {
	const period_end = status.period_end || status.next_end;
	if (!period_end) {
		listview.page.set_indicator(__("Auto invoice enabled"), "blue");
		return;
	}

	const today = frappe.datetime.get_today();
	const days =
		status.days_until == null ? frappe.datetime.get_diff(period_end, today) : cint(status.days_until);
	const period_label = frappe.datetime.str_to_user(period_end);
	let text;
	let color = "blue";

	if (days > 1) {
		text = __("Auto invoice in {0} days (period ends {1})", [days, period_label]);
		color = days <= 3 ? "orange" : "blue";
	} else if (days === 1) {
		text = __("Auto invoice in 1 day (period ends {0})", [period_label]);
		color = "orange";
	} else if (days === 0) {
		text = __("Auto invoice today (period ends {0})", [period_label]);
		color = "green";
	} else {
		text = __("Auto invoice due (period ends {0})", [period_label]);
		color = "green";
	}

	listview.page.set_indicator(text, color);
}

function open_invoice_days_dialog(listview) {
	frappe.call({
		method: "hrms.payroll.auto_client_invoice.get_automatic_invoice_status",
		callback: function (r) {
			show_invoice_days_dialog(listview, r.message || {});
		},
		error: function () {
			show_invoice_days_dialog(listview, {});
		},
	});
}

function show_invoice_days_dialog(listview, status) {
	const dialog = new frappe.ui.Dialog({
		title: __("Set Invoice Days"),
		fields: [
			{
				fieldname: "enable_automatic_client_invoice",
				label: __("Run Client Invoices Automatically"),
				fieldtype: "Check",
				default: status.enabled ? 1 : 0,
			},
			{
				fieldname: "weekly_days",
				label: __("Weekly"),
				fieldtype: "Int",
				default: cint(status.weekly_days),
				description: __("Days in a weekly billing period. Set 0 to skip this template."),
			},
			{
				fieldname: "fortnightly_days",
				label: __("2-weeks"),
				fieldtype: "Int",
				default: cint(status.fortnightly_days),
				description: __("Days in a 2-week billing period. Set 0 to skip this template."),
			},
			{
				fieldname: "monthly_days",
				label: __("Monthly"),
				fieldtype: "Int",
				default: cint(status.monthly_days),
				description: __("Days in a monthly billing period. Set 0 to skip this template."),
			},
		],
		primary_action_label: __("Save"),
		primary_action(values) {
			const weekly = cint(values.weekly_days);
			const fortnightly = cint(values.fortnightly_days);
			const monthly = cint(values.monthly_days);
			if (values.enable_automatic_client_invoice && weekly < 1 && fortnightly < 1 && monthly < 1) {
				frappe.msgprint(__("Set days for Weekly, 2-weeks, or Monthly."));
				return;
			}
			dialog.hide();
			frappe.call({
				method: "hrms.payroll.auto_client_invoice.set_automatic_invoice_interval",
				args: {
					weekly_days: weekly,
					fortnightly_days: fortnightly,
					monthly_days: monthly,
					enable: values.enable_automatic_client_invoice ? 1 : 0,
				},
				freeze: true,
				freeze_message: __("Saving invoice schedule..."),
				callback: function (r) {
					apply_automatic_invoice_indicator(listview, r.message || {});
					listview.refresh();
					frappe.show_alert({
						message: __("Invoice schedule saved"),
						indicator: "green",
					});
				},
			});
		},
	});
	dialog.show();
}

function run_client_invoices_now(listview) {
	frappe.call({
		method: "hrms.payroll.auto_client_invoice.run_automatic_invoices_now",
		freeze: true,
		freeze_message: __("Running client invoices..."),
		callback: function (r) {
			listview.refresh();
			if (r.message && r.message.message) {
				frappe.msgprint(r.message.message);
			}
		},
	});
}
