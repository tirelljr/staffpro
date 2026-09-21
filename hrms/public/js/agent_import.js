// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("hrms");

hrms.open_import_agents = function () {
	const state = {
		filename: "",
		filedata: "",
		preview: null,
	};

	const dialog = new frappe.ui.Dialog({
		title: __("Import Agents"),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "body" }],
		primary_action_label: __("Import Agents"),
		primary_action() {
			confirm_import(dialog, state);
		},
	});
	dialog.$wrapper.addClass("sp-agent-import-dialog");
	dialog.get_primary_btn().prop("disabled", true);
	dialog.show();
	render_loading(dialog);

	frappe.call({
		method: "hrms.hr.agent_import.get_import_schema",
		callback(r) {
			state.schema = r.message || {};
			render_dialog(dialog, state);
		},
		error() {
			$(dialog.fields_dict.body.wrapper).html(
				`<div class="sp-agent-import"><p class="text-danger">${frappe.utils.escape_html(
					__("Could not load import columns. Stay on this page and try again."),
				)}</p></div>`,
			);
		},
	});
};

function render_loading(dialog) {
	$(dialog.fields_dict.body.wrapper).html(
		`<div class="sp-agent-import"><p class="text-muted">${frappe.utils.escape_html(__("Loading import columns..."))}</p></div>`,
	);
}

function render_dialog(dialog, state) {
	const schema = state.schema || {};
	const columns = schema.columns || [];
	const required = columns.filter((column) => column.required);
	const optional = columns.filter((column) => !column.required);
	const $body = $(dialog.fields_dict.body.wrapper);
	$body.html(`
		<div class="sp-agent-import">
			<p class="sp-agent-import__help">
				${frappe.utils.escape_html(
					__("Download the template and keep the header row. The first data row is an example — replace it with real agents. Upload the file to preview before anything is created."),
				)}
			</p>
			<div class="sp-agent-import__actions">
				<button type="button" class="btn btn-default btn-sm" data-action="download-xlsx">${frappe.utils.escape_html(__("Download Excel (.xlsx)"))}</button>
				<button type="button" class="btn btn-default btn-sm" data-action="download-csv">${frappe.utils.escape_html(__("Download CSV"))}</button>
				<button type="button" class="btn btn-default btn-sm" data-action="copy-headers">${frappe.utils.escape_html(__("Copy headers"))}</button>
				<button type="button" class="btn btn-primary btn-sm" data-action="choose-file">${frappe.utils.escape_html(__("Upload CSV or Excel"))}</button>
				<span class="sp-agent-import__file-name" data-file-name>${frappe.utils.escape_html(__("No file selected"))}</span>
				<input type="file" accept=".csv,.xlsx,.xlsm,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" hidden>
			</div>
			<p class="sp-agent-import__hint">
				${frappe.utils.escape_html(
					__("Keep Employee Number, phone, bank account, and Social Security Number as text so Excel does not change them. Dates should be YYYY-MM-DD."),
				)}
			</p>
			<div class="sp-agent-import__section">
				<div class="sp-agent-import__section-title">${frappe.utils.escape_html(__("Required column headers"))}</div>
				<div class="sp-agent-import__chips">
					${required.map((column) => chip_html(column.label, true)).join("")}
				</div>
			</div>
			<div class="sp-agent-import__section">
				<div class="sp-agent-import__section-title">${frappe.utils.escape_html(__("Optional column headers"))}</div>
				<div class="sp-agent-import__chips sp-agent-import__chips--optional">
					${optional.map((column) => chip_html(column.label, false)).join("")}
				</div>
			</div>
			<div class="sp-agent-import__preview" data-preview></div>
		</div>
	`);

	$body.find("[data-action='download-xlsx']").on("click", () => download_template("xlsx"));
	$body.find("[data-action='download-csv']").on("click", () => download_template("csv"));
	$body.find("[data-action='copy-headers']").on("click", () => copy_headers(columns));
	const $file = $body.find("input[type='file']");
	$body.find("[data-action='choose-file']").on("click", () => $file.trigger("click"));
	$file.on("change", function () {
		const file = this.files && this.files[0];
		if (!file) return;
		$body.find("[data-file-name]").text(file.name);
		read_file(file).then((filedata) => {
			state.filename = file.name;
			state.filedata = filedata;
			load_preview(dialog, state);
		});
	});
	sync_primary(dialog, state);
}

function chip_html(label, required) {
	return `<span class="sp-agent-import__chip${required ? " is-required" : ""}">${frappe.utils.escape_html(label)}</span>`;
}

function download_template(file_format) {
	open_url_post("/api/method/hrms.hr.agent_import.download_template", { file_format });
}

function copy_headers(columns) {
	const text = (columns || []).map((column) => column.label).join(",");
	if (!text) return;
	if (navigator.clipboard?.writeText) {
		navigator.clipboard.writeText(text).then(() => {
			frappe.show_alert({ message: __("Column headers copied."), indicator: "green" });
		});
		return;
	}
	frappe.msgprint(text);
}

function read_file(file) {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result);
		reader.onerror = () => reject(reader.error);
		reader.readAsDataURL(file);
	});
}

function load_preview(dialog, state) {
	const $preview = $(dialog.fields_dict.body.wrapper).find("[data-preview]");
	$preview.html(`<p class="text-muted">${frappe.utils.escape_html(__("Building preview..."))}</p>`);
	dialog.get_primary_btn().prop("disabled", true);
	frappe.call({
		method: "hrms.hr.agent_import.preview_agent_import",
		args: { filename: state.filename, filedata: state.filedata },
		freeze: true,
		freeze_message: __("Reading file..."),
		callback(r) {
			state.preview = r.message || {};
			render_preview($preview, state.preview);
			sync_primary(dialog, state);
		},
		error() {
			state.preview = null;
			$preview.html(`<p class="text-danger">${frappe.utils.escape_html(__("Could not read that file."))}</p>`);
			sync_primary(dialog, state);
		},
	});
}

