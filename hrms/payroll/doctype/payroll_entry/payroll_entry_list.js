// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

(function applyPayrollEntryListLabels() {
	const messages = frappe._messages || frappe.boot?.__messages || {};
	Object.assign(messages, {
		"Add Payroll Entry": "Client Payroll Entry",
	});
	frappe._messages = messages;
	if (frappe.boot) {
		frappe.boot.__messages = messages;
	}
})();

frappe.listview_settings["Payroll Entry"] = {
	has_indicator_for_draft: 1,
	add_fields: ["end_date", "start_date", "customer", "status", "docstatus"],
	formatters: {
		payroll_frequency: function (value) {
			return hrms.payroll_frequency_label ? hrms.payroll_frequency_label(value) : __(value);
		},
		customer: function (value) {
			return value === "All Clients" ? __("All Clients") : value || "";
		},
		start_date: function (value, df, options, doc) {
			if (!value) return "";
			const row = doc || options || {};
			const start = frappe.datetime.str_to_user(value);
			const end = row.end_date ? frappe.datetime.str_to_user(row.end_date) : "";
			return end ? `${start} – ${end}` : start;
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
		patch_payroll_entry_actions_menu();
		hide_payroll_view_switcher(listview);
		hide_unneeded_payroll_entry_actions(listview);
		set_client_payroll_entry_action(listview);
		place_payroll_days_button(listview);
		place_run_payroll_for_every_agent_button(listview);
		bind_payroll_selection_actions(listview);
		refresh_automatic_payroll_ui(listview);
	},

	refresh: function (listview) {
		hide_payroll_view_switcher(listview);
		hide_unneeded_payroll_entry_actions(listview);
		set_client_payroll_entry_action(listview);
		place_payroll_days_button(listview);
		place_run_payroll_for_every_agent_button(listview);
		bind_payroll_selection_actions(listview);
		sync_payroll_selection_action(listview);
		refresh_automatic_payroll_ui(listview);
	},
};

const HIDDEN_PAYROLL_ENTRY_ACTIONS = [
	"Copy to Clipboard",
	"Assign To",
	"Clear Assignment",
	"Apply Assignment Rule",
	"Add Tags",
];

function payroll_entry_action_label(value) {
	return decodeURIComponent(String(value || ""))
		.replace(/\s+/g, " ")
		.trim();
}

function is_hidden_payroll_entry_action(label) {
	const name = payroll_entry_action_label(label);
	if (!name) return false;
	return HIDDEN_PAYROLL_ENTRY_ACTIONS.some((hidden) => name === hidden || name === __(hidden));
}

function hide_unneeded_payroll_entry_actions(listview) {
	if (Array.isArray(listview?.actions_menu_items)) {
		listview.actions_menu_items = listview.actions_menu_items.filter(
			(item) => !is_hidden_payroll_entry_action(item?.label),
		);
	}

	const $stores = [listview?.page?.actions, listview?.page?.menu].filter(($el) => $el?.length);
	$stores.forEach(($store) => {
		$store.children("li").each(function () {
			const $li = $(this);
			const label = payroll_entry_action_label(
				$li.find(".menu-item-label").text() ||
					$li.find("a").attr("data-label") ||
					$li.text(),
			);
			if (is_hidden_payroll_entry_action(label)) {
				$li.remove();
			}
		});
	});
}

function patch_payroll_entry_actions_menu() {
	const ListView = frappe.views?.ListView;
	if (!ListView || ListView.prototype._staff_pro_payroll_entry_actions) return;

	const original = ListView.prototype.get_actions_menu_items;
	if (typeof original !== "function") return;

	ListView.prototype._staff_pro_payroll_entry_actions = true;
	ListView.prototype.get_actions_menu_items = function (...args) {
		const items = original.apply(this, arguments);
		if (this.doctype !== "Payroll Entry" || !Array.isArray(items)) {
			return items;
		}
		return items.filter((item) => !is_hidden_payroll_entry_action(item?.label));
	};
}

patch_payroll_entry_actions_menu();

function set_client_payroll_entry_action(listview) {
	if (!listview?.page) return;

	const can_add =
		!frappe.boot?.read_only &&
		(frappe.model.can_create("Payroll Entry") || listview.can_create);
	const make_new = listview.make_new_doc?.bind(listview) || (() => frappe.new_doc("Payroll Entry"));

	listview.set_primary_action = () => {
		if (can_add) {
			listview.page.set_primary_action(__("Client Payroll Entry"), () => make_new());
		} else {
			listview.page.clear_primary_action();
		}
	};
	listview.set_primary_action();
}

function hide_payroll_view_switcher(listview) {
	const $wrapper = listview?.page?.wrapper;
	if (!$wrapper) return;
	$wrapper
		.find(".view-switcher, .views-switcher")
		.addClass("hidden hide")
		.hide();
}

function inject_payroll_selection_styles() {
	if (document.getElementById("staff-pro-payroll-selection-styles")) return;
	const style = document.createElement("style");
	style.id = "staff-pro-payroll-selection-styles";
	style.textContent = `
		.page-form .staff-pro-payroll-selection-btn,
		.standard-filter-section .staff-pro-payroll-selection-btn {
			display: inline-flex;
			align-items: center;
			justify-content: center;
			height: 28px;
			margin-left: auto;
			padding: 0 14px;
			border: 0;
			border-radius: 6px;
			background: #dc2626;
			color: #ffffff;
			font: inherit;
			font-size: 13px;
			font-weight: 600;
			line-height: 1;
			white-space: nowrap;
			flex-shrink: 0;
			cursor: pointer;
			appearance: none;
			box-shadow: none;
		}
		.page-form .staff-pro-payroll-selection-btn:hover,
		.page-form .staff-pro-payroll-selection-btn:focus,
		.standard-filter-section .staff-pro-payroll-selection-btn:hover,
		.standard-filter-section .staff-pro-payroll-selection-btn:focus {
			background: #b91c1c;
			color: #ffffff;
		}
		.page-form .staff-pro-payroll-selection-btn[hidden],
		.standard-filter-section .staff-pro-payroll-selection-btn[hidden] {
			display: none !important;
		}
	`;
	document.head.appendChild(style);
}

function payroll_selection_host(listview) {
	const $form = listview?.page?.wrapper?.find(".page-form, .list-page-form").first();
	if (!$form?.length) return $();
	const $filters = $form.find(".standard-filter-section").first();
	return $filters.length ? $filters : $form;
}

function is_cancelled_payroll_entry(doc) {
	return cint(doc.docstatus) === 2 || doc.status === "Cancelled";
}

function can_cancel_payroll_entries() {
	return frappe.model.can_cancel("Payroll Entry") || frappe.model.can_write("Payroll Entry");
}

function can_delete_payroll_entries() {
	return frappe.model.can_delete("Payroll Entry");
}

function bind_payroll_selection_actions(listview) {
	inject_payroll_selection_styles();
	if (listview._staff_pro_payroll_selection_bound) {
		sync_payroll_selection_action(listview);
		return;
	}
	listview._staff_pro_payroll_selection_bound = true;
	const original = listview.on_row_checked;
	listview.on_row_checked = function () {
		if (typeof original === "function") {
			original.apply(this, arguments);
		}
		sync_payroll_selection_action(listview);
	};
	listview.page?.wrapper?.on(
		"change.sp-payroll-selection",
		".list-row-checkbox, .list-check-all",
		() => sync_payroll_selection_action(listview),
	);
	sync_payroll_selection_action(listview);
}

function sync_payroll_selection_action(listview) {
	const $host = payroll_selection_host(listview);
	if (!$host?.length) return;

	let $btn = $host.find(".staff-pro-payroll-selection-btn");
	if (!$btn.length) {
		$btn = $(
			`<button type="button" class="staff-pro-payroll-selection-btn" hidden>${frappe.utils.escape_html(
				__("Cancel"),
			)}</button>`,
		);
		$host.append($btn);
		$btn.on("click", function (e) {
			e.preventDefault();
			e.stopPropagation();
			run_payroll_selection_action(listview);
		});
	}

	const checked = listview.get_checked_items() || [];
	const all_cancelled = checked.length > 0 && checked.every(is_cancelled_payroll_entry);
	const show_delete = all_cancelled && can_delete_payroll_entries();
	const show_cancel = checked.length > 0 && !all_cancelled && can_cancel_payroll_entries();

	$btn.text(show_delete ? __("Delete") : __("Cancel"));
	if (show_delete || show_cancel) {
		$btn.removeAttr("hidden");
	} else {
		$btn.attr("hidden", true);
	}
}

function run_payroll_selection_action(listview) {
	const checked = listview.get_checked_items() || [];
	if (!checked.length) {
		frappe.msgprint(__("Please select the payroll entries first"));
		return;
	}

	if (checked.every(is_cancelled_payroll_entry)) {
		delete_selected_payroll_entries(
			listview,
			checked.map((row) => row.name),
		);
		return;
	}

	cancel_selected_payroll_entries(
		listview,
		checked.filter((row) => !is_cancelled_payroll_entry(row)).map((row) => row.name),
	);
}

function cancel_selected_payroll_entries(listview, names) {
	if (!names.length) {
		frappe.msgprint(__("Please select the payroll entries to cancel"));
		return;
	}
	const message =
		names.length === 1
			? __("Cancel this payroll entry?")
			: __("Cancel {0} payroll entries?", [names.length]);
	frappe.confirm(message, () => {
		frappe.call({
			method: "hrms.payroll.doctype.payroll_entry.payroll_entry.bulk_cancel_payroll_entries",
			args: { names },
			freeze: true,
			freeze_message: __("Cancelling..."),
			callback: function (r) {
				show_payroll_bulk_result(r.message || {}, "cancelled");
				listview.refresh();
			},
		});
	});
}

function delete_selected_payroll_entries(listview, names) {
	if (!names.length) {
		frappe.msgprint(__("Please select the payroll entries to delete"));
		return;
	}
	const message =
		names.length === 1
			? __("Delete this cancelled payroll entry permanently?")
			: __("Delete {0} cancelled payroll entries permanently?", [names.length]);
	frappe.confirm(message, () => {
		frappe.call({
			method: "hrms.payroll.doctype.payroll_entry.payroll_entry.bulk_delete_payroll_entries",
			args: { names },
			freeze: true,
			freeze_message: __("Deleting..."),
			callback: function (r) {
				show_payroll_bulk_result(r.message || {}, "deleted");
				listview.refresh();
			},
		});
	});
}

function show_payroll_bulk_result(payload, success_key) {
	const done = payload[success_key] || [];
	const errors = payload.errors || [];
	if (done.length) {
		const deleted = success_key === "deleted";
		frappe.show_alert({
			message: deleted
				? done.length === 1
					? __("Payroll entry deleted")
					: __("{0} payroll entries deleted", [done.length])
				: done.length === 1
					? __("Payroll entry cancelled")
					: __("{0} payroll entries cancelled", [done.length]),
			indicator: deleted ? "red" : "orange",
		});
	}
	if (errors.length) {
		frappe.msgprint({
			title: __("Some payroll entries could not be updated"),
			indicator: "red",
			message: errors
				.map((row) => `${frappe.utils.escape_html(row.name)}: ${frappe.utils.escape_html(row.error)}`)
				.join("<br>"),
		});
	}
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

function place_run_payroll_for_every_agent_button(listview) {
	const page = listview?.page;
	const $host = page?.custom_actions?.length
		? page.custom_actions
		: page?.wrapper?.find(".custom-actions").first();
	if (!$host?.length) return;
	if ($host.find(".staff-pro-run-payroll-every-agent-btn").length) return;
	if (!frappe.perm.has_perm("Payroll Entry", 0, "create")) return;

	const $btn = $(
		`<div class="custom-btn-group">
			<button type="button" class="btn btn-sm staff-pro-run-payroll-every-agent-btn">
				${frappe.utils.escape_html(__("Run Payroll For Every Agent"))}
			</button>
		</div>`,
	);
	$btn.find("button").css({
		background: "#000",
		color: "#fff",
		borderColor: "#000",
	});
	$btn.on("click", () => run_payroll_for_every_agent(listview));
	$host.append($btn);
}

function refresh_automatic_payroll_ui(listview) {
	remove_run_payroll_now_button(listview);
	frappe.call({
		method: "hrms.payroll.auto_payroll.get_automatic_payroll_status",
		callback: function (r) {
			const status = r.message || {};
			apply_automatic_payroll_indicator(listview, status);
			remove_run_payroll_now_button(listview);
		},
		error: function () {
			// Optional status widget; missing Payroll Settings fields must not block this list.
			remove_run_payroll_now_button(listview);
		},
	});
}

function remove_run_payroll_now_button(listview) {
	const page = listview?.page;
	if (!page) return;
	if (typeof page.remove_inner_button === "function") {
		page.remove_inner_button(__("Run Payroll Now"));
	}
	page.wrapper?.find(".custom-actions button").each(function () {
		const label = decodeURIComponent(this.getAttribute("data-label") || this.textContent || "");
		if (label.trim() === "Run Payroll Now") {
			this.remove();
		}
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

function run_payroll_for_every_agent(listview) {
	if (!hrms || !hrms.payroll_utils || typeof hrms.payroll_utils.confirm_payroll_run !== "function") {
		frappe.msgprint(__("Payroll preview is not available. Refresh the page and try again."));
		return;
	}
	hrms.payroll_utils.confirm_payroll_run({
		preview_method: "hrms.payroll.auto_payroll.preview_payroll_for_every_agent",
		run_method: "hrms.payroll.auto_payroll.run_payroll_for_every_agent_now",
		title: __("Approve Payroll For Every Agent"),
		freeze_message: __("Running payroll for every agent..."),
		on_done(payload) {
			listview.refresh();
			if (!payload) return;
			show_run_payroll_details_dialog(payload);
		},
	});
}

function show_run_payroll_details_dialog(payload) {
	const created = payload.created || [];
	const skipped = payload.skipped || [];
	const details = payload.details || {};
	const created_by_bucket = details.created_by_bucket || {};

	const createdHtml = created.length
		? `<ul style="margin: 0; padding-left: 18px;">
				${created.map((name) => `<li>${frappe.utils.escape_html(name)}</li>`).join("")}
			</ul>`
		: `<span class="text-muted">${__("None")}</span>`;

	const skippedHtml = skipped.length
		? `<ul style="margin: 0; padding-left: 18px;">
				${skipped.map((name) => `<li>${frappe.utils.escape_html(name)}</li>`).join("")}
			</ul>`
		: `<span class="text-muted">${__("None")}</span>`;

	const bucketsEntries = Object.entries(created_by_bucket);
	const bucketHtml = bucketsEntries.length
		? `<div style="max-height: 220px; overflow: auto;">
				${bucketsEntries
					.map(
						([bucketKey, names]) => `
							<div style="margin-bottom: 12px;">
								<div><b>${frappe.utils.escape_html(bucketKey)}</b> (${(names || []).length})</div>
								<ul style="margin: 6px 0 0; padding-left: 18px;">
									${(names || [])
										.map((n) => `<li>${frappe.utils.escape_html(n)}</li>`)
										.join("")}
								</ul>
							</div>
						`,
					)
					.join("")}
			</div>`
		: `<span class="text-muted">${__("Not provided")}</span>`;

	const dialog = new frappe.ui.Dialog({
		title: __("Run Payroll For Every Agent - Details"),
		fields: [
			{
				fieldname: "summary",
				fieldtype: "HTML",
				options: `
					<div style="margin-bottom: 12px;">
						<div><b>${__("Message")}:</b> ${frappe.utils.escape_html(payload.message || "")}</div>
					</div>
					<div style="margin-bottom: 12px;">
						<div><b>${__("Created Payroll Entries")}:</b> (${created.length})</div>
						${createdHtml}
					</div>
					<div style="margin-bottom: 12px;">
						<div><b>${__("Skipped")}:</b> (${skipped.length})</div>
						${skippedHtml}
					</div>
					<div style="margin-bottom: 12px;">
						<div><b>${__("Breakdown by Bucket")}:</b></div>
						${bucketHtml}
					</div>
				`,
			},
		],
		primary_action_label: __("Close"),
		primary_action() {
			dialog.hide();
		},
	});

	dialog.show();
}
