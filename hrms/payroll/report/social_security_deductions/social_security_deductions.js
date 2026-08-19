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
			fieldname: "employee_group",
			label: __("Team Group"),
			fieldtype: "Link",
			options: "Employee Group",
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
	onload: function () {
		set_period_dates();
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