function render_preview($preview, preview) {
	const rows = preview.rows || [];
	const missing = preview.missing_headers || [];
	const unknown = preview.unknown_headers || [];
	const banners = [];
	if (missing.length) {
		banners.push(
			`<div class="sp-agent-import__banner is-error">${frappe.utils.escape_html(
				__("Required headers missing: {0}", [missing.join(", ")]),
			)}</div>`,
		);
	}
	if (unknown.length) {
		banners.push(
			`<div class="sp-agent-import__banner">${frappe.utils.escape_html(
				__("These headers were ignored: {0}", [unknown.join(", ")]),
			)}</div>`,
		);
	}
	banners.push(
		`<div class="sp-agent-import__summary">${frappe.utils.escape_html(
			__("{0} rows · {1} ready · {2} with errors", [
				preview.total_count || 0,
				preview.ready_count || 0,
				preview.error_count || 0,
			]),
		)}</div>`,
	);

	const tableRows = rows
		.map((row) => {
			const previewValues = row.preview || {};
			const errors = (row.errors || []).join(" ");
			return `<tr class="${row.ok ? "" : "is-error"}">
				<td>${frappe.utils.escape_html(row.row_number)}</td>
				<td>${frappe.utils.escape_html(previewValues.first_name)}</td>
				<td>${frappe.utils.escape_html(previewValues.last_name)}</td>
				<td>${frappe.utils.escape_html(previewValues.company_email)}</td>
				<td>${frappe.utils.escape_html(previewValues.department)}</td>
				<td>${frappe.utils.escape_html(previewValues.designation)}</td>
				<td>${frappe.utils.escape_html(previewValues.grade)}</td>
				<td>${frappe.utils.escape_html(format_preview_value(previewValues.ctc))}</td>
				<td>${frappe.utils.escape_html(previewValues.status)}</td>
				<td class="sp-agent-import__status">${
					row.ok
						? `<span class="indicator-pill green">${frappe.utils.escape_html(__("Ready"))}</span>`
						: `<span class="indicator-pill red" title="${frappe.utils.escape_html(errors)}">${frappe.utils.escape_html(
								errors || __("Error"),
							)}</span>`
				}</td>
			</tr>`;
		})
		.join("");

	$preview.html(`
		${banners.join("")}
		<div class="sp-agent-import__table-wrap">
			<table class="sp-agent-import__table">
				<thead>
					<tr>
						<th>${frappe.utils.escape_html(__("Row"))}</th>
						<th>${frappe.utils.escape_html(__("First Name"))}</th>
						<th>${frappe.utils.escape_html(__("Last Name"))}</th>
						<th>${frappe.utils.escape_html(__("Company Email"))}</th>
						<th>${frappe.utils.escape_html(__("Team"))}</th>
						<th>${frappe.utils.escape_html(__("Role"))}</th>
						<th>${frappe.utils.escape_html(__("Campaign"))}</th>
						<th>${frappe.utils.escape_html(__("Agent Hourly"))}</th>
						<th>${frappe.utils.escape_html(__("Status"))}</th>
						<th>${frappe.utils.escape_html(__("Preview"))}</th>
					</tr>
				</thead>
				<tbody>${tableRows}</tbody>
			</table>
		</div>
		${
			preview.error_count
				? `<label class="sp-agent-import__skip"><input type="checkbox" data-skip-errors checked> ${frappe.utils.escape_html(
						__("Skip rows with errors and import the ready agents"),
					)}</label>`
				: ""
		}
	`);
}

function format_preview_value(value) {
	if (value === 0) return "0";
	return value == null ? "" : String(value);
}

function sync_primary(dialog, state) {
	const ready = state.preview?.ready_count || 0;
	const btn = dialog.get_primary_btn();
	btn.prop("disabled", !ready);
	btn.text(ready ? __("Import {0} Agents", [ready]) : __("Import Agents"));
}

function confirm_import(dialog, state) {
	const ready = state.preview?.ready_count || 0;
	if (!ready) {
		frappe.msgprint(__("Preview a file with at least one valid agent row first."));
		return;
	}
	const skip = $(dialog.fields_dict.body.wrapper).find("[data-skip-errors]").is(":checked") ? 1 : 0;
	if (state.preview.error_count && !skip) {
		frappe.msgprint(__("Fix the rows with errors, or skip those rows."));
		return;
	}
	frappe.confirm(__("Create {0} agent record(s)? This cannot be undone from this popup.", [ready]), () => {
		frappe.call({
			method: "hrms.hr.agent_import.import_agents",
			args: {
				filename: state.filename,
				filedata: state.filedata,
				skip_errors: skip,
			},
			freeze: true,
			freeze_message: __("Creating agents..."),
			callback(r) {
				const result = r.message || {};
				dialog.hide();
				frappe.show_alert({
					message: __("Imported {0} agent(s).", [result.created_count || 0]),
					indicator: "green",
				});
				if (result.failed_count || result.skipped_count) {
					frappe.msgprint({
						title: __("Import finished"),
						message: __("Created {0}. Skipped {1}. Failed {2}.", [
							result.created_count || 0,
							result.skipped_count || 0,
							result.failed_count || 0,
						]),
						indicator: result.failed_count ? "orange" : "green",
					});
				}
			},
		});
	});
}
