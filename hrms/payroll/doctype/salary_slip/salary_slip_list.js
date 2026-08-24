frappe.listview_settings["Salary Slip"] = {
	add_fields: [
		"payment_status",
		"payment_date",
		"payment_time",
		"docstatus",
		"ss_employee_amount",
		"start_date",
		"end_date",
		"net_pay",
		"currency",
		"bank_name",
		"bank_account_no",
		"paid_from_bank",
		"paid_from_bank_account",
		"employee_name",
		"company",
		"salary_withholding",
	],
	hide_name_column: true,
	get_indicator: function (doc) {
		if (doc.docstatus === 2) {
			return [__("Cancelled"), "gray", "docstatus,=,2"];
		}
		if (doc.payment_status === "Paid") {
			return [__("Paid"), "green", "payment_status,=,Paid"];
		}
		if (doc.docstatus === 1) {
			return [__("Not Paid"), "orange", "payment_status,=,Not Paid"];
		}
		return [__("Draft"), "red", "docstatus,=,0"];
	},
	formatters: {
		payroll_frequency: function (value) {
			return hrms.payroll_frequency_label ? hrms.payroll_frequency_label(value) : __(value);
		},
		ss_employee_amount: function (value, df, options, doc) {
			return format_currency(value || 0, doc && doc.currency);
		},
		payment_time: function (value) {
			return format_payment_time(value);
		},
		pay_agent: function () {
			return "";
		},
	},
	onload: function (listview) {
		inject_pay_agent_styles();
		move_ss_column_beside_net_pay(listview);
		apply_past_payment_columns(listview);
		ensure_pay_agent_column(listview);
		setup_pay_stubs_list(listview);
		place_salary_slip_export(listview);
		bind_bulk_slip_actions(listview);
		sync_bulk_slip_actions(listview);

		if (
			!has_common(frappe.user_roles, [
				"Administrator",
				"System Manager",
				"HR Manager",
				"HR User",
			])
		)
			return;

		listview.page.add_menu_item(__("Email Salary Slips"), () => {
			if (!listview.get_checked_items().length) {
				frappe.msgprint(__("Please select the salary slips to email"));
				return;
			}

			frappe.confirm(__("Are you sure you want to email the selected salary slips?"), () => {
				listview.call_for_selected_items(
					"hrms.payroll.doctype.salary_slip.salary_slip.enqueue_email_salary_slips",
				);
			});
		});
	},
	refresh: function (listview) {
		move_ss_column_beside_net_pay(listview);
		apply_past_payment_columns(listview);
		ensure_pay_agent_column(listview);
		place_pay_agent_buttons(listview);
		apply_pay_stubs_status_filter(listview);
		set_pay_stubs_title(listview);
		ensure_past_date_filters(listview);
		place_salary_slip_export(listview);
		sync_bulk_slip_actions(listview);
	},
};

function place_salary_slip_export(listview) {
	hrms.mount_invoice_list_export?.(listview, {
		doctype: "Salary Slip",
		label: __("Salary Slip"),
		file_stem: "Salary_Slips",
		storage_key: "staff-pro-salary-slip-export-format",
		method_prefix: "hrms.payroll.salary_slip_export",
		default_format: "PDF",
		min_selected: 1,
	});
}

const PAY_STUBS_MODE_KEY = "staff_pro_pay_stubs_view";

function get_pay_stubs_mode() {
	try {
		const params = new URLSearchParams(window.location.search);
		const from_url = (params.get("pay_stubs") || "").toLowerCase();
		if (from_url === "past" || from_url === "current") {
			sessionStorage.setItem(PAY_STUBS_MODE_KEY, from_url);
			return from_url;
		}
	} catch (e) {
		/* ignore */
	}
	try {
		const stored = sessionStorage.getItem(PAY_STUBS_MODE_KEY);
		if (stored === "past" || stored === "current") {
			return stored;
		}
	} catch (e) {
		/* ignore */
	}
	return "current";
}

