(function applyPostedInvoiceUiLabels() {
	const messages = frappe._messages || frappe.boot?.__messages || {};
	Object.assign(messages, {
		"Sales Invoice": "Posted Invoice",
		"Sales Invoices": "Posted Invoices",
		"New Sales Invoice": "New Posted Invoice",
	});
	frappe._messages = messages;
	if (frappe.boot) {
		frappe.boot.__messages = messages;
	}
})();

frappe.ui.form.on("Sales Invoice", {
	onload(frm) {
		if (frm.is_new() && frappe.model.can_create("Client Invoice")) {
			frappe.new_doc("Client Invoice");
			return;
		}
		apply_bpo_invoice_layout(frm);
	},

	refresh(frm) {
		if (frm.is_new() && frappe.model.can_create("Client Invoice")) {
			return;
		}
		apply_bpo_invoice_layout(frm);
		strip_erpnext_invoice_actions(frm);
		setTimeout(() => apply_bpo_invoice_layout(frm), 150);
		setTimeout(() => strip_erpnext_invoice_actions(frm), 150);
	},
});

const HIDDEN_INVOICE_FIELDS = [
	"scan_barcode",
	"update_stock",
	"set_warehouse",
	"set_target_warehouse",
	"naming_series",
	"set_posting_time",
	"posting_time",
	"is_pos",
	"pos_profile",
	"is_return",
	"is_debit_note",
	"customer_group",
	"territory",
	"campaign",
	"source",
	"project",
	"cost_center",
	"incoterm",
	"shipping_rule",
	"tax_id",
	"tax_category",
	"taxes_and_charges",
	"exempt_from_sales_tax",
	"taxes",
	"taxes_section",
	"section_break_40",
	"section_break_43",
	"section_break_vacb",
	"total_advance",
	"allocate_advances_automatically",
	"use_company_roundoff_cost_center",
	"ignore_pricing_rule",
	"additional_discount_percentage",
	"discount_amount",
	"apply_discount_on",
	"loyalty_points",
	"timesheets",
	"packed_items",
	"transporter",
	"address_and_contact_tab",
	"more_info",
	"more_info_tab",
	"terms_tab",
	"tc_name",
	"terms",
	"selling_price_list",
	"price_list_currency",
	"plc_conversion_rate",
	"debit_to",
	"against_income_account",
	"letter_head",
	"sales_partner",
	"commission_rate",
	"total_commission",
	"in_words",
];

const HIDDEN_ITEM_FIELDS = [
	"warehouse",
	"target_warehouse",
	"from_warehouse",
	"actual_qty",
	"stock_uom",
	"conversion_factor",
	"serial_no",
	"batch_no",
	"item_group",
	"brand",
	"image",
	"barcode",
	"item_tax_template",
	"income_account",
	"expense_account",
	"cost_center",
	"discount_percentage",
	"discount_amount",
];

const HIDDEN_TABS = ["Address & Contact", "More Info", "Terms"];

function apply_bpo_invoice_layout(frm) {
	HIDDEN_INVOICE_FIELDS.forEach((fieldname) => {
		if (frm.fields_dict[fieldname]) {
			frm.set_df_property(fieldname, "hidden", 1);
		}
	});

	const labels = {
		customer: __("Client"),
		customer_name: __("Client Name"),
		items: __("Agent Hours"),
		items_section: __("Agent Hours"),
		posting_date: __("Invoice Date"),
		due_date: __("Payment Due"),
		billing_from: __("Billing From"),
		billing_to: __("Billing To"),
		remarks: __("Notes"),
		payment_terms_template: __("Payment Terms"),
		outstanding_amount: __("Outstanding"),
		grand_total: __("Total"),
		total_qty: __("Total Hours"),
	};
	Object.entries(labels).forEach(([fieldname, label]) => {
		if (frm.fields_dict[fieldname]) {
			frm.set_df_property(fieldname, "hidden", 0);
			frm.set_df_property(fieldname, "label", label);
		}
	});

	const items = frm.get_field("items");
	if (items?.grid) {
		HIDDEN_ITEM_FIELDS.forEach((fieldname) => {
			items.grid.update_docfield_property(fieldname, "hidden", 1);
		});
		items.grid.update_docfield_property("item_code", "label", __("Service"));
		items.grid.update_docfield_property("item_name", "label", __("Description"));
		items.grid.update_docfield_property("qty", "label", __("Hours"));
		items.grid.update_docfield_property("rate", "label", __("Billing Rate"));
		items.grid.refresh();
	}

	hide_invoice_tabs(frm);
	relabel_invoice_page(frm);
}

function hide_invoice_tabs(frm) {
	const $tabs = frm.$wrapper?.closest(".page-body, .page-container") || frm.page?.wrapper;
	const $nav = ($tabs?.find ? $tabs : $(frm.page.wrapper)).find("#form-tabs");
	$nav.find("li, .nav-item").each(function () {
		const label = ($(this).text() || "").replace(/\s+/g, " ").trim();
		if (HIDDEN_TABS.includes(label)) {
			$(this).hide();
		}
	});
}

function relabel_invoice_page(frm) {
	const title = frm.is_new()
		? __("New Posted Invoice")
		: frm.doc.customer_name || frm.doc.name || __("Posted Invoice");
	frm.page.set_title(title);

	const $head = frm.page.wrapper.find(".page-head");
	$head.find(".title-text, h3, .ellipsis, .breadcrumb-item, .page-title").each(function () {
		const $el = $(this);
		const text = ($el.text() || "").trim();
		if (!text) return;
		if (text === "Sales Invoice" || text === __("Sales Invoice")) {
			$el.text(__("Posted Invoice"));
		} else if (text.includes("Sales Invoice")) {
			$el.text(text.replace(/Sales Invoice/g, __("Posted Invoice")));
		}
	});
}

function strip_erpnext_invoice_actions(frm) {
	["Sales Order", "Delivery Note", "Quotation", "Pick List"].forEach((label) => {
		frm.remove_custom_button(__(label), __("Get Items From"));
	});
	frm.remove_custom_button(__("Get Items From"));
	frm.page.remove_inner_button?.(__("Get Items From"));
	frm.page.btn_inner_group?.find(".inner-group-button").each(function () {
		const label = ($(this).find(".dropdown-toggle").text() || "").trim();
		if (label === __("Get Items From") || label === "Get Items From") {
			$(this).hide();
		}
	});
}
