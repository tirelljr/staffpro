frappe.provide("hrms.ui");

frappe.pages["time-clock-adjustment"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Time Clock Adjustment"),
		single_column: true,
	});

	frappe.breadcrumbs.add("HR");
	frappe.time_clock_adjustment.make(page);
};

frappe.pages["time-clock-adjustment"].on_page_show = function () {
	frappe.time_clock_adjustment.refresh();
};

frappe.time_clock_adjustment = {
	page: null,
	$body: null,
	payload: null,
	status: "Pending",
	department: "",

	make(page) {
		this.page = page;
		const $existing = page.main.find(".sp-tca-page");
		if ($existing.length) {
			this.$body = $existing;
			this.refresh();
			return;
		}
		this.$body = $('<div class="sp-tca-page"></div>').appendTo(page.main);
		this.render_shell();
		this.bind();
		this.refresh();
	},

	escape(value) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
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

	render_shell() {
		this.$body.html(`
			<section class="sp-dash-panel sp-tca-panel" aria-label="${this.escape(__("Time Clock Adjustment"))}">
				<div class="sp-dash-panel__head">
					<h2 class="sp-dash-panel__title">${this.escape(__("Time Clock Adjustment"))}</h2>
					<div class="sp-dash-panel__filters">
						<div class="sp-dash-panel__filter">
							${this.select_html(
								"sp-tca__status",
								"outline",
								__("Status"),
								[
									{ value: "Pending", label: __("Pending") },
									{ value: "Approved", label: __("Approved") },
									{ value: "Rejected", label: __("Rejected") },
									{ value: "All", label: __("All") },
								],
								this.status,
							)}
						</div>
						<div class="sp-dash-panel__filter">
							${this.select_html(
								"sp-tca__department",
								"outline",
								__("Department"),
								[{ value: "", label: __("All Departments") }],
								"",
							)}
						</div>
						<button type="button" class="sp-tca__refresh">${this.escape(__("Refresh"))}</button>
					</div>
				</div>
				<p class="sp-tca__hint">${this.escape(
					__("Approve applies the requested in/out times the same way as Day View add or edit."),
				)}</p>
				<div class="sp-tca__totals" aria-live="polite"></div>
				<div class="sp-tca__table-wrap">
					<div class="sp-tca__table-head">
						<span>${this.escape(__("Employee"))}</span>
						<span>${this.escape(__("Date"))}</span>
						<span>${this.escape(__("Current"))}</span>
						<span>${this.escape(__("Requested"))}</span>
						<span>${this.escape(__("Note"))}</span>
						<span>${this.escape(__("Status"))}</span>
						<span></span>
					</div>
					<div class="sp-tca__list"></div>
				</div>
			</section>
		`);
		if (hrms.ui && typeof hrms.ui.bind_dash_selects === "function") {
			hrms.ui.bind_dash_selects(this.$body);
		}
	},

	bind() {
		const me = this;
		this.$body.on("click", ".sp-tca__refresh", () => me.refresh());
		this.$body.on("change", ".sp-tca__status", function () {
			me.status = $(this).val() || "Pending";
			me.refresh();
		});
		this.$body.on("change", ".sp-tca__department", function () {
			me.department = $(this).val() || "";
			me.render_rows();
		});
		if (hrms.time && typeof hrms.time.bind_adjustment_actions === "function") {
			hrms.time.bind_adjustment_actions(this.$body, () => me.refresh());
		}
	},

	clock(value) {
		if (hrms.time?.format_clock) {
			return hrms.time.format_clock(value) || "—";
		}
		return value || "—";
	},

	range(in_time, out_time) {
		return `${this.clock(in_time)} – ${this.clock(out_time)}`;
	},

	set_department_options(payload) {
		const $select = this.$body.find(".sp-tca__department");
		const options = [{ value: "", label: __("All Departments") }];
		(payload.departments || []).forEach((name) => options.push({ value: name, label: name }));
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

	refresh() {
		const me = this;
		if (!this.$body) {
			return;
		}
		const $list = this.$body.find(".sp-tca__list");
		$list.addClass("is-loading");
		frappe.call({
			method: "hrms.hr.page.time_clock_adjustment.time_clock_adjustment.get_adjustments",
			args: { status: this.status, department: this.department || undefined },
			callback(r) {
				$list.removeClass("is-loading");
				me.payload = r.message || { rows: [], departments: [] };
				me.set_department_options(me.payload);
				me.render_rows();
			},
			error() {
				$list.removeClass("is-loading");
				me.payload = { rows: [], departments: [] };
				me.$body.find(".sp-tca__totals").empty();
				$list.html(`<div class="sp-tca__empty"><p>${me.escape(__("Could not load time clock adjustments."))}</p></div>`);
			},
		});
	},

	filtered_rows() {
		return (this.payload?.rows || []).filter((row) => {
			if (!this.department) {
				return true;
			}
			return row.department === this.department;
		});
	},

	render_rows() {
		const $list = this.$body.find(".sp-tca__list");
		const rows = this.filtered_rows();
		const pending = rows.filter((row) => row.status === "Pending").length;
		this.$body.find(".sp-tca__totals").html(`
			<span><strong>${this.escape(__("Total"))}:</strong> ${rows.length}</span>
			<span><strong>${this.escape(__("Pending"))}:</strong> ${pending}</span>
		`);
		if (!rows.length) {
			$list.html(`<div class="sp-tca__empty"><p>${this.escape(__("No time clock adjustments for this filter."))}</p></div>`);
			return;
		}
		$list.html(
			rows
				.map((row) => {
					const actions =
						row.status === "Pending" && hrms.time?.render_adjustment_actions
							? hrms.time.render_adjustment_actions(row)
							: `<span class="sp-tca__status">${this.escape(__(row.status || ""))}</span>`;
					return `
						<div class="sp-tca__row" data-name="${this.escape(row.name || "")}">
							<span>
								<strong>${this.escape(row.employee_name || row.employee || "")}</strong>
								${row.department ? `<span class="sp-tca__dept">${this.escape(row.department)}</span>` : ""}
							</span>
							<span>${this.escape(row.attendance_date ? frappe.datetime.str_to_user(row.attendance_date) : "")}</span>
							<span>${this.escape(this.range(row.current_in_time, row.current_out_time))}</span>
							<span class="sp-tca__requested">${this.escape(this.range(row.requested_in_time, row.requested_out_time))}</span>
							<span class="sp-tca__note">${this.escape(row.note || "")}</span>
							<span>${this.escape(__(row.status || ""))}</span>
							<span class="sp-tca__actions">${actions}</span>
						</div>`;
				})
				.join(""),
		);
	},
};
