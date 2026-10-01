// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Role", {
	onload(frm) {
		apply_role_access_form(frm);
	},
	refresh(frm) {
		apply_role_access_form(frm);
	},
	before_save(frm) {
		if (window.hrms?.role_access?.sync_role_form) {
			hrms.role_access.sync_role_form(frm);
		}
	},
});

function apply_role_access_form(frm) {
	if (!window.hrms?.role_access) return;
	hrms.role_access.mount_role_form(frm);
	hrms.role_access.watch_role_form(frm);
	watch_role_users_tab(frm);
	patch_role_user_assignment();
}

function patch_role_user_assignment() {
	if (typeof UsersTab === "undefined" || !UsersTab.prototype || UsersTab.prototype._staffProAssign) {
		return;
	}
	UsersTab.prototype._staffProAssign = true;
	UsersTab.prototype.add_role = function (user_name) {
		return assign_role_user(this.role, user_name, 0);
	};
	UsersTab.prototype.remove = function (user_name) {
		return assign_role_user(this.role, user_name, 1);
	};
}

function assign_role_user(role, user, remove) {
	return frappe
		.call({
			method: "hrms.hr.role_access.assign_role_user",
			args: { role, user, remove },
		})
		.then((response) => response.message);
}

function label_role_users_tab(frm) {
	const $tab = $(frm.page?.wrapper || frm.$wrapper).find("#role-users_tab");
	if (!$tab.length) return;
	const intro = __(
		"Users attached to this role get all of its permissions and access. Add or remove people here.",
	);
	let $intro = $tab.find(".staff-pro-role-users-intro");
	if (!$intro.length) {
		const $body = $tab.find(".section-body").first();
		$intro = $('<p class="staff-pro-role-users-intro text-muted">');
		if ($body.length) {
			$body.prepend($intro);
		} else {
			$tab.prepend($intro);
		}
	}
	$intro.text(intro);
}

function watch_role_users_tab(frm) {
	label_role_users_tab(frm);
	const body = $(frm.page?.wrapper || frm.$wrapper).find(".form-page").get(0);
	if (!body || body._staffProRoleUsers) return;
	body._staffProRoleUsers = true;
	new MutationObserver(() => label_role_users_tab(frm)).observe(body, {
		childList: true,
		subtree: true,
	});
}