function can_pay_agents() {
	return has_common(frappe.user_roles, [
		"Administrator",
		"System Manager",
		"HR Manager",
		"HR User",
	]);
}

function can_delete_slips() {
	return frappe.model.can_delete
		? frappe.model.can_delete("Salary Slip")
		: frappe.perm.has_perm("Salary Slip", 0, "delete");
}

function is_payable_slip(doc) {
	return cint(doc?.docstatus) === 1 && doc.payment_status !== "Paid" && !doc.salary_withholding;
}

function is_deletable_slip(doc) {
	const status = cint(doc?.docstatus);
	return status === 0 || status === 2;
}

function setup_pay_stubs_list(listview) {
	apply_pay_stubs_status_filter(listview);
	ensure_past_date_filters(listview);
	set_pay_stubs_title(listview);
	place_pay_agent_buttons(listview);
}

function apply_pay_stubs_status_filter(listview) {
	if (!listview?.filter_area) return;
	const mode = get_pay_stubs_mode();
	const status = mode === "past" ? "Paid" : "Not Paid";
	const existing = (listview.filter_area.get?.() || []).find((row) => row[1] === "payment_status");
	if (existing && existing[3] === status) {
		listview._staff_pro_pay_status = status;
		return;
	}
	if (listview._staff_pro_applying_pay_status) return;
	listview._staff_pro_applying_pay_status = true;
	listview._staff_pro_pay_status = status;
	try {
		listview.filter_area.remove("payment_status");
		listview.filter_area.add([[listview.doctype, "payment_status", "=", status]]);
	} finally {
		listview._staff_pro_applying_pay_status = false;
	}
}

function set_pay_stubs_title(listview) {
	const mode = get_pay_stubs_mode();
	const title = mode === "past" ? __("Past Pay Stubs") : __("Current Pay Stubs");
	if (typeof listview.page?.set_title === "function") {
		listview.page.set_title(title);
	}
}

function move_ss_column_beside_net_pay(listview) {
	if (!listview?.columns) return;
	const ss_idx = listview.columns.findIndex((col) => col.df?.fieldname === "ss_employee_amount");
	if (ss_idx < 0) return;

	const ss_col = listview.columns[ss_idx];
	ss_col.df = Object.assign({}, ss_col.df, { label: __("Social Security") });

	const net_idx = listview.columns.findIndex((col) => col.df?.fieldname === "net_pay");
	if (net_idx < 0) return;
	if (ss_idx === net_idx + 1) return;

	listview.columns.splice(ss_idx, 1);
	const insert_at = listview.columns.findIndex((col) => col.df?.fieldname === "net_pay") + 1;
	listview.columns.splice(insert_at, 0, ss_col);
}

function format_payment_time(value) {
	if (!value) return "";
	const raw = String(value).split(".")[0];
	if (typeof frappe.datetime.time_to_user === "function") {
		return frappe.datetime.time_to_user(raw);
	}
	if (window.moment) {
		const parsed = moment(raw, ["HH:mm:ss", "HH:mm"]);
		if (parsed.isValid()) {
			return parsed.format("h:mm A");
		}
	}
	return raw.slice(0, 5);
}

function snapshot_list_column(col) {
	return {
		type: col.type,
		df: Object.assign({}, col.df),
	};
}

function apply_past_payment_columns(listview) {
	if (!listview?.columns) return;
	const past = get_pay_stubs_mode() === "past";
	const changed = sync_past_payment_columns(listview, past);
	if (!changed || listview._staff_pro_rendering_payment_cols) return;
	if (typeof listview.render !== "function" || !listview.$result?.length) return;

	listview._staff_pro_rendering_payment_cols = true;
	try {
		listview.render();
	} finally {
		listview._staff_pro_rendering_payment_cols = false;
	}
}

