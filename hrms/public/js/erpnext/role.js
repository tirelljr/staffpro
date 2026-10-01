// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Role", {
	onload(frm) {
		apply_role_access_form(frm);
	},
	refresh(frm) {
		apply_role_access_form(frm);
	},
});

function apply_role_access_form(frm) {
	if (!window.hrms?.role_access) return;
	hrms.role_access.mount_role_form(frm);
	hrms.role_access.watch_role_form(frm);
}
