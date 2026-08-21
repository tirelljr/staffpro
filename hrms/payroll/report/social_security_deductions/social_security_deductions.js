// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Social Security Deductions"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "period",
			label: __("Period"),
			fieldtype: "Select",
			options: ["This Week", "This Month", "This Year", "Custom"],
			default: "This Month",
			on_change: function () {
				set_period_dates();
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
		},
		{
			fieldname: "employee",
			label: __("Agent"),
			fieldtype: "Link",
			options: "Employee",
			get_query: function () {
				const company = frappe.query_report.get_filter_value("company");
				return company ? { filters: { company } } : {};
			},
		},
		{
			fieldname: "ss_number",
			label: __("Social Security Number"),
			fieldtype: "Data",
		},
	],
	onload: function (report) {
		set_period_dates();
		mount_ss_report_actions(report);
	},
};

function set_period_dates() {
	const period = frappe.query_report.get_filter_value("period") || "This Month";
	if (period === "Custom") return;

	const today = frappe.datetime.get_today();
	let from_date = frappe.datetime.month_start();
	let to_date = today;

	if (period === "This Week") {
		from_date = monday_of_week(today);
	} else if (period === "This Year") {
		from_date = frappe.datetime.year_start();
	}

	frappe.query_report.set_filter_value("from_date", from_date);
	frappe.query_report.set_filter_value("to_date", to_date);
}

function monday_of_week(date_str) {
	const date = frappe.datetime.str_to_obj(date_str);
	const day = date.getDay();
	const offset = day === 0 ? -6 : 1 - day;
	return frappe.datetime.add_days(date_str, offset);
}

const SS_EXPORT_FORMATS = ["CSV", "PDF", "ZIP"];
const SS_EXPORT_STORAGE_KEY = "staff-pro-ss-deductions-export-format";

function mount_ss_report_actions(report) {
	inject_ss_report_chrome_css();
	hide_ss_report_menus(report);

	const page = report?.page;
	const $host = page?.custom_actions?.length
		? page.custom_actions
		: page?.wrapper?.find(".custom-actions").first();
	if (!$host?.length || $host.find(".sp-ss-actions").length) return;

	const selected = get_saved_export_format();
	const $wrap = $(ss_report_actions_html(selected));
	$host.removeClass("hidden hide").prepend($wrap);
	bind_export_dropdown($wrap.find(".sp-report-export"));
	$wrap.find(".sp-ss-push-btn").on("click", (event) => {
		event.preventDefault();
		push_to_social_security();
	});
}

function inject_ss_report_chrome_css() {
	if (document.getElementById("staff-pro-ss-report-css")) return;
	const style = document.createElement("style");
	style.id = "staff-pro-ss-report-css";
	style.textContent = `
		#page-query-report:has(.sp-ss-actions) .inner-group-button,
		#page-query-report:has(.sp-ss-actions) .menu-btn-group {
			display: none !important;
		}
		#page-query-report:has(.sp-ss-actions) .page-icon-group {
			display: inline-flex !important;
		}
	`;
	document.head.appendChild(style);
}

function hide_ss_report_menus(report) {
	const $wrapper = report?.page?.wrapper;
	if (!$wrapper?.length) return;

	const apply = () => {
		$wrapper.find(".inner-group-button, .menu-btn-group").addClass("hidden").hide();
		$wrapper.find(".page-icon-group").removeClass("hidden").css("display", "");
		report?.refresh_button?.show?.();
	};
	apply();
	if (report._staff_pro_ss_chrome) return;
	report._staff_pro_ss_chrome = true;
	const head = $wrapper.find(".page-head").get(0);
	if (!head || typeof MutationObserver === "undefined") return;
	const observer = new MutationObserver(apply);
	observer.observe(head, { childList: true, subtree: true });
}

function ss_report_actions_html(selected) {
	return `<div class="sp-ss-actions">
		${export_dropdown_html(selected)}
		<button type="button" class="sp-ss-push-btn">
			<img src="/assets/hrms/images/belize-ssb-logo.png" alt="" class="sp-ss-push-btn__logo">
			<span>${frappe.utils.escape_html(__("Push to Social Security"))}</span>
		</button>
	</div>`;
}

function export_dropdown_html(selected) {
	const items = SS_EXPORT_FORMATS.map((format) => {
		const is_selected = format === selected;
		return `<button type="button" class="sp-report-export__item${
			is_selected ? " is-selected" : ""
		}" role="menuitem" data-format="${format}" aria-checked="${is_selected}">
			${file_format_icon(format)}
			<span class="sp-report-export__label">${frappe.utils.escape_html(__(format))}</span>
			<span class="sp-report-export__check" aria-hidden="true">${check_icon()}</span>
		</button>`;
	}).join("");

	return `<div class="sp-report-export">
		<button type="button" class="sp-report-export__btn" aria-expanded="false" aria-haspopup="menu">
			<span>${frappe.utils.escape_html(__("Export"))}</span>
			${caret_icon()}
		</button>
		<div class="sp-report-export__menu" role="menu" hidden>
			<div class="sp-report-export__heading">${frappe.utils.escape_html(__("Export Format"))}</div>
			${items}
		</div>
	</div>`;
}