function sync_past_payment_columns(listview, past) {
	let changed = false;

	const status_idx = listview.columns.findIndex(
		(col) =>
			col.type === "Status" || ["status_field", "payment_time"].includes(col.df?.fieldname),
	);
	if (status_idx >= 0) {
		const current = listview.columns[status_idx];
		if (
			!listview._staff_pro_status_col &&
			(current.type === "Status" || current.df?.fieldname === "status_field")
		) {
			listview._staff_pro_status_col = snapshot_list_column(current);
		}
		const target = past
			? {
					type: "Field",
					df: {
						label: __("Payment Time"),
						fieldname: "payment_time",
						fieldtype: "Time",
						width: 110,
					},
				}
			: listview._staff_pro_status_col;
		if (
			target &&
			(current.type !== target.type || current.df?.fieldname !== target.df?.fieldname)
		) {
			listview.columns[status_idx] = {
				type: target.type,
				df: Object.assign({}, target.df),
			};
			changed = true;
		}
	}

	const date_idx = listview.columns.findIndex((col) =>
		["posting_date", "payment_date"].includes(col.df?.fieldname),
	);
	if (date_idx >= 0) {
		const current = listview.columns[date_idx];
		if (!listview._staff_pro_date_col && current.df?.fieldname === "posting_date") {
			listview._staff_pro_date_col = snapshot_list_column(current);
		}
		const target = past
			? {
					type: "Field",
					df: {
						label: __("Payment Date"),
						fieldname: "payment_date",
						fieldtype: "Date",
						width: listview._staff_pro_date_col?.df?.width,
					},
				}
			: listview._staff_pro_date_col;
		if (target && current.df?.fieldname !== target.df?.fieldname) {
			listview.columns[date_idx] = {
				type: target.type,
				df: Object.assign({}, target.df),
			};
			changed = true;
		}
	}

	return changed;
}

function ensure_pay_agent_column(listview) {
	if (!listview?.columns) return;
	const idx = listview.columns.findIndex((col) => col.df?.fieldname === "pay_agent");
	if (get_pay_stubs_mode() === "past" || (!can_pay_agents() && !can_delete_slips())) {
		if (idx >= 0) {
			listview.columns.splice(idx, 1);
		}
		return;
	}

	const col = {
		type: "Field",
		df: {
			label: __("Pay Agent"),
			fieldname: "pay_agent",
			fieldtype: "Data",
			width: 110,
		},
	};
	if (idx < 0) {
		const status_idx = listview.columns.findIndex((c) => c.df?.fieldname === "payment_status");
		if (status_idx >= 0) {
			listview.columns.splice(status_idx + 1, 0, col);
		} else {
			listview.columns.push(col);
		}
		return;
	}

	const status_idx = listview.columns.findIndex((c) => c.df?.fieldname === "payment_status");
	if (status_idx >= 0 && idx !== status_idx + 1) {
		const [existing] = listview.columns.splice(idx, 1);
		const insert_at = listview.columns.findIndex((c) => c.df?.fieldname === "payment_status") + 1;
		listview.columns.splice(insert_at, 0, existing);
	}
}

