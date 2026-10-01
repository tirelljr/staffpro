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
			(df) => !["email", "first_name", "role_profiles"].includes(df.fieldname)
		);
		fields.unshift(
			{
				fieldname: "login_name",
				fieldtype: "Data",
				label: __("Username"),
				reqd: 1,
			},
			{
				fieldname: "new_password",
				fieldtype: "Password",
				label: __("Password"),
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

	insert() {
		const me = this;
		const data = this.get_values();
		if (!data) {
			return Promise.resolve();
		}

		const username = (data.login_name || "").trim();
		const password = String(data.new_password || "");
		const confirm = String(data.confirm_password || "");
		if (!username || username.includes("@")) {
			this.dialog.working = false;
			frappe.msgprint(__("Use a username, not an email address."));
			return Promise.resolve();
		}
		if (password.length < 8) {
			this.dialog.working = false;
			frappe.msgprint(__("Password must be at least 8 characters."));
			return Promise.resolve();
		}
		if (password !== confirm) {
			this.dialog.working = false;
			frappe.msgprint(__("Passwords do not match."));
			return Promise.resolve();
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
					if (r?.message) {
						me.process_after_insert(r);
						frappe.show_alert({
							message: __("{0} saved", [__("User")]),
							indicator: "green",
						});
						if (cur_list?.doctype === "User") {
							cur_list.refresh();
						}
					}
					resolve(me.doc);
				},
				always() {
					me.dialog.working = false;
				},
			});
		});
	}
};
