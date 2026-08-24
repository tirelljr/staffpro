// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("hrms");

const INVOICE_EXPORT_FORMATS = ["CSV", "PDF", "ZIP"];
let invoice_export_uid = 0;

hrms.mount_invoice_export = function (opts) {
	const page = opts.page;
	const $host = page?.custom_actions?.length
		? page.custom_actions
		: page?.wrapper?.find(".custom-actions").first();
	if (!$host?.length) return null;

	$host.removeClass("hidden hide");
	let $wrap = $host.find(`.sp-invoice-export[data-export-key="${opts.storage_key}"]`);
	if (!$wrap.length) {
		const selected = get_saved_invoice_export_format(
			opts.storage_key,
			opts.formats,
			opts.default_format,
		);
		$wrap = $(invoice_export_html(selected, opts));
		$host.prepend($wrap);
		bind_invoice_export_dropdown($wrap, opts);
	}

	sync_invoice_export_visibility($wrap, opts);
	return $wrap;
};

hrms.mount_invoice_list_export = function (listview, opts) {
	if (!can_export_invoices(opts.doctype)) return;

	const settings = Object.assign(
		{
			page: listview.page,
			get_names: () => selected_invoice_names(listview),
			min_selected: 1,
			always_visible: false,
			formats: INVOICE_EXPORT_FORMATS,
		},
		opts,
	);

	const sync = () => hrms.mount_invoice_export(settings);
	if (!listview._sp_invoice_export_bound) {
		listview._sp_invoice_export_bound = true;
		const original = listview.on_row_checked;
		listview.on_row_checked = function () {
			if (typeof original === "function") {
				original.apply(this, arguments);
			}
			sync();
		};
		listview.page?.wrapper?.on(
			"change.sp-invoice-export",
			".list-row-checkbox, .list-check-all",
			sync,
		);
	}
	sync();
};

hrms.mount_invoice_form_export = function (frm, opts) {
	if (!can_export_invoices(opts.doctype)) return;
	if (frm.is_new() || !frm.doc?.name) {
		frm.page?.wrapper?.find(`.sp-invoice-export[data-export-key="${opts.storage_key}"]`).attr("hidden", true);
		return;
	}

	hrms.mount_invoice_export(
		Object.assign(
			{
				page: frm.page,
				get_names: () => [frm.doc.name],
				min_selected: 1,
				always_visible: true,
				formats: ["CSV", "PDF"],
			},
			opts,
		),
	);
};

function can_export_invoices(doctype) {
	return frappe.perm.has_perm(doctype, 0, "export") || frappe.perm.has_perm(doctype, 0, "print");
}

function selected_invoice_names(listview) {
	return (listview.get_checked_items?.() || []).map((row) => row.name).filter(Boolean);
}

function sync_invoice_export_visibility($wrap, opts) {
	if (!$wrap?.length) return;
	if (opts.always_visible) {
		$wrap.removeAttr("hidden");
		return;
	}
	const count = (opts.get_names?.() || []).length;
	if (count >= (opts.min_selected || 1)) {
		$wrap.removeAttr("hidden");
	} else {
		$wrap.attr("hidden", true);
		close_invoice_export($wrap);
	}
}

function invoice_export_html(selected, opts) {
	const formats = opts.formats || INVOICE_EXPORT_FORMATS;
	const items = formats
		.map((format) => {
			const is_selected = format === selected;
			return `<button type="button" class="sp-report-export__item${
				is_selected ? " is-selected" : ""
			}" role="menuitem" data-format="${format}" aria-checked="${is_selected}" title="${frappe.utils.escape_html(
				invoice_export_title(format, opts.label),
			)}">
			${invoice_file_icon(format)}
			<span class="sp-report-export__label">${frappe.utils.escape_html(__(format))}</span>
			<span class="sp-report-export__check" aria-hidden="true">${invoice_check_icon()}</span>
		</button>`;
		})
		.join("");

	return `<div class="sp-invoice-export" data-export-key="${frappe.utils.escape_html(opts.storage_key)}" hidden>
		<div class="sp-report-export">
			<button type="button" class="sp-report-export__btn" aria-expanded="false" aria-haspopup="menu">
				<span>${frappe.utils.escape_html(__("Export"))}</span>
				${invoice_caret_icon()}
			</button>
			<div class="sp-report-export__menu" role="menu" hidden>
				<div class="sp-report-export__heading">${frappe.utils.escape_html(__("Export Format"))}</div>
				${items}
			</div>
		</div>
	</div>`;
}

function invoice_export_title(format, label) {
	if (format === "ZIP") {
		return __("Select more than one {0}, then export one CSV each", [label]);
	}
	return __("Export the {0} as {1}", [label, format]);
}

function bind_invoice_export_dropdown($wrap, opts) {
	const $dropdown = $wrap.find(".sp-report-export");
	const $btn = $dropdown.find(".sp-report-export__btn");
	const $menu = $dropdown.find(".sp-report-export__menu");
	const ns = `.sp-inv-export-${++invoice_export_uid}`;

	$btn.on("click", (event) => {
		event.preventDefault();
		event.stopPropagation();
		if ($dropdown.hasClass("is-open")) close_invoice_export($wrap);
		else open_invoice_export($wrap);
	});

	$wrap.on("click", ".sp-report-export__item", (event) => {
		event.preventDefault();
		event.stopPropagation();
		const format = $(event.currentTarget).data("format");
		if (!format) return;
		set_selected_invoice_export_format($wrap, opts.storage_key, format);
		close_invoice_export($wrap);
		export_invoices(format, opts);
	});

	$(document).on(`click${ns}`, (event) => {
		if (!$dropdown.hasClass("is-open")) return;
		if (!$.contains($wrap.get(0), event.target)) close_invoice_export($wrap);
	});

	$(document).on(`keydown${ns}`, (event) => {
		if (event.key === "Escape") close_invoice_export($wrap);
	});
}

