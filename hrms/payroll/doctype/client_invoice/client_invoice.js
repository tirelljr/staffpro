// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Client Invoice", {
	refresh(frm) {
		frm.trigger("toggle_get_agents_button");
		if (frm.doc.docstatus === 1 && frm.doc.sales_invoice) {
			frm.add_custom_button(
				__("Sales Invoice"),
				() => {
					frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
				},
				__("View")
			);
		}
	},

	customer(frm) {
		frm.trigger("toggle_get_agents_button");
	},

	company(frm) {
		frm.trigger("toggle_get_agents_button");
	},

	from_date(frm) {
		frm.trigger("toggle_get_agents_button");
	},

	to_date(frm) {
		frm.trigger("toggle_get_agents_button");
	},

	toggle_get_agents_button(frm) {
		frm.remove_custom_button(__("Get Agents"));
		if (frm.doc.docstatus !== 0 || frm.is_new()) {
			return;
		}
		if (!(frm.doc.customer && frm.doc.company && frm.doc.from_date && frm.doc.to_date)) {
			return;
		}
		frm
			.add_custom_button(__("Get Agents"), () => {
				return frappe
					.call({
						doc: frm.doc,
						method: "get_agents",
						freeze: true,
						freeze_message: __("Fetching agents from attendance..."),
					})
					.then((r) => {
						if (r.docs?.[0]?.agents) {
							frm.dirty();
							return frm.save();
						}
						frm.refresh();
					});
			})
			.addClass("btn-primary");
	},
});

frappe.ui.form.on("Client Invoice Item", {
	hours(frm, cdt, cdn) {
		calculate_row_amount(frm, cdt, cdn);
	},
	billing_rate(frm, cdt, cdn) {
		calculate_row_amount(frm, cdt, cdn);
	},
	agents_remove(frm) {
		calculate_totals(frm);
	},
});

function calculate_row_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.hours) * flt(row.billing_rate));
	calculate_totals(frm);
}

function calculate_totals(frm) {
	let total_hours = 0;
	let total_amount = 0;
	(frm.doc.agents || []).forEach((row) => {
		total_hours += flt(row.hours);
		total_amount += flt(row.amount);
	});
	frm.set_value("total_hours", total_hours);
	frm.set_value("total_amount", total_amount);
}
