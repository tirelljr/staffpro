// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Client Invoice", {
	onload(frm) {
		if (frm.is_new() && frm.doc.currency !== "USD") {
			frm.set_value("currency", "USD");
		}
	},

	refresh(frm) {
		frm.trigger("toggle_get_agents_button");
		frm.set_query("employee", "agents", () => ({
			filters: {
				status: "Active",
				company: frm.doc.company,
				...(frm.doc.customer ? { bill_to_customer: frm.doc.customer } : {}),
			},
		}));
		hrms.mount_invoice_form_export?.(frm, {
			doctype: "Client Invoice",
			label: __("Client Invoice"),
			file_stem: "Client_Invoices",
			storage_key: "staff-pro-client-invoice-export-format",
		});
		if (frm.doc.docstatus === 1 && frm.doc.sales_invoice) {
			frm.add_custom_button(
				__("Posted Invoice"),
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
		if (frm.doc.currency !== "USD") {
			frm.set_value("currency", "USD");
		}
	},

	from_date(frm) {
		frm.trigger("set_working_period_dates");
		frm.trigger("toggle_get_agents_button");
	},

	to_date(frm) {
		frm.trigger("toggle_get_agents_button");
		frm.trigger("refresh_agent_rows");
	},

	set_working_period_dates(frm) {
		if (!frm.doc.from_date || frm.doc.docstatus !== 0) {
			return;
		}
		return frappe.call({
			method: "hrms.payroll.auto_payroll.get_working_period_end",
			args: {
				start_date: frm.doc.from_date,
				working_days: 10,
			},
			callback(r) {
				if (r.message?.end_date) {
					frm.set_value("to_date", r.message.end_date);
					frm.set_value("posting_date", r.message.end_date);
				}
			},
		});
	},

	refresh_agent_rows(frm) {
		(frm.doc.agents || []).forEach((row) => {
			if (row.employee) {
				fill_agent_row(frm, row.doctype, row.name);
			}
		});
	},

	toggle_get_agents_button(frm) {
		frm.remove_custom_button(__("Get Agents"));
		if (frm.doc.docstatus !== 0) {
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
	employee(frm, cdt, cdn) {
		fill_agent_row(frm, cdt, cdn);
	},
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

function fill_agent_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row?.employee) {
		return;
	}
	if (!(frm.doc.from_date && frm.doc.to_date)) {
		return;
	}
	return frm
		.call({
			method: "get_agent_billing_row",
			args: { employee: row.employee },
		})
		.then((r) => {
			const data = r.message || {};
			if (data.employee_name) {
				frappe.model.set_value(cdt, cdn, "employee_name", data.employee_name);
			}
			frappe.model.set_value(cdt, cdn, "hours", flt(data.hours));
			frappe.model.set_value(cdt, cdn, "billing_rate", flt(data.billing_rate));
			calculate_totals(frm);
		});
}

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