function bind_export_dropdown($wrap) {
	const $btn = $wrap.find(".sp-report-export__btn");
	const $menu = $wrap.find(".sp-report-export__menu");

	const close = () => {
		$wrap.removeClass("is-open");
		$btn.attr("aria-expanded", "false");
		$menu.attr("hidden", true);
	};

	const open = () => {
		$wrap.addClass("is-open");
		$btn.attr("aria-expanded", "true");
		$menu.removeAttr("hidden");
	};

	$btn.on("click", (event) => {
		event.preventDefault();
		event.stopPropagation();
		if ($wrap.hasClass("is-open")) close();
		else open();
	});

	$wrap.on("click", ".sp-report-export__item", (event) => {
		event.preventDefault();
		event.stopPropagation();
		const format = $(event.currentTarget).data("format");
		if (!format) return;
		set_selected_export_format($wrap, format);
		close();
		export_ss_deductions(format);
	});

	$(document)
		.off("click.ss-export-dropdown")
		.on("click.ss-export-dropdown", (event) => {
			if (!$wrap.hasClass("is-open")) return;
			if (!$.contains($wrap.get(0), event.target)) close();
		});

	$(document)
		.off("keydown.ss-export-dropdown")
		.on("keydown.ss-export-dropdown", (event) => {
			if (event.key === "Escape") close();
		});
}

function set_selected_export_format($wrap, format) {
	try {
		localStorage.setItem(SS_EXPORT_STORAGE_KEY, format);
	} catch (e) {
		/* ignore quota / private mode */
	}
	$wrap.find(".sp-report-export__item").each(function () {
		const is_selected = $(this).data("format") === format;
		$(this).toggleClass("is-selected", is_selected).attr("aria-checked", is_selected);
	});
}

function get_saved_export_format() {
	try {
		const saved = localStorage.getItem(SS_EXPORT_STORAGE_KEY);
		if (SS_EXPORT_FORMATS.includes(saved)) return saved;
	} catch (e) {
		/* ignore */
	}
	return "CSV";
}

function export_ss_deductions(format) {
	const report = frappe.query_report;
	if (!report) return;

	if (format === "PDF") {
		export_ss_pdf(report);
		return;
	}
	if (format === "ZIP") {
		export_ss_zip(report);
		return;
	}
	export_ss_query(report, "CSV");
}

function ensure_report_has_data(report) {
	if (typeof report.get_validated_visible_indexes === "function") {
		report.get_validated_visible_indexes();
		return;
	}
	if (!report.data?.length) {
		frappe.throw({
			title: __("No data to perform this action"),
			message: __("Please adjust filters to include some data"),
		});
	}
}

function export_ss_query(report, file_format) {
	ensure_report_has_data(report);
	report.make_access_log?.("Export", file_format);

	const filters = report.get_filter_values(true);
	const args = {
		cmd: "frappe.desk.query_report.export_query",
		report_name: report.report_name,
		custom_columns: report.custom_columns?.length ? report.custom_columns : [],
		file_format_type: file_format,
		filters,
		applied_filters: report.get_applied_filters?.(filters) || {},
		include_filters: 1,
	};
	open_url_post(frappe.request.url, args);
}

function export_ss_pdf(report) {
	ensure_report_has_data(report);
	const print_settings = {
		with_letter_head: 1,
		orientation: "Landscape",
		letter_head: report.report_doc?.letter_head || report.report_doc?.default_letter_head,
		include_filters: 1,
	};
	report.pdf_report(print_settings);
}

function export_ss_zip(report) {
	ensure_report_has_data(report);
	const filters = report.get_filter_values(true);
	open_url_post(
		"/api/method/hrms.payroll.report.social_security_deductions.social_security_deductions.download_zip",
		{ filters: JSON.stringify(filters) },
	);
}

function push_to_social_security() {
	const report = frappe.query_report;
	if (!report) return;
	ensure_report_has_data(report);

	const summary = ss_push_summary(report);
	const filters = report.get_filter_values(true);
	const from_date = frappe.datetime.str_to_user(filters.from_date);
	const to_date = frappe.datetime.str_to_user(filters.to_date);
	const total = format_ss_currency(summary.total, report);

	frappe.confirm(
		__(
			"Push {0} Social Security deduction row(s) totaling {1} for {2} to {3}? This prepares the SSB filing package.",
			[summary.count, total, from_date, to_date],
		),
		() => {
			export_ss_zip(report);
			frappe.show_alert({
				message: __("Social Security filing package downloaded."),
				indicator: "green",
			});
		},
	);
}

function ss_push_summary(report) {
	const rows = (report.data || []).filter((row) => !row.is_total_row);
	let total = 0;
	for (const row of rows) {
		total += flt(row.total);
	}
	return { count: rows.length, total };
}

function format_ss_currency(amount, report) {
	const currency =
		report.data?.find((row) => row.currency)?.currency ||
		frappe.defaults.get_default("currency") ||
		"BZD";
	return format_currency(amount, currency);
}

function file_format_icon(format) {
	return `<span class="sp-report-export__file" aria-hidden="true">
		<svg viewBox="0 0 24 24" fill="none">
			<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
			<path d="M14 3v5h5" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
		</svg>
		<span>${frappe.utils.escape_html(format)}</span>
	</span>`;
}

function caret_icon() {
	return `<svg class="sp-report-export__caret" width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
		<path d="m6 9 6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
	</svg>`;
}

function check_icon() {
	return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none">
		<path d="M20 6 9 17l-5-5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
	</svg>`;
}
