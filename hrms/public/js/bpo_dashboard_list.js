frappe.provide("hrms.desk");

const BPO_CHART_MODULES = ["HR", "Payroll"];

function apply_bpo_chart_module_filter(listview) {
	if (!listview?.filter_area) {
		return;
	}
	const has_module = (listview.filter_area.get() || []).some((filter) => filter[1] === "module");
	if (has_module) {
		return;
	}
	listview.filter_area.add([[listview.doctype, "module", "in", BPO_CHART_MODULES]]);
}

["Dashboard Chart", "Number Card", "Dashboard"].forEach((doctype) => {
	const existing = frappe.listview_settings[doctype] || {};
	frappe.listview_settings[doctype] = Object.assign({}, existing, {
		onload(listview) {
			if (typeof existing.onload === "function") {
				existing.onload(listview);
			}
			apply_bpo_chart_module_filter(listview);
		},
	});
});
