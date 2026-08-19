// Copyright (c) 2026, Staff Pro BPO and contributors
// For license information, please see license.txt

frappe.query_reports["Social Security Contributions"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			on_change: function () {
				// optional filter — blank means all employers
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
		},
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: [
				{ value: 1, label: __("Jan") },
				{ value: 2, label: __("Feb") },
				{ value: 3, label: __("Mar") },
				{ value: 4, label: __("Apr") },
				{ value: 5, label: __("May") },
				{ value: 6, label: __("June") },
				{ value: 7, label: __("July") },
				{ value: 8, label: __("Aug") },
				{ value: 9, label: __("Sep") },
				{ value: 10, label: __("Oct") },
				{ value: 11, label: __("Nov") },
				{ value: 12, label: __("Dec") },
			],
			default: frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 1,
			on_change: function () {
				set_dates_from_month_year();
			},
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Select",
			on_change: function () {
				set_dates_from_month_year();
			},
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			get_query: function () {
				let company = frappe.query_report.get_filter_value("company");
				return company ? { filters: { company: company } } : {};
			},
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
	],

	onload: function (report) {
		frappe.call({
			method:
				"hrms.payroll.report.social_security_contributions.social_security_contributions.get_years",
			callback: function (r) {
				let year_filter = frappe.query_report.get_filter("year");
				year_filter.df.options = r.message;
				year_filter.df.default = r.message.split("\n")[0];
				year_filter.refresh();
				year_filter.set_input(year_filter.df.default);
			},
		});

		report.page.add_inner_button(__("Download Excel"), () => {
			download_report_file("download_excel");
		});

		report.page.add_inner_button(__("Download PDF"), () => {
			download_report_file("download_pdf");
		});
	},
};

function set_dates_from_month_year() {
	let month = frappe.query_report.get_filter_value("month");
	let year = frappe.query_report.get_filter_value("year");
	if (!month || !year) return;

	let start = `${year}-${String(month).padStart(2, "0")}-01`;
	frappe.query_report.set_filter_value("from_date", start);
	frappe.query_report.set_filter_value("to_date", frappe.datetime.month_end(start));
}

function download_report_file(method_name) {
	let filters = frappe.query_report.get_filter_values();
	open_url_post(
		`/api/method/hrms.payroll.report.social_security_contributions.social_security_contributions.${method_name}`,
		{ filters: JSON.stringify(filters) }
	);
}
