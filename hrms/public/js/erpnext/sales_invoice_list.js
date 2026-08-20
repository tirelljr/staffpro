const existing_sales_invoice_listview = frappe.listview_settings["Sales Invoice"] || {};
const existing_onload = existing_sales_invoice_listview.onload;
const existing_refresh = existing_sales_invoice_listview.refresh;

function open_client_invoice() {
	frappe.new_doc("Client Invoice");
}

function set_client_invoice_primary_action(list_view) {
	if (!list_view?.page) return;

	const can_add =
		!frappe.boot?.read_only &&
		(frappe.model.can_create("Client Invoice") || list_view.can_create);

	list_view.set_primary_action = () => {
		if (can_add) {
			list_view.page.set_primary_action(__("Add Client Invoice"), open_client_invoice);
		} else {
			list_view.page.clear_primary_action();
		}
	};
	list_view.make_new_doc = open_client_invoice;
	list_view.set_primary_action();
}

frappe.listview_settings["Sales Invoice"] = Object.assign({}, existing_sales_invoice_listview, {
	onload(list_view) {
		existing_onload?.(list_view);
		set_client_invoice_primary_action(list_view);
	},
	refresh(list_view) {
		existing_refresh?.(list_view);
		list_view.set_primary_action?.();
	},
});
