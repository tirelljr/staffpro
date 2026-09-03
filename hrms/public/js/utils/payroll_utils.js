hrms.payroll_utils = {
	confirm_payroll_run(opts) {
		const preview_method = opts.preview_method;
		const run_method = opts.run_method;
		const title = opts.title || __("Approve Payroll");
		const freeze_message = opts.freeze_message || __("Creating payroll...");
		const on_done = opts.on_done;

		frappe.call({
			method: preview_method,
			freeze: true,
			freeze_message: __("Preparing payroll preview..."),
			callback(r) {
				try {
					hrms.payroll_utils.show_payroll_preview_dialog({
						preview: r.message || {},
						title,
						preview_method,
						run_method,
						freeze_message,
						on_done,
					});
				} catch (e) {
					console.error(e);
					frappe.msgprint({
						title: __("Payroll preview failed"),
						message: e.message || e,
						indicator: "red",
					});
				}
			},
			error() {
				frappe.msgprint({
					title: __("Payroll preview failed"),
					message: __("The server did not return a payroll preview. Refresh the page and try again."),
					indicator: "red",
				});
			},
		});
	},

	preview_period_dates(preview) {
		const source = preview || {};
		const entries = source.entries || [];
		let start = source.start_date || "";
		let end = source.end_date || "";
		if (!start && entries.length) {
			start = entries.reduce((earliest, row) => {
				return !earliest || row.start_date < earliest ? row.start_date : earliest;
			}, "");
		}
		if (!end && entries.length) {
			end = entries.reduce((latest, row) => {
				return !latest || row.end_date > latest ? row.end_date : latest;
			}, "");
		}
		return { start, end };
	},

	show_payroll_preview_dialog({ preview, title, preview_method, run_method, freeze_message, on_done }) {
		let current = preview || {};
		const dates = hrms.payroll_utils.preview_period_dates(current);
		const can_create = Boolean(current.can_create && (current.entries || []).length);
		const dialog = new frappe.ui.Dialog({
			title: title || __("Approve Payroll"),
			size: "large",
			fields: [
				{
					fieldname: "start_date",
					fieldtype: "Date",
					label: __("Start Date"),
					default: dates.start || null,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "end_date",
					fieldtype: "Date",
					label: __("End Date"),
					default: dates.end || null,
				},
				{
					fieldtype: "Section Break",
					description: __(
						"Change the pay period to recalculate agents, hours, and who is included.",
					),
				},
				{
					fieldname: "summary",
					fieldtype: "HTML",
					options: hrms.payroll_utils.render_payroll_preview_html(current),
				},
			],
			primary_action_label: can_create ? __("Approve & Create") : __("Close"),
			primary_action() {
				if (!can_create_from(current)) {
					dialog.hide();
					return;
				}
				const period = selected_dates();
				if (!period.start || !period.end) {
					frappe.msgprint(__("Select a Start Date and End Date"));
					return;
				}
				if (period.start > period.end) {
					frappe.msgprint(__("End Date cannot be before Start Date"));
					return;
				}
				dialog.hide();
				frappe.call({
					method: run_method,
					args: { start_date: period.start, end_date: period.end },
					freeze: true,
					freeze_message: freeze_message || __("Creating payroll..."),
					callback(r) {
						if (typeof on_done === "function") {
							on_done(r.message);
						}
					},
				});
			},
		});

		function can_create_from(payload) {
			return Boolean(payload && payload.can_create && (payload.entries || []).length);
		}

		function selected_dates() {
			return {
				start: dialog.get_value("start_date") || "",
				end: dialog.get_value("end_date") || "",
			};
		}

		function apply_preview(next) {
			current = next || {};
			const summary = dialog.fields_dict.summary;
			if (summary && summary.$wrapper) {
				summary.$wrapper.html(hrms.payroll_utils.render_payroll_preview_html(current));
			}
			const $btn = typeof dialog.get_primary_btn === "function" ? dialog.get_primary_btn() : null;
			if ($btn && $btn.length) {
				$btn.text(can_create_from(current) ? __("Approve & Create") : __("Close"));
			}
		}

		let last_start = dates.start || "";
		let last_end = dates.end || "";
		let ready = false;

		function reload_preview() {
			if (!ready || !preview_method) {
				return;
			}
			const period = selected_dates();
			if (!period.start || !period.end) {
				return;
			}
			if (period.start > period.end) {
				frappe.msgprint(__("End Date cannot be before Start Date"));
				return;
			}
			if (period.start === last_start && period.end === last_end) {
				return;
			}
			last_start = period.start;
			last_end = period.end;
			frappe.call({
				method: preview_method,
				args: { start_date: period.start, end_date: period.end },
				freeze: true,
				freeze_message: __("Updating payroll preview..."),
				callback(r) {
					apply_preview(r.message || {});
				},
			});
		}

		if (can_create) {
			dialog.set_secondary_action_label(__("Cancel"));
			dialog.set_secondary_action(() => dialog.hide());
		}
		dialog.show();

		const start_field = dialog.get_field("start_date");
		const end_field = dialog.get_field("end_date");
		if (start_field && start_field.df) {
			start_field.df.change = reload_preview;
		}
		if (end_field && end_field.df) {
			end_field.df.change = reload_preview;
		}
		ready = true;
		return dialog;
	},

	render_payroll_preview_html(preview) {
		preview = preview || {};
		const entries = preview.entries || [];
		const skipped = preview.skipped || [];
		const rows = entries
			.map((entry) => {
				const period = [entry.start_date, entry.end_date]
					.filter(Boolean)
					.map((value) => frappe.datetime.str_to_user(value))
					.join(" – ");
				const agents = (entry.agent_names || []).length
					? frappe.utils.escape_html((entry.agent_names || []).join(", "))
					: __("None");
				const note = entry.note
					? `<div class="text-muted" style="margin-top: 4px;">${frappe.utils.escape_html(entry.note)}</div>`
					: "";
				return `<tr>
					<td>${frappe.utils.escape_html(entry.customer_label || __("All Agents"))}</td>
					<td>${frappe.utils.escape_html(entry.label || entry.frequency || "")}</td>
					<td>${frappe.utils.escape_html(period)}</td>
					<td>${cint(entry.agents)}</td>
					<td>${flt(entry.hours).toFixed(2)}</td>
					<td>${agents}${note}</td>
				</tr>`;
			})
			.join("");

		const table = entries.length
			? `<table class="table table-bordered" style="margin-top: 12px;">
				<thead>
					<tr>
						<th>${__("Client")}</th>
						<th>${__("Pay Template")}</th>
						<th>${__("Pay Period")}</th>
						<th>${__("Agents")}</th>
						<th>${__("Hours")}</th>
						<th>${__("Agents / Notes")}</th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>`
			: `<p class="text-muted">${__("Nothing to create.")}</p>`;

		const skipped_html = skipped.length
			? `<div style="margin-top: 12px;">
				<div><b>${__("Skipped")}</b></div>
				<ul style="margin: 6px 0 0; padding-left: 18px;">
					${skipped.map((item) => `<li>${frappe.utils.escape_html(item)}</li>`).join("")}
				</ul>
			</div>`
			: "";

		return `
			<div>
				<p>${frappe.utils.escape_html(preview.message || "")}</p>
				${table}
				${skipped_html}
			</div>
		`;
	},

	set_autocompletions_for_condition_and_formula: function (frm, child_row = "") {
		const autocompletions = [];
		frappe.run_serially([
			...["Employee", "Salary Structure", "Salary Structure Assignment", "Salary Slip"].map(
				(doctype) =>
					frappe.model.with_doctype(doctype, () => {
						autocompletions.push(
							...hrms.get_doctype_fields_for_autocompletion(doctype),
						);
					}),
			),
			() => {
				frappe.db
					.get_list("Salary Component", {
						fields: ["salary_component_abbr"],
					})
					.then((salary_components) => {
						autocompletions.push(
							...salary_components.map((d) => ({
								value: d.salary_component_abbr,
								score: 9,
								meta: __("Salary Component"),
							})),
						);

						autocompletions.push(
							...["base", "variable"].map((d) => ({
								value: d,
								score: 10,
								meta: __("Salary Structure Assignment field"),
							})),
						);

						if (child_row) {
							["condition", "formula"].forEach((field) => {
								frm.set_df_property(
									child_row.parentfield,
									"autocompletions",
									autocompletions,
									frm.doc.name,
									field,
									child_row.name,
								);
							});

							frm.refresh_field(child_row.parentfield);
						} else {
							["condition", "formula"].forEach((field) => {
								frm.set_df_property(field, "autocompletions", autocompletions);
							});
						}
					});
			},
		]);
	},
};