function inject_pay_agent_styles() {
	if (document.getElementById("staff-pro-pay-agent-styles")) return;
	const style = document.createElement("style");
	style.id = "staff-pro-pay-agent-styles";
	style.textContent = `
		.list-row-col[data-fieldname="pay_agent"],
		.list-row-head .list-row-col:has([data-sort-by="pay_agent"]) {
			overflow: visible !important;
			min-width: 108px;
		}
		.staff-pro-pay-agent-btn {
			background: #1e3a8a !important;
			color: #ffffff !important;
			border: 0 !important;
			border-radius: 4px;
			padding: 2px 10px;
			font-size: 12px;
			font-weight: 600;
			line-height: 1.4;
			white-space: nowrap;
			box-shadow: none !important;
		}
		.staff-pro-pay-agent-btn:hover,
		.staff-pro-pay-agent-btn:focus {
			background: #1e40af !important;
			color: #ffffff !important;
		}
		.staff-pro-pay-agent-delete {
			background: #dc2626 !important;
			color: #ffffff !important;
			border: 0 !important;
			border-radius: 4px;
			padding: 2px 10px;
			font-size: 12px;
			font-weight: 600;
			line-height: 1.4;
			white-space: nowrap;
			box-shadow: none !important;
		}
		.staff-pro-pay-agent-delete:hover,
		.staff-pro-pay-agent-delete:focus {
			background: #b91c1c !important;
			color: #ffffff !important;
		}
		.staff-pro-slip-bulk-actions {
			display: inline-flex;
			align-items: center;
			gap: 8px;
			margin-right: 8px;
		}
		.staff-pro-slip-bulk-actions[hidden] {
			display: none !important;
		}
		.staff-pro-bulk-pay-agents,
		.staff-pro-bulk-delete-slips {
			display: inline-flex;
			align-items: center;
			height: 28px;
			padding: 0 12px;
			border: 0;
			border-radius: 6px;
			font: inherit;
			font-size: 13px;
			font-weight: 600;
			line-height: 1;
			white-space: nowrap;
			cursor: pointer;
			appearance: none;
			box-shadow: none;
			color: #ffffff;
		}
		.staff-pro-bulk-pay-agents[hidden],
		.staff-pro-bulk-delete-slips[hidden] {
			display: none !important;
		}
		.staff-pro-bulk-pay-agents {
			background: #1e3a8a;
		}
		.staff-pro-bulk-pay-agents:hover,
		.staff-pro-bulk-pay-agents:focus {
			background: #1e40af;
			color: #ffffff;
		}
		.staff-pro-bulk-delete-slips {
			background: #dc2626;
		}
		.staff-pro-bulk-delete-slips:hover,
		.staff-pro-bulk-delete-slips:focus {
			background: #b91c1c;
			color: #ffffff;
		}
		.staff-pro-pay-dialog .staff-pro-pay-table {
			width: 100%;
			border-collapse: collapse;
			font-size: 13px;
		}
		.staff-pro-pay-dialog .staff-pro-pay-table th,
		.staff-pro-pay-dialog .staff-pro-pay-table td {
			padding: 8px 10px;
			border-bottom: 1px solid var(--border-color, #e5e7eb);
			text-align: left;
			vertical-align: top;
		}
		.staff-pro-pay-dialog .staff-pro-pay-table th {
			color: var(--text-muted, #6b7280);
			font-weight: 600;
			white-space: nowrap;
		}
		.staff-pro-pay-dialog .staff-pro-pay-table td.num,
		.staff-pro-pay-dialog .staff-pro-pay-table th.num {
			text-align: right;
		}
		.staff-pro-pay-dialog .staff-pro-pay-total {
			margin-top: 12px;
			font-weight: 600;
			font-size: 14px;
			text-align: right;
		}
		.staff-pro-pay-dialog .staff-pro-pay-meta {
			margin-bottom: 10px;
			color: var(--text-muted, #6b7280);
		}
		.staff-pro-pay-dialog .btn-primary {
			background: #1e3a8a !important;
			border-color: #1e3a8a !important;
			color: #fff !important;
		}
	`;
	document.head.appendChild(style);
}

