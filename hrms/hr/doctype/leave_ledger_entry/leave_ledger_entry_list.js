frappe.listview_settings["Leave Ledger Entry"] = {
	onload: function (listview) {
		if (typeof listview.can_cancel === "function") {
			listview.can_cancel = () => false;
		}
		if (listview.page.fields_dict.transaction_type) {
			listview.page.fields_dict.transaction_type.get_query = function () {
				return {
					filters: {
						name: [
							"in",
							["Leave Allocation", "Leave Application", "Leave Encashment"],
						],
					},
				};
			};
		}
	},
};
