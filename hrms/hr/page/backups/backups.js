frappe.provide("hrms");

const BACKUP_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

frappe.pages["backups"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Backups"),
		single_column: true,
	});
	frappe.breadcrumbs.add("HR");
	hrms.backups_page.make(page);
};

frappe.pages["backups"].on_page_show = function () {
	hrms.backups_page.refresh();
};

hrms.backups_page = {
	page: null,
	$body: null,
	busy: false,

	make(page) {
		this.page = page;
		page.set_primary_action(__("Dump data now"), () => this.dump_now());
		const $existing = page.main.find(".sp-backups-page");
		if ($existing.length) {
			this.$body = $existing;
			this.refresh();
			return;
		}
		this.$body = $('<div class="sp-backups-page"></div>').appendTo(page.main);
		this.render_shell();
		this.bind();
		this.refresh();
	},

	render_shell() {
		this.$body.html(`
			<section class="sp-backups-card">
				<h2>${__("Backup period")}</h2>
				<p class="sp-backups-note">
					${__("Dump the site database on a schedule, or dump it now. Older dumps are removed after the keep limit.")}
				</p>
				<div class="sp-backups-grid">
					<div class="sp-backups-period"></div>
					<div class="sp-backups-weekday"></div>
					<div class="sp-backups-month-day"></div>
					<div class="sp-backups-limit"></div>
				</div>
				<button type="button" class="btn btn-default btn-sm sp-backups-save">${__("Save")}</button>
			</section>
			<section class="sp-backups-card">
				<h2>${__("Data dumps")}</h2>
				<div class="sp-backups-list"></div>
			</section>
		`);
		this.period = this.control(this.$body.find(".sp-backups-period"), {
			fieldtype: "Select",
			fieldname: "period",
			label: __("Backup period"),
			options: ["Off", "Daily", "Weekly", "Monthly"].join("\n"),
			onchange: () => this.toggle_period_fields(),
		});
		this.weekday = this.control(this.$body.find(".sp-backups-weekday"), {
			fieldtype: "Select",
			fieldname: "weekday",
			label: __("Weekday"),
			options: BACKUP_WEEKDAYS.join("\n"),
		});
		this.month_day = this.control(this.$body.find(".sp-backups-month-day"), {
			fieldtype: "Int",
			fieldname: "month_day",
			label: __("Day of month"),
			description: __("From 1 to 28."),
		});
		this.limit = this.control(this.$body.find(".sp-backups-limit"), {
			fieldtype: "Int",
			fieldname: "limit",
			label: __("Dumps to keep"),
		});
		this.toggle_period_fields();
	},

	control(parent, df) {
		return frappe.ui.form.make_control({
			parent,
			df,
			render_input: true,
		});
	},

	bind() {
		this.$body.on("click", ".sp-backups-save", () => this.save());
		this.$body.on("click", "[data-dump]", (event) => {
			const filename = $(event.currentTarget).attr("data-dump");
			if (filename) {
				this.download(filename);
			}
		});
	},

	toggle_period_fields() {
		const period = this.period?.get_value() || "Off";
		this.$body.find(".sp-backups-weekday").toggle(period === "Weekly");
		this.$body.find(".sp-backups-month-day").toggle(period === "Monthly");
	},

	refresh() {
		if (!this.$body || this.busy) {
			return;
		}
		frappe.call({
			method: "hrms.hr.backups.get_backup_state",
			callback: (r) => this.apply_state(r.message || {}),
		});
	},

	apply_state(state) {
		const settings = state.settings || {};
		if (this.period) {
			this.period.set_value(settings.period || "Off");
			this.weekday.set_value(settings.weekday || "Monday");
			this.month_day.set_value(settings.month_day || 1);
			this.limit.set_value(settings.limit || 7);
			this.toggle_period_fields();
		}
		this.render_dumps(state.dumps || []);
	},

	render_dumps(dumps) {
		const $list = this.$body.find(".sp-backups-list");
		if (!dumps.length) {
			$list.html(`<p class="sp-backups-empty">${__("No data dumps yet.")}</p>`);
			return;
		}
		const rows = dumps
			.map(
				(row) => `
				<tr>
					<td>${frappe.utils.escape_html(row.filename || "")}</td>
					<td>${frappe.utils.escape_html(row.created || "")}</td>
					<td>${frappe.utils.escape_html(row.size || "")}</td>
					<td>
						<button type="button" class="btn btn-default btn-xs" data-dump="${frappe.utils.escape_html(row.filename || "")}">
							${__("Download")}
						</button>
					</td>
				</tr>`,
			)
			.join("");
		$list.html(`
			<table class="sp-backups-table">
				<thead>
					<tr>
						<th>${__("File")}</th>
						<th>${__("Created")}</th>
						<th>${__("Size")}</th>
						<th></th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>
		`);
	},

	save() {
		if (this.busy) {
			return;
		}
		this.busy = true;
		frappe.call({
			method: "hrms.hr.backups.save_backup_settings",
			args: {
				period: this.period.get_value(),
				weekday: this.weekday.get_value(),
				month_day: this.month_day.get_value(),
				limit: this.limit.get_value(),
			},
			callback: (r) => {
				this.busy = false;
				this.apply_state(r.message || {});
				frappe.show_alert({ message: __("Backup settings saved."), indicator: "green" });
			},
			error: () => {
				this.busy = false;
			},
		});
	},

	dump_now() {
		if (this.busy) {
			return;
		}
		this.busy = true;
		frappe.dom.freeze(__("Dumping data..."));
		frappe.call({
			method: "hrms.hr.backups.dump_now",
			callback: (r) => {
				this.busy = false;
				frappe.dom.unfreeze();
				const message = r.message || {};
				this.apply_state(message);
				frappe.show_alert({ message: __("Data dump is ready."), indicator: "green" });
				if (message.filename) {
					this.download(message.filename);
				}
			},
			error: () => {
				this.busy = false;
				frappe.dom.unfreeze();
			},
		});
	},

	download(filename) {
		const params = { filename };
		if (frappe.csrf_token && frappe.csrf_token !== "None") {
			params.csrf_token = frappe.csrf_token;
		}
		window.open(
			frappe.urllib.get_full_url("/api/method/hrms.hr.backups.download_dump?" + $.param(params)),
		);
	},
};