function place_pay_agent_buttons(listview) {
	inject_pay_agent_styles();
	const $result = listview.$result;
	if (!$result?.length) return;

	$result.find(".staff-pro-pay-agent-btn, .staff-pro-pay-agent-delete").remove();
	if (get_pay_stubs_mode() === "past") return;

	$result.find(".list-row-container").each(function () {
		const $container = $(this);
		if ($container.find(".list-row-head").length) return;

		const name =
			$container.find(".list-row-checkbox").attr("data-name") ||
			$container.attr("data-name") ||
			"";
		if (!name) return;

		const $cell = $container.find('[data-fieldname="pay_agent"]');
		if (!$cell.length) return;

		const doc = (listview.data || []).find((row) => row.name === name) || {};
		if (is_payable_slip(doc) && can_pay_agents()) {
			$cell.html(
				`<button type="button" class="btn btn-xs staff-pro-pay-agent-btn" data-slip="${frappe.utils.escape_html(
					name,
				)}">${frappe.utils.escape_html(__("Pay Agent"))}</button>`,
			);
			return;
		}
		if (is_deletable_slip(doc) && can_delete_slips()) {
			$cell.html(
				`<button type="button" class="btn btn-xs staff-pro-pay-agent-delete" data-slip="${frappe.utils.escape_html(
					name,
				)}">${frappe.utils.escape_html(__("Delete"))}</button>`,
			);
			return;
		}
		$cell.empty();
	});

	$result.off("click.payagent").on("click.payagent", ".staff-pro-pay-agent-btn", function (e) {
		e.preventDefault();
		e.stopPropagation();
		e.stopImmediatePropagation();
		const clicked = $(this).attr("data-slip");
		open_pay_confirm_dialog(listview, names_for_action(listview, clicked, is_payable_slip));
	});
	$result.off("click.delslip").on("click.delslip", ".staff-pro-pay-agent-delete", function (e) {
		e.preventDefault();
		e.stopPropagation();
		e.stopImmediatePropagation();
		const clicked = $(this).attr("data-slip");
		delete_salary_slips(listview, names_for_action(listview, clicked, is_deletable_slip));
	});
	bind_bulk_slip_actions(listview);
}

function names_for_action(listview, clicked_name, predicate) {
	const checked = (listview.get_checked_items() || []).filter(predicate);
	const names = checked.map((item) => item.name);
	if (names.length > 1 && names.includes(clicked_name)) {
		return names;
	}
	return clicked_name ? [clicked_name] : names;
}

function slip_actions_host(listview) {
	const page = listview?.page;
	return page?.custom_actions?.length
		? page.custom_actions
		: page?.wrapper?.find(".custom-actions").first();
}

function bind_bulk_slip_actions(listview) {
	if (listview._staff_pro_bulk_slip_bound) return;
	listview._staff_pro_bulk_slip_bound = true;
	const original = listview.on_row_checked;
	listview.on_row_checked = function () {
		if (typeof original === "function") {
			original.apply(this, arguments);
		}
		sync_bulk_slip_actions(listview);
	};
	listview.page?.wrapper?.on(
		"change.sp-slip-bulk",
		".list-row-checkbox, .list-check-all",
		() => sync_bulk_slip_actions(listview),
	);
}

function sync_bulk_slip_actions(listview) {
	const $host = slip_actions_host(listview);
	if (!$host?.length) return;

	$host.removeClass("hidden hide");
	let $wrap = $host.find(".staff-pro-slip-bulk-actions");
	if (!$wrap.length) {
		$wrap = $(`<div class="staff-pro-slip-bulk-actions" hidden>
			<button type="button" class="staff-pro-bulk-pay-agents" hidden>${frappe.utils.escape_html(
				__("Pay Agents"),
			)}</button>
			<button type="button" class="staff-pro-bulk-delete-slips" hidden>${frappe.utils.escape_html(
				__("Delete"),
			)}</button>
		</div>`);
		const $export = $host.find(".sp-invoice-export").first();
		if ($export.length) {
			$export.after($wrap);
		} else {
			$host.prepend($wrap);
		}
		$wrap.on("click", ".staff-pro-bulk-pay-agents", function (e) {
			e.preventDefault();
			e.stopPropagation();
			open_pay_confirm_dialog(
				listview,
				(listview.get_checked_items() || []).filter(is_payable_slip).map((row) => row.name),
			);
		});
		$wrap.on("click", ".staff-pro-bulk-delete-slips", function (e) {
			e.preventDefault();
			e.stopPropagation();
			delete_salary_slips(
				listview,
				(listview.get_checked_items() || []).filter(is_deletable_slip).map((row) => row.name),
			);
		});
	}

	const current = get_pay_stubs_mode() !== "past";
	const checked = listview.get_checked_items() || [];
	const show_pay = current && can_pay_agents() && checked.some(is_payable_slip);
	const show_delete = current && can_delete_slips() && checked.some(is_deletable_slip);

	toggle_hidden($wrap.find(".staff-pro-bulk-pay-agents"), !show_pay);
	toggle_hidden($wrap.find(".staff-pro-bulk-delete-slips"), !show_delete);
	toggle_hidden($wrap, !(show_pay || show_delete));
}

