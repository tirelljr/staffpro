// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cubicle", {
	employee(frm) {
		frm.set_value("status", frm.doc.employee ? "Occupied" : "Vacant");
		if (!frm.doc.employee) {
			frm.set_value("employee_name", "");
		}
	},
});
