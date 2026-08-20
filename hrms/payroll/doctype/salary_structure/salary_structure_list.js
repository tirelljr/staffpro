frappe.listview_settings["Salary Structure"] = {
	formatters: {
		payroll_frequency: function (value) {
			return hrms.payroll_frequency_label ? hrms.payroll_frequency_label(value) : __(value);
		},
	},
	onload: function (list_view) {
		list_view.page.add_inner_button(__("Bulk Salary Structure Assignment"), function () {
			frappe.set_route("Form", "Bulk Salary Structure Assignment");
		});
	},
};
