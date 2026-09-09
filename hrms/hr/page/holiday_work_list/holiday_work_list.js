frappe.provide("hrms.ui");

frappe.pages["holiday-work-list"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Holiday Work List"),
		single_column: true,
	});

	frappe.breadcrumbs.add("HR");
	frappe.holiday_work_list.make(page);
};

frappe.pages["holiday-work-list"].on_page_show = function () {
	frappe.holiday_work_list.refresh();
};

frappe.holiday_work_list = {
	page: null,
	$body: null,
	holidays: [],
	roster: null,
	holiday_date: "",
	department: "",
	status: "Working",

	make(page) {
		this.page = page;
		const $existing = page.main.find(".sp-hwl-page");
		if ($existing.length) {
			this.$body = $existing;
			this.refresh();
			return;
		}
		this.$body = $('<div class="sp-hwl-page"></div>').appendTo(page.main);
		this.render_shell();
		this.bind();
		this.refresh();
	},

	escape(value) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
	},

	avatar(row) {
		if (row.image) {
			return `<img class="sp-celebrations__avatar-img" src="${this.escape(row.image)}" alt="">`;
		}
		const initials = String(row.employee_name || row.employee || "")
			.trim()
			.split(/\s+/)
			.slice(0, 2)
			.map((part) => part[0] || "")
			.join("")
			.toUpperCase();
		return `<span class="sp-celebrations__avatar-fallback">${this.escape(initials)}</span>`;
	},

	select_html(className, variant, label, options, value) {
		if (hrms.ui && typeof hrms.ui.dash_select_html === "function") {
			return hrms.ui.dash_select_html({ className, variant, label, options, value });
		}
		const selected = options.find((opt) => opt.value === value) || options[0];
		return `
			<select class="${this.escape(className)} sp-dash-panel__select sp-dash-panel__select--${this.escape(variant)}" aria-label="${this.escape(label)}">
				${options
					.map(
						(opt) =>
							`<option value="${this.escape(opt.value)}"${opt.value === selected.value ? " selected" : ""}>${this.escape(opt.label)}</option>`,
					)
					.join("")}
			</select>`;
	},

	status_toggle_html() {
		const working = this.status === "Working";
		return `
			<div class="sp-hwl-toggle" role="group" aria-label="${this.escape(__("Working / Not Working"))}">
				<button type="button" class="sp-hwl-toggle__btn${working ? " is-active" : ""}" data-value="Working">${this.escape(__("Working"))}</button>
				<button type="button" class="sp-hwl-toggle__btn${!working ? " is-active" : ""}" data-value="Not Working">${this.escape(__("Not Working"))}</button>
			</div>
		`;
	},

	render_shell() {
		this.$body.html(`
			<div class="sp-hwl-layout">
				<section class="sp-dash-panel sp-hwl-holidays" aria-label="${this.escape(__("Upcoming Holidays"))}">
					<div class="sp-dash-panel__head">
						<h2 class="sp-dash-panel__title">${this.escape(__("Upcoming Holidays"))}</h2>
						<button type="button" class="sp-hwl-refresh">${this.escape(__("Refresh"))}</button>
					</div>
					<div class="sp-hwl-holiday-list"></div>
				</section>
				<section class="sp-dash-panel sp-hwl-detail" aria-label="${this.escape(__("Holiday Work List"))}">
					<div class="sp-dash-panel__head">
						<h2 class="sp-dash-panel__title sp-hwl-detail-title">${this.escape(__("Select a holiday"))}</h2>
						<div class="sp-dash-panel__filters">
							<div class="sp-dash-panel__filter">
								${this.select_html(
									"sp-hwl-department",
									"outline",
									__("Department"),
									[{ value: "", label: __("All Departments") }],
									"",
								)}
							</div>
							${this.status_toggle_html()}
						</div>
					</div>
					<div class="sp-hwl-totals" aria-live="polite"></div>
					<div class="sp-hwl-people"></div>
				</section>
			</div>
		`);
		if (hrms.ui && typeof hrms.ui.bind_dash_selects === "function") {
			hrms.ui.bind_dash_selects(this.$body);
		}
	},

	bind() {
		const me = this;
		this.$body.on("click", ".sp-hwl-refresh", () => me.refresh());
		this.$body.on("click", ".sp-hwl-holiday", function () {
			me.holiday_date = $(this).data("date") || "";
			me.load_roster();
		});
		this.$body.on("change", ".sp-hwl-department", function () {
			me.department = $(this).val() || "";
			me.load_roster();
		});
		this.$body.on("click", ".sp-hwl-toggle__btn", function () {
			const value = $(this).data("value");
			if (!value || $(this).hasClass("is-active")) {
				return;
			}
			me.status = value;
			me.$body.find(".sp-hwl-toggle__btn").removeClass("is-active");
			$(this).addClass("is-active");
			me.render_people();
		});
		this.$body.on("click", ".sp-hwl-person", function () {
			const employee = $(this).data("employee");
			if (employee) {
				frappe.set_route("Form", "Employee", employee);
			}
		});
	},

	empty_html(message) {
		return `
			<div class="sp-hwl-empty">
				<p>${this.escape(message)}</p>
			</div>
		`;
	},

	refresh() {
		const me = this;
		if (!this.$body) {
			return;
		}
		this.$body.find(".sp-hwl-holiday-list").addClass("is-loading");
		frappe.call({
			method: "hrms.hr.page.holiday_work_list.holiday_work_list.get_upcoming_holidays",
			callback(r) {
				me.$body.find(".sp-hwl-holiday-list").removeClass("is-loading");
				me.holidays = r.message || [];
				if (!me.holiday_date && me.holidays.length) {
					me.holiday_date = me.holidays[0].holiday_date;
				}
				me.render_holidays();
				if (me.holiday_date) {
					me.load_roster();
				} else {
					me.roster = null;
					me.render_detail();
				}
			},
			error() {
				me.$body.find(".sp-hwl-holiday-list").removeClass("is-loading");
				me.holidays = [];
				me.roster = null;
				me.$body.find(".sp-hwl-holiday-list").html(me.empty_html(__("Could not load upcoming holidays.")));
				me.render_detail();
			},
		});
	},

	render_holidays() {
		const $list = this.$body.find(".sp-hwl-holiday-list");
		if (!this.holidays.length) {
			$list.html(this.empty_html(__("No upcoming public holidays.")));
			return;
		}
		$list.html(
			this.holidays
				.map((holiday) => {
					const selected = holiday.holiday_date === this.holiday_date ? " is-selected" : "";
					return `
						<button type="button" class="sp-hwl-holiday${selected}" data-date="${this.escape(holiday.holiday_date)}">
							<span class="sp-hwl-holiday__name">${this.escape(holiday.description)}</span>
							<span class="sp-hwl-holiday__date">${this.escape(frappe.datetime.str_to_user(holiday.holiday_date))}</span>
							<span class="sp-hwl-holiday__counts">
								${this.escape(__("Working"))}: ${holiday.working_count || 0}
								· ${this.escape(__("Not Working"))}: ${holiday.not_working_count || 0}
							</span>
						</button>
					`;
				})
				.join(""),
		);
	},

	department_options(roster) {
		const options = [{ value: "", label: __("All Departments") }];
		(roster?.departments || []).forEach((name) => options.push({ value: name, label: name }));
		if ((roster?.details || []).some((row) => !row.department)) {
			options.push({ value: "__none__", label: __("No Department") });
		}
		return options;
	},

	set_department_options(roster) {
		const $select = this.$body.find(".sp-hwl-department");
		const options = this.department_options(roster);
		if (hrms.ui && typeof hrms.ui.set_dash_select_options === "function") {
			this.department = hrms.ui.set_dash_select_options($select, options) || this.department || "";
			return;
		}
		const current = $select.val() || this.department || "";
		const values = options.map((opt) => String(opt.value));
		const selected = values.includes(current) ? current : "";
		$select.html(
			options
				.map(
					(opt) =>
						`<option value="${this.escape(opt.value)}"${String(opt.value) === selected ? " selected" : ""}>${this.escape(opt.label)}</option>`,
				)
				.join(""),
		);
		$select.val(selected);
		this.department = selected;
	},

	load_roster() {
		const me = this;
		if (!this.holiday_date) {
			this.roster = null;
			this.render_detail();
			return;
		}
		this.$body.find(".sp-hwl-people").addClass("is-loading");
		frappe.call({
			method: "hrms.hr.page.holiday_work_list.holiday_work_list.get_holiday_work_list",
			args: {
				holiday_date: this.holiday_date,
				department: this.department || undefined,
			},
			callback(r) {
				me.$body.find(".sp-hwl-people").removeClass("is-loading");
				me.roster = r.message || { details: [], departments: [] };
				me.set_department_options(me.roster);
				me.render_holidays();
				me.render_detail();
			},
			error() {
				me.$body.find(".sp-hwl-people").removeClass("is-loading");
				me.roster = { details: [], departments: [] };
				me.render_detail();
			},
		});
	},

	filtered_people() {
		const rows = this.roster?.details || [];
		if (this.status === "Working") {
			return rows.filter((row) => row.will_work);
		}
		return rows.filter((row) => !row.will_work);
	},

	render_detail() {
		const title = this.roster?.description
			? this.roster.description
			: __("Select a holiday");
		this.$body.find(".sp-hwl-detail-title").text(title);
		const working = this.roster?.working_count || 0;
		const notWorking = this.roster?.not_working_count || 0;
		if (this.roster) {
			this.$body.find(".sp-hwl-totals").html(`
				<span><strong>${this.escape(__("Working"))}:</strong> ${working}</span>
				<span><strong>${this.escape(__("Not Working"))}:</strong> ${notWorking}</span>
			`);
		} else {
			this.$body.find(".sp-hwl-totals").empty();
		}
		this.render_people();
	},

	render_people() {
		const $list = this.$body.find(".sp-hwl-people");
		if (!this.roster) {
			$list.html(this.empty_html(__("Select a holiday to see who elected to work.")));
			return;
		}
		const rows = this.filtered_people();
		if (!rows.length) {
			const message =
				this.status === "Working"
					? __("No one has elected to work on this holiday.")
					: __("Everyone eligible has elected to work.");
			$list.html(this.empty_html(message));
			return;
		}
		$list.html(
			rows
				.map(
					(row) => `
				<button type="button" class="sp-hwl-person" data-employee="${this.escape(row.employee)}">
					<span class="sp-hwl-person__avatar">${this.avatar(row)}</span>
					<span class="sp-hwl-person__meta">
						<span class="sp-hwl-person__name">${this.escape(row.employee_name || row.employee || "")}</span>
						${row.department ? `<span class="sp-hwl-person__dept">${this.escape(row.department)}</span>` : ""}
					</span>
					<span class="sp-hwl-person__status${row.will_work ? " is-working" : ""}">${this.escape(row.status)}</span>
				</button>
			`,
				)
				.join(""),
		);
	},
};
