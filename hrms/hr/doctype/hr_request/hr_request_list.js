frappe.listview_settings["HR Request"] = {
	add_fields: ["status", "priority", "request_type", "assigned_to"],
	filters: [["status", "not in", ["Resolved", "Rejected", "Cancelled"]]],
	has_indicator_for_draft: 1,
	get_indicator: function (doc) {
		const colors = {
			Open: "orange",
			"In Progress": "blue",
			"Waiting on Employee": "yellow",
			Resolved: "green",
			Rejected: "red",
			Cancelled: "gray",
		};
		return [__(doc.status), colors[doc.status] || "gray", "status,=," + doc.status];
	},
	onload: function (listview) {
		const apply = (filters) => {
			listview.filter_area.clear();
			filters.forEach((filter) => listview.filter_area.add(filter));
			listview.refresh();
		};

		listview.page.add_inner_button(__("Open"), () => {
			apply([["HR Request", "status", "=", "Open"]]);
		});
		listview.page.add_inner_button(__("Unassigned"), () => {
			apply([
				["HR Request", "assigned_to", "=", ""],
				["HR Request", "status", "not in", ["Resolved", "Rejected", "Cancelled"]],
			]);
		});
		listview.page.add_inner_button(__("Job Letter"), () => {
			apply([["HR Request", "request_type", "=", "Job Letter"]]);
		});
		listview.page.add_inner_button(__("My Tickets"), () => {
			apply([["HR Request", "assigned_to", "=", frappe.session.user]]);
		});
	},
};