function toggle_hidden($el, hidden) {
	if (!$el?.length) return;
	if (hidden) {
		$el.attr("hidden", true);
	} else {
		$el.removeAttr("hidden");
	}
}

function delete_salary_slips(listview, names) {
	if (!names?.length) {
		frappe.msgprint(__("Please select the pay stubs to delete"));
		return;
	}
	const message =
		names.length === 1
			? __("Delete this pay stub permanently?")
			: __("Delete {0} pay stubs permanently?", [names.length]);
	frappe.confirm(message, () => {
		frappe.call({
			method: "frappe.desk.reportview.delete_items",
			args: {
				doctype: "Salary Slip",
				items: names,
			},
			freeze: true,
			freeze_message: __("Deleting..."),
			callback: function () {
				frappe.show_alert({
					message:
						names.length === 1
							? __("Pay stub deleted")
							: __("{0} pay stubs deleted", [names.length]),
					indicator: "red",
				});
				listview.refresh();
			},
		});
	});
}

function open_pay_confirm_dialog(listview, names) {
	if (!names?.length) {
		frappe.msgprint(__("Please select the pay stubs to pay"));
		return;
	}

	frappe.call({
		method: "hrms.payroll.doctype.salary_slip.salary_slip.get_pay_preview",
		args: { names },
		freeze: true,
		freeze_message: __("Loading payment details..."),
		callback: function (r) {
			const preview = r.message || {};
			const agents = preview.agents || [];
			if (!agents.length) {
				frappe.msgprint(
					__("No unpaid submitted pay stubs were selected. Draft, cancelled, withheld, or already paid stubs were skipped."),
				);
				return;
			}
			show_pay_confirm_dialog(listview, preview);
		},
	});
}

function show_pay_confirm_dialog(listview, preview) {
	const agents = preview.agents || [];
	const names = agents.map((row) => row.name);
	const title =
		agents.length === 1
			? __("Confirm Payment for {0}", [agents[0].employee_name || agents[0].employee])
			: __("Confirm Payment for {0} Agents", [agents.length]);

	const dialog = new frappe.ui.Dialog({
		title,
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "details" }],
		primary_action_label: agents.length === 1 ? __("Pay Agent") : __("Pay Agents"),
		primary_action() {
			dialog.hide();
			submit_agent_payments(listview, names);
		},
	});
	dialog.$wrapper.addClass("staff-pro-pay-dialog");
	dialog.fields_dict.details.$wrapper.html(pay_preview_html(preview));
	dialog.show();
}

