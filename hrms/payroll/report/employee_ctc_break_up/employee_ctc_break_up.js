// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Employee CTC Break-up"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			reqd: 1,
			get_query: function () {
				let company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						company: company,
					},
				};
			},
			on_change: function () {
				let employee = frappe.query_report.get_filter_value("employee");
				frappe.query_report.set_filter_value("salary_structure_assignment", "");
				if (!employee) return;
				frappe.db
					.get_list("Salary Structure Assignment", {
						filters: { employee: employee, docstatus: 1 },
						fields: ["name"],
						order_by: "from_date desc",
						limit: 1,
					})
					.then(function (result) {
						if (frappe.query_report.get_filter_value("salary_structure_assignment"))
							return;
						frappe.query_report.set_filter_value(
							"salary_structure_assignment",
							(result[0] && result[0].name) || "",
						);
					});
			},
		},
		{
			fieldname: "salary_structure_assignment",
			label: __("Salary Structure Assignment"),
			fieldtype: "Link",
			options: "Salary Structure Assignment",
			reqd: 1,
			get_query: function () {
				let employee = frappe.query_report.get_filter_value("employee");
				if (!employee) return;
				return {
					filters: {
						employee: employee,
						docstatus: 1,
					},
					order_by: "from_date desc",
				};
			},
		},
	],
	onload: async function (report) {
		mount_hourly_breakdown_actions(report);

		if (report.get_filter_value("employee")) return;

		const employee = await hrms.get_current_employee();
		if (!employee) return;
		report.set_filter_value("employee", employee);
	},
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data?.bold && value) value = `<strong>${value}</strong>`;
		if (column.fieldname == "type" && value) {
			let indicator_color = value === "Fixed" ? "blue" : "orange";
			value = `<span class="indicator-pill no-indicator-dot ${indicator_color}">${value}</span>`;
		}
		return value;
	},
};

function mount_hourly_breakdown_actions(report) {
	inject_hourly_breakdown_chrome_css();
	hide_hourly_breakdown_menus(report);

	const page = report?.page;
	let $host = page?.custom_actions?.length
		? page.custom_actions
		: page?.wrapper?.find(".custom-actions").first();
	if (!$host?.length) {
		$host = page?.wrapper?.find(".page-head-content .page-actions").first();
	}
	if (!$host?.length || $host.find(".sp-hourly-actions").length) return;

	const $wrap = $(hourly_breakdown_actions_html());
	$host.removeClass("hidden hide").prepend($wrap);
	$wrap.find(".sp-hourly-print").on("click", (event) => {
		event.preventDefault();
		if (typeof report.print_report === "function") {
			report.print_report();
		}
	});
	$wrap.find(".sp-hourly-export").on("click", (event) => {
		event.preventDefault();
		if (typeof report.export_report === "function") {
			report.export_report();
		}
	});
}

function hourly_breakdown_actions_html() {
	return `<div class="sp-hourly-actions">
		<button type="button" class="sp-report-action-btn sp-hourly-print">${frappe.utils.escape_html(
			__("Print"),
		)}</button>
		<button type="button" class="sp-report-action-btn sp-hourly-export">${frappe.utils.escape_html(
			__("Export"),
		)}</button>
	</div>`;
}

function inject_hourly_breakdown_chrome_css() {
	if (document.getElementById("staff-pro-hourly-breakdown-css")) return;
	const style = document.createElement("style");
	style.id = "staff-pro-hourly-breakdown-css";
	style.textContent = `
		#page-query-report:has(.sp-hourly-actions) .inner-group-button,
		#page-query-report:has(.sp-hourly-actions) .menu-btn-group,
		#page-query-report:has(.sp-hourly-actions) .menu-more-button {
			display: none !important;
		}
		#page-query-report:has(.sp-hourly-actions) .page-icon-group {
			display: none !important;
		}
	`;
	document.head.appendChild(style);
}

function hide_hourly_breakdown_menus(report) {
	const $wrapper = report?.page?.wrapper;
	if (!$wrapper?.length) return;

	const apply = () => {
		$wrapper.find(".inner-group-button, .menu-btn-group, .menu-more-button").addClass("hidden").hide();
		$wrapper.find(".page-icon-group").addClass("hidden").hide();
		report?.refresh_button?.show?.();
	};
	apply();
	if (report._staff_pro_hourly_chrome) return;
	report._staff_pro_hourly_chrome = true;
	const head = $wrapper.find(".page-head").get(0);
	if (!head || typeof MutationObserver === "undefined") return;
	const observer = new MutationObserver(apply);
	observer.observe(head, { childList: true, subtree: true });
}
