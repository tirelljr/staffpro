// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.UserQuickEntryForm = class UserQuickEntryForm extends frappe.ui.form.QuickEntryForm {
	setup() {
		return new Promise((resolve) => {
			frappe.model.with_doctype("Has Role", () => {
				super.setup().then(resolve);
			});
		});
	}

	set_meta_and_mandatory_fields() {
		super.set_meta_and_mandatory_fields();
		const fields = this.docfields.filter(
			(df) =>
				![
					"email",
					"first_name",
					"new_password",
					"role_profiles",
					"role_profile_name",
					"send_welcome_email",
				].includes(df.fieldname)
		);
		// Field names must not match User fields. The dialog copies the User
		// definition onto matching names, and User.new_password is hidden.
		fields.unshift(
			{
				fieldname: "login_name",
				fieldtype: "Data",
				label: __("Username"),
				reqd: 1,
			},
			{
				fieldname: "login_password",
				fieldtype: "Password",
				label: __("Password"),
				description: __("At least 8 characters."),
				reqd: 1,
			},
			{
				fieldname: "confirm_password",
				fieldtype: "Password",
				label: __("Confirm Password"),
				reqd: 1,
			}
		);
		fields.push({
			fieldname: "desk_roles",
			fieldtype: "Table MultiSelect",
			label: __("Roles"),
			options: "Has Role",
			reqd: 1,
		});
		this.docfields = fields;
	}

	register_primary_action() {
		const me = this;
		this.set_primary_action(__("Save"), () => {
			if (me.working) return;
			if (!me.get_values()) return;
			me.working = true;
			me.insert()
				.then((saved) => {
					if (!saved) return;
					me.animation_speed = "slow";
					me.hide();
				})
				.finally(() => {
					me.working = false;
				});
		});
	}

	typed_value(fieldname) {
		const field = this.fields_dict?.[fieldname];
		const direct = field?.$input?.val();
		if (direct) return String(direct);
		let best = "";
		field?.$wrapper?.find("input").each(function () {
			const value = String($(this).val() || "");
			if (value.length > best.length) best = value;
		});
		return best;
	}

	insert() {
		const me = this;
		const data = this.get_values();
		if (!data) {
			return Promise.resolve(null);
		}

		const username = (data.login_name || "").trim();
		const password = this.typed_value("login_password") || String(data.login_password || "");
		const confirm = this.typed_value("confirm_password") || String(data.confirm_password || "");
		if (!username || username.includes("@")) {
			frappe.msgprint(__("Use a username, not an email address."));
			return Promise.resolve(null);
		}
		if (password.length < 8) {
			frappe.msgprint(__("Password must be at least 8 characters."));
			return Promise.resolve(null);
		}
		if (password !== confirm) {
			frappe.msgprint(__("Passwords do not match."));
			return Promise.resolve(null);
		}

		return new Promise((resolve) => {
			frappe.call({
				method: "hrms.overrides.employee_master.create_user_login",
				args: {
					username,
					first_name: data.first_name,
					last_name: data.last_name,
					roles: data.desk_roles || [],
					new_password: password,
				},
				callback(r) {
					if (!r?.message) {
						resolve(null);
						return;
					}
					me.process_after_insert(r);
					frappe.show_alert({
						message: __("{0} saved", [__("User")]),
						indicator: "green",
					});
					if (cur_list?.doctype === "User") {
						cur_list.refresh();
					}
					resolve(me.doc);
				},
				error() {
					resolve(null);
				},
			});
		});
	}
};

function hide_new_user_modal_fields($modal) {
	const has_username = $modal.find('[data-fieldname="username"], [data-fieldname="login_name"]').length;
	["role_profiles", "role_profile_name", "send_welcome_email"].forEach((fieldname) => {
		$modal
			.find(`[data-fieldname="${fieldname}"]`)
			.closest(".frappe-control, .form-group, .form-section")
			.addClass("hidden hide")
			.hide();
	});
	if (has_username) {
		$modal
			.find('[data-fieldname="email"]')
			.closest(".frappe-control, .form-group")
			.addClass("hidden hide")
			.hide();
	} else {
		$modal.find('[data-fieldname="email"] .clearfix, [data-fieldname="email"] label').text(__("Username"));
	}
	$modal.find(".section-head, .clearfix").each(function () {
		const text = ($(this).text() || "").replace(/\s+/g, " ").trim();
		if (text === __("Role Profile") || text === "Role Profile") {
			$(this).closest(".frappe-control, .form-group, .form-section").addClass("hidden hide").hide();
		}
	});
}

$(document).on("shown.bs.modal", ".modal", function () {
	const $modal = $(this);
	const title = ($modal.find(".modal-title, .title-section").first().text() || "")
		.replace(/\s+/g, " ")
		.trim();
	if (title !== __("New User") && title !== "New User") return;
	hide_new_user_modal_fields($modal);
	setTimeout(() => hide_new_user_modal_fields($modal), 50);
});
