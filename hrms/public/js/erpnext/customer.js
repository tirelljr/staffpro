(function applyClientUiLabels() {
	const messages = frappe._messages || frappe.boot?.__messages || {};
	Object.assign(messages, {
		Customer: "Client",
		Customers: "Clients",
		"Add Customer": "Add Client",
		"New Customer": "New Client",
		"Customer Name": "Client Name",
		"Customer Type": "Client Type",
		"Customer Group": "Client Group",
	});
	frappe._messages = messages;
	if (frappe.boot) {
		frappe.boot.__messages = messages;
	}
})();

frappe.ui.form.on("Customer", {
	onload(frm) {
		apply_bpo_customer_layout(frm);
	},

	refresh(frm) {
		apply_bpo_customer_layout(frm);
		strip_erpnext_customer_actions(frm);
		add_client_invoice_action(frm);
		setTimeout(() => apply_bpo_customer_layout(frm), 150);
		setTimeout(() => strip_erpnext_customer_actions(frm), 150);
	},
});

const HIDDEN_CUSTOMER_FIELDS = [
	"naming_series",
	"salutation",
	"gender",
	"default_bank_account",
	"lead_name",
	"opportunity_name",
	"prospect_name",
	"tax_id",
	"tax_category",
	"tax_withholding_category",
	"default_price_list",
	"customer_pos_id",
	"is_internal_customer",
	"represents_company",
	"market_segment",
	"industry",
	"website",
	"language",
	"territory",
	"default_sales_partner",
	"default_commission_rate",
	"sales_team",
	"loyalty_program",
	"loyalty_program_tier",
	"portal_users",
	"so_required",
	"dn_required",
	"is_frozen",
	"companies",
	"credit_limits",
	"tax_tab",
	"sales_team_tab",
	"settings_tab",
	"portal_users_tab",
	"more_info",
	"more_info_tab",
];

const CUSTOMER_LABELS = {
	customer_name: "Client Name",
	customer_type: "Client Type",
	customer_group: "Client Group",
	account_manager: "Account Manager",
	customer_details: "Notes",
	customer_primary_contact: "Primary Contact",
	customer_primary_address: "Primary Address",
	payment_terms: "Payment Terms",
	default_currency: "Currency",
	default_billing_rate: "Hourly Billing Rate",
	alias: "Short Name",
};

const HIDDEN_CUSTOMER_TABS = ["Tax", "Sales Team", "Portal Users", "Settings", "More Info"];

function apply_bpo_customer_layout(frm) {
	HIDDEN_CUSTOMER_FIELDS.forEach((fieldname) => {
		if (frm.fields_dict[fieldname]) {
			frm.set_df_property(fieldname, "hidden", 1);
		}
	});

	Object.entries(CUSTOMER_LABELS).forEach(([fieldname, label]) => {
		if (frm.fields_dict[fieldname]) {
			frm.set_df_property(fieldname, "label", __(label));
		}
	});

	hide_customer_tabs(frm);
	relabel_customer_page(frm);
}

function hide_customer_tabs(frm) {
	const $nav = $(frm.page.wrapper).find("#form-tabs");
	$nav.find("li, .nav-item").each(function () {
		const label = ($(this).text() || "").replace(/\s+/g, " ").trim();
		if (HIDDEN_CUSTOMER_TABS.includes(label)) {
			$(this).hide();
		}
	});
}

function relabel_customer_page(frm) {
	const title = frm.is_new() ? __("New Client") : frm.doc.customer_name || frm.doc.name || __("Client");
	frm.page.set_title(title);

	const $head = frm.page.wrapper.find(".page-head");
	$head.find(".title-text, h3, .ellipsis, .breadcrumb-item, .page-title").each(function () {
		const $el = $(this);
		const text = ($el.text() || "").trim();
		if (!text) return;
		if (text === "Customer" || text === __("Customer")) {
			$el.text(__("Client"));
		} else if (text === "New Customer" || text.startsWith("New Customer")) {
			$el.text(text.replace("New Customer", __("New Client")));
		}
	});
}

function strip_erpnext_customer_actions(frm) {
	["Quotation", "Sales Order", "Opportunity", "Subscription", "Payment Request"].forEach((label) => {
		frm.remove_custom_button(__(label), __("Create"));
	});
}

function add_client_invoice_action(frm) {
	if (frm.is_new() || frm.doc.disabled) return;
	if (!frappe.model.can_create("Client Invoice")) return;

	frm.remove_custom_button(__("Client Invoice"), __("Create"));
	frm.add_custom_button(
		__("Client Invoice"),
		() => {
			frappe.new_doc("Client Invoice", { customer: frm.doc.name });
		},
		__("Create")
	);
}
