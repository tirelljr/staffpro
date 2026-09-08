frappe.listview_settings["Additional Salary"] = {
	hide_name_column: true,
	onload(listview) {
		const title = __("Bonuses");
		listview.page_title = title;
		listview.page.set_title(title);
	},
	refresh(listview) {
		listview.page.set_title(__("Bonuses"));
		listview.page.wrapper
			.find("button")
			.filter(function () {
				return ($(this).text() || "").trim() === __("Templates");
			})
			.hide();
	},
};
