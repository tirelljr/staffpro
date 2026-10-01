frappe.pages["master-key"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Master Key"),
		single_column: true,
	});
	frappe.breadcrumbs.add("HR");
	hrms.master_key.make(page);
};

frappe.pages["master-key"].on_page_show = function () {
	hrms.master_key.refresh();
};

frappe.provide("hrms");

hrms.master_key = {
	page: null,
	$body: null,
	status: null,
	until_control: null,

	make(page) {
		this.page = page;
		const existing = page.main.find(".sp-mk-page");
		if (existing.length) {
			this.$body = existing;
			this.refresh();
			return;
		}
		this.$body = $('<div class="sp-mk-page"></div>').appendTo(page.main);
		this.refresh();
	},

	refresh() {
		if (!this.$body) return;
		frappe.call({
			method: "hrms.hr.master_key.get_status",
			callback: (response) => {
				this.status = response.message || {};
				this.render();
			},
			error: (error) => {
				const message =
					(error && error.message) || __("Master Key is not available yet. Run bench migrate, then open this page again.");
				this.$body.html(
					`<section class="sp-mk-card"><p>${frappe.utils.escape_html(message)}</p></section>`,
				);
			},
		});
	},

	render() {
		const status = this.status || {};
		const locked = !!status.locked;
		const configured = !!status.key_configured;
		const status_class = locked ? "is-locked" : "is-open";
		const status_text = locked
			? status.message || __("System access is turned off.")
			: __("System access is on.");
		const key_heading = configured ? __("Change master key") : __("Set master key");
		const key_copy = configured
			? __("Enter the current master key, your login password, and the new key. The key is stored as a hash and cannot be shown again.")
			: __("Choose a master key of at least 12 characters and confirm it with your login password. It is stored as a hash and cannot be shown again.");
		const current_field = configured
			? this.field("current_key", __("Current master key"), "current-password")
			: "";

		this.$body.html(`
			<section class="sp-mk-card">
				<div class="sp-mk-status ${status_class}">${frappe.utils.escape_html(status_text)}</div>
			</section>
			<section class="sp-mk-card">
				<h2>${frappe.utils.escape_html(key_heading)}</h2>
				<p>${frappe.utils.escape_html(key_copy)}</p>
				${current_field}
				${this.field("master_key", __("New master key"), "new-password")}
				${this.field("confirm_key", __("Confirm new master key"), "new-password")}
				${this.field("account_password", __("Your login password"), "current-password")}
				<div class="sp-mk-actions">
					<button type="button" class="btn btn-primary btn-sm sp-mk-save">${__("Save master key")}</button>
				</div>
			</section>
			<section class="sp-mk-card">
				<h2>${__("Turn access off")}</h2>
				<p class="sp-mk-note">${__(
					"This signs everyone out, including you. Desk, login, API, and kiosk access stay off until the master key turns them back on, or until the time you choose."
				)}</p>
				${this.field("lock_key", __("Master key"), "current-password")}
				<div class="sp-mk-actions">
					<button type="button" class="btn btn-danger btn-sm sp-mk-lock-manual" ${
						configured ? "" : "disabled"
					}>${__("Lock until I turn it back on")}</button>
				</div>
				<div class="sp-mk-until"></div>
				<div class="sp-mk-actions">
					<button type="button" class="btn btn-danger btn-sm sp-mk-lock-until" ${
						configured ? "" : "disabled"
					}>${__("Lock until this time")}</button>
				</div>
			</section>
		`);
		this.until_control = frappe.ui.form.make_control({
			parent: this.$body.find(".sp-mk-until").get(0),
			df: {
				fieldtype: "Datetime",
				fieldname: "locked_until",
				label: __("Turn access back on"),
			},
			render_input: true,
		});
		this.bind();
	},

	field(name, label, autocomplete) {
		return `
			<label class="sp-mk-field">
				<span>${frappe.utils.escape_html(label)}</span>
				<input type="password" name="${frappe.utils.escape_html(name)}" autocomplete="${frappe.utils.escape_html(
					autocomplete
				)}">
			</label>
		`;
	},

	value(name) {
		return this.$body.find(`input[name="${name}"]`).val() || "";
	},

	clear_secrets() {
		this.$body.find("input[type=password]").val("");
	},

	bind() {
		this.$body.find(".sp-mk-save").on("click", () => this.save_key());
		this.$body.find(".sp-mk-lock-manual").on("click", () => this.confirm_lock("manual"));
		this.$body.find(".sp-mk-lock-until").on("click", () => this.confirm_lock("until"));
	},

	save_key() {
		frappe.call({
			method: "hrms.hr.master_key.set_master_key",
			args: {
				master_key: this.value("master_key"),
				confirm_key: this.value("confirm_key"),
				account_password: this.value("account_password"),
				current_key: this.value("current_key"),
			},
			freeze: true,
			freeze_message: __("Saving master key"),
			callback: () => {
				frappe.show_alert({ message: __("Master key saved"), indicator: "green" });
				this.refresh();
			},
			error: () => this.clear_secrets(),
		});
	},

	confirm_lock(mode) {
		const until = mode === "until" && this.until_control ? this.until_control.get_value() : null;
		if (mode === "until" && !until) {
			frappe.msgprint(__("Choose a time in the future."));
			return;
		}
		const message =
			mode === "until"
				? __("This signs everyone out until {0}. You will need the master key to turn access back on sooner.", [
						frappe.datetime.str_to_user(until),
					])
				: __(
						"This signs everyone out, including you. Access stays off until the master key is used on the lock screen."
					);
		frappe.confirm(message, () => this.lock(mode, until));
	},

	lock(mode, until) {
		frappe.call({
			method: "hrms.hr.master_key.lock_access",
			args: {
				master_key: this.value("lock_key"),
				mode,
				locked_until: until,
			},
			freeze: true,
			freeze_message: __("Turning access off"),
			callback: (response) => {
				window.location.href = (response.message && response.message.redirect) || "/system-lock";
			},
			error: () => this.clear_secrets(),
		});
	},
};