function open_invoice_export($wrap) {
	const $dropdown = $wrap.find(".sp-report-export");
	$dropdown.addClass("is-open");
	$dropdown.find(".sp-report-export__btn").attr("aria-expanded", "true");
	$dropdown.find(".sp-report-export__menu").removeAttr("hidden");
}

function close_invoice_export($wrap) {
	const $dropdown = $wrap.find(".sp-report-export");
	$dropdown.removeClass("is-open");
	$dropdown.find(".sp-report-export__btn").attr("aria-expanded", "false");
	$dropdown.find(".sp-report-export__menu").attr("hidden", true);
}

function set_selected_invoice_export_format($wrap, storage_key, format) {
	try {
		localStorage.setItem(storage_key, format);
	} catch (e) {
		/* ignore quota / private mode */
	}
	$wrap.find(".sp-report-export__item").each(function () {
		const is_selected = $(this).data("format") === format;
		$(this).toggleClass("is-selected", is_selected).attr("aria-checked", is_selected);
	});
}

function get_saved_invoice_export_format(storage_key, formats, default_format) {
	const allowed = formats || INVOICE_EXPORT_FORMATS;
	try {
		const saved = localStorage.getItem(storage_key);
		if (allowed.includes(saved)) return saved;
	} catch (e) {
		/* ignore */
	}
	if (default_format && allowed.includes(default_format)) return default_format;
	return allowed[0] || "CSV";
}

function export_invoices(format, opts) {
	const names = opts.get_names?.() || [];
	if (names.length < (opts.min_selected || 1)) {
		frappe.throw({
			title: __("Select {0}", [opts.label]),
			message: __("Select at least {0} {1} to export.", [
				opts.min_selected || 1,
				opts.label,
			]),
		});
	}
	if (format === "ZIP" && names.length < 2) {
		frappe.throw({
			title: __("Select {0}", [opts.label]),
			message: __("Select more than one {0} to export a ZIP of CSV files.", [opts.label]),
		});
	}

	const method = format === "PDF" ? "download_pdf" : format === "ZIP" ? "download_zip" : "download_csv";
	post_invoice_download(
		method,
		opts.doctype,
		names,
		default_invoice_filename(opts.file_stem, format),
		opts.method_prefix,
	);
}

function default_invoice_filename(stem, format) {
	if (format === "PDF") return `${stem}.pdf`;
	if (format === "ZIP") return `${stem}.zip`;
	return `${stem}.csv`;
}

function post_invoice_download(method, doctype, names, filename_fallback, method_prefix) {
	const endpoint = method_prefix || "hrms.payroll.invoice_export";
	frappe.dom.freeze(__("Downloading {0}...", [filename_fallback]));
	fetch(`/api/method/${endpoint}.${method}`, {
		method: "POST",
		credentials: "same-origin",
		headers: {
			"X-Frappe-CSRF-Token": frappe.csrf_token,
			"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
		},
		body: new URLSearchParams({
			doctype,
			names: JSON.stringify(names),
		}),
	})
		.then(async (response) => {
			const content_type = response.headers.get("Content-Type") || "";
			const blob = await response.blob();
			if (!response.ok || is_invoice_error_response(content_type, blob.type)) {
				throw new Error(await invoice_error_from_blob(blob));
			}
			trigger_invoice_blob_download(blob, filename_from_invoice_response(response, filename_fallback));
		})
		.catch((error) => {
			frappe.msgprint({
				title: __("Export failed"),
				indicator: "red",
				message: error.message || __("Could not download the file."),
			});
		})
		.finally(() => frappe.dom.unfreeze());
}

function is_invoice_error_response(content_type, blob_type) {
	const type = `${content_type} ${blob_type}`.toLowerCase();
	return type.includes("text/html") || type.includes("application/json");
}

async function invoice_error_from_blob(blob) {
	const fallback = __("Could not download the file.");
	try {
		const text = await blob.text();
		const json = JSON.parse(text);
		if (json._server_messages) {
			const messages = JSON.parse(json._server_messages).map((row) => {
				try {
					return JSON.parse(row).message || row;
				} catch (e) {
					return row;
				}
			});
			return messages.filter(Boolean).join("<br>") || fallback;
		}
		return json.exception || json.message || fallback;
	} catch (e) {
		return fallback;
	}
}

function filename_from_invoice_response(response, fallback) {
	const disposition = response.headers.get("Content-Disposition") || "";
	const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
	if (!match) return fallback;
	return decodeURIComponent(match[1] || match[2]);
}

function trigger_invoice_blob_download(blob, filename) {
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.href = url;
	link.download = filename;
	document.body.appendChild(link);
	link.click();
	link.remove();
	setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function invoice_file_icon(format) {
	return `<span class="sp-report-export__file" aria-hidden="true">
		<svg viewBox="0 0 24 24" fill="none">
			<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
			<path d="M14 3v5h5" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
		</svg>
		<span>${frappe.utils.escape_html(format)}</span>
	</span>`;
}

function invoice_caret_icon() {
	return `<svg class="sp-report-export__caret" width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
		<path d="m6 9 6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
	</svg>`;
}

function invoice_check_icon() {
	return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none">
		<path d="M20 6 9 17l-5-5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
	</svg>`;
}
