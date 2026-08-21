const existing_customer_listview = frappe.listview_settings["Customer"] || {};
const existing_onload = existing_customer_listview.onload;
const existing_refresh = existing_customer_listview.refresh;

(function applyClientListLabels() {
	const messages = frappe._messages || frappe.boot?.__messages || {};
	Object.assign(messages, {
		Customer: "Client",
		Customers: "Clients",
		"Add Customer": "Add Client",
		"New Customer": "New Client",
	});
	frappe._messages = messages;
	if (frappe.boot) {
		frappe.boot.__messages = messages;
	}
})();

function set_client_list_chrome(list_view) {
	if (!list_view?.page) return;

	const title = __("Clients");
	list_view.page_title = title;
	list_view.page.set_title(title);

	const can_add =
		!frappe.boot?.read_only &&
		(frappe.model.can_create("Customer") || list_view.can_create);
	const make_new = list_view.make_new_doc?.bind(list_view);

	list_view.set_primary_action = () => {
		if (can_add && make_new) {
			list_view.page.set_primary_action(__("Add Client"), () => make_new());
		} else {
			list_view.page.clear_primary_action();
		}
	};
	list_view.set_primary_action();
}

frappe.listview_settings["Customer"] = Object.assign({}, existing_customer_listview, {
	onload(list_view) {
		existing_onload?.(list_view);
		set_client_list_chrome(list_view);
	},
	refresh(list_view) {
		existing_refresh?.(list_view);
		set_client_list_chrome(list_view);
	},
});