function pay_preview_html(preview) {
	const agents = preview.agents || [];
	const escape = frappe.utils.escape_html;
	const money = (amount, currency) => format_currency(amount || 0, currency || preview.currency);

	const rows = agents
		.map((row) => {
			const period = [row.start_date, row.end_date]
				.filter(Boolean)
				.map((value) => frappe.datetime.str_to_user(value))
				.join(" – ");
			return `<tr>
				<td>${escape(row.employee_name || row.employee || "")}</td>
				<td>${escape(period)}</td>
				<td>${escape(row.pay_from || "—")}</td>
				<td>${escape(row.pay_to || "—")}</td>
				<td class="num">${escape(money(row.ss_employee_amount, row.currency))}</td>
				<td class="num">${escape(money(row.net_pay, row.currency))}</td>
			</tr>`;
		})
		.join("");

	const total = money(preview.total_net, preview.currency);
	const intro =
		agents.length === 1
			? `<div class="staff-pro-pay-meta">${escape(__("Review the payment details, then confirm."))}</div>`
			: `<div class="staff-pro-pay-meta">${escape(
					__("Review the payment details for the selected agents, then confirm."),
				)}</div>`;

	return `${intro}
		<table class="staff-pro-pay-table">
			<thead>
				<tr>
					<th>${escape(__("Agent"))}</th>
					<th>${escape(__("Pay Period"))}</th>
					<th>${escape(__("Pay From"))}</th>
					<th>${escape(__("Pay To"))}</th>
					<th class="num">${escape(__("Social Security"))}</th>
					<th class="num">${escape(__("Net Pay"))}</th>
				</tr>
			</thead>
			<tbody>${rows}</tbody>
		</table>
		<div class="staff-pro-pay-total">${escape(__("Total"))}: ${escape(total)}</div>`;
}

function submit_agent_payments(listview, names) {
	frappe.call({
		method: "hrms.payroll.doctype.salary_slip.salary_slip.pay_agents",
		args: { names },
		freeze: true,
		freeze_message: __("Paying agent(s)..."),
		callback: function (r) {
			const paid = r.message?.paid || [];
			const skipped = r.message?.skipped || [];
			if (paid.length) {
				frappe.show_alert({
					message: __(
						paid.length === 1
							? "Agent paid. The pay stub moved to Past Pay Stubs."
							: "{0} agents paid. Their pay stubs moved to Past Pay Stubs.",
						[paid.length],
					),
					indicator: "green",
				});
			}
			if (skipped.length && !paid.length) {
				frappe.msgprint(
					__("No unpaid submitted pay stubs were selected. Draft, cancelled, withheld, or already paid stubs were skipped."),
				);
			}
			listview.refresh();
		},
	});
}

function ensure_past_date_filters(listview) {
	const mode = get_pay_stubs_mode();
	const from_field = listview.page?.fields_dict?.pay_stub_from_date;
	const to_field = listview.page?.fields_dict?.pay_stub_to_date;

	if (mode !== "past") {
		from_field?.$wrapper?.hide();
		to_field?.$wrapper?.hide();
		if (listview.filter_area && listview._staff_pro_past_date_filter_on) {
			listview.filter_area.remove("payment_date");
			listview.filter_area.remove("posting_date");
			listview._staff_pro_past_date_filter_on = false;
		}
		return;
	}

	if (!listview._staff_pro_past_dates && listview.page?.add_field) {
		listview._staff_pro_past_dates = true;
		listview.page.add_field({
			fieldtype: "Date",
			fieldname: "pay_stub_from_date",
			label: __("From Date"),
			change: () => apply_past_date_filters(listview),
		});
		listview.page.add_field({
			fieldtype: "Date",
			fieldname: "pay_stub_to_date",
			label: __("To Date"),
			change: () => apply_past_date_filters(listview),
		});
	}

	listview.page.fields_dict?.pay_stub_from_date?.$wrapper?.show();
	listview.page.fields_dict?.pay_stub_to_date?.$wrapper?.show();
}

function apply_past_date_filters(listview) {
	if (!listview?.filter_area) return;
	const from = listview.page.fields_dict?.pay_stub_from_date?.get_value?.();
	const to = listview.page.fields_dict?.pay_stub_to_date?.get_value?.();
	const fieldname = (listview.meta?.fields || []).some((field) => field.fieldname === "payment_date")
		? "payment_date"
		: "posting_date";

	listview.filter_area.remove("payment_date");
	listview.filter_area.remove("posting_date");
	if (from) {
		listview.filter_area.add([[listview.doctype, fieldname, ">=", from]]);
	}
	if (to) {
		listview.filter_area.add([[listview.doctype, fieldname, "<=", to]]);
	}
	listview._staff_pro_past_date_filter_on = Boolean(from || to);
}
