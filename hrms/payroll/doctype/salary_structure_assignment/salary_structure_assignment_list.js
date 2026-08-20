// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Salary Structure Assignment"] = {
	onload(listview) {
		hide_salary_structure_assignment_list_chrome(listview);
	},
	refresh(listview) {
		hide_salary_structure_assignment_list_chrome(listview);
	},
};

function hide_salary_structure_assignment_list_chrome(listview) {
	const page = listview?.page;
	if (!page) return;
	if (typeof page.hide_menu === "function") {
		page.hide_menu();
	}
	page.menu_btn_group?.addClass("hidden hide").hide();
	page.wrapper?.find(".menu-btn-group, .view-switcher").addClass("hidden hide").hide();
}
