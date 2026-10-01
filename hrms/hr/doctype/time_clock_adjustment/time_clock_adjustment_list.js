frappe.listview_settings["Time Clock Adjustment"] = {
	onload(listview) {
		listview.page.clear_primary_action();
		frappe.set_route("time-clock-adjustments");
	},
};
