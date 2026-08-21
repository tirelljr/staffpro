frappe.provide("hrms.ui");

frappe.pages["in-out-today"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Who Is In"),
		single_column: true,
	});

	frappe.breadcrumbs.add("HR");
	frappe.in_out_today.make(page);
};

frappe.pages["in-out-today"].on_page_show = function () {
	frappe.in_out_today.refresh();
};

frappe.in_out_today = {
	page: null,
	$body: null,
	payload: null,
	department: "",
	status: "all",

	make(page) {
		this.page = page;
		const $existing = page.main.find(".sp-inout-page");
		if ($existing.length && $existing.find(".sp-dash-inout").length && $existing.find(".sp-clock-btn").length) {
			this.$body = $existing;
			this.refresh();
			return;
		}
		$existing.remove();
		this.$body = $('<div class="sp-inout-page"></div>').appendTo(page.main);
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

	render_shell() {
		this.$body.html(`
			<section class="sp-dash-panel sp-dash-inout" aria-label="${this.escape(__("Who Is In"))}">
				<div class="sp-dash-panel__head">
					<h2 class="sp-dash-panel__title">${this.escape(__("Who Is In"))}</h2>
					<div class="sp-dash-panel__filters">
						<div class="sp-dash-panel__filter">
							${this.select_html(
								"sp-inout-dash__department",
								"outline",
								__("Department"),
								[{ value: "", label: __("All Departments") }],
								"",
							)}
						</div>
						<button type="button" class="sp-clock-btn">${this.escape(__("CLOCK"))}</button>
						<div class="sp-dash-panel__filter">
							${this.select_html(
								"sp-inout-dash__status",
								"solid",
								__("Status"),
								[
									{ value: "all", label: __("All") },
									{ value: "IN", label: __("IN") },
									{ value: "OUT", label: __("OUT") },
								],
								"all",
							)}
						</div>
						<button type="button" class="sp-inout-dash__open sp-inout-refresh">${this.escape(__("Refresh"))}</button>
					</div>
				</div>
				<div class="sp-inout-dash__totals" aria-live="polite"></div>
				<div class="sp-inout-dash__summary"></div>
				<div class="sp-inout-dash__table-wrap">
					<div class="sp-inout-dash__table-head">
						<span>${this.escape(__("Name"))}</span>
						<span>${this.escape(__("In / Out"))}</span>
						<span>${this.escape(__("Time"))}</span>
						<span>${this.escape(__("Job / Pto Code"))}</span>
						<span>${this.escape(__("Device ID"))}</span>
					</div>
					<div class="sp-inout-dash__list"></div>
				</div>
			</section>
		`);
		if (hrms.ui && typeof hrms.ui.bind_dash_selects === "function") {
			hrms.ui.bind_dash_selects(this.$body);
		}
	},

	bind() {
		const me = this;
		this.$body.on("click", ".sp-inout-refresh", () => me.refresh());
		this.$body.on("click", ".sp-clock-btn", () => me.open_clock());
		this.$body.on("change", ".sp-inout-dash__department", function () {
			me.department = $(this).val() || "";
			me.render_panel();
		});
		this.$body.on("change", ".sp-inout-dash__status", function () {
			me.status = $(this).val() || "all";
			me.render_rows();
		});
		this.$body.on("click", ".sp-inout-dash__row", function () {
			const employee = $(this).data("employee");
			if (employee) {
				frappe.set_route("Form", "Employee", employee);
			}
		});
	},

	open_clock() {
		if (!hrms.time?.show_add_entry_dialog) {
			hrms.time?.go_attendance_portal?.();
			return;
		}
		const me = this;
		const department = this.department && this.department !== "__none__" ? this.department : "";
		hrms.time.show_add_entry_dialog(
			{
				doctype: "Attendance",
				refresh() {
					me.refresh();
				},
				filter_area: {
					get() {
						return department ? [["Attendance", "department", "=", department]] : [];
					},
				},
				page: { wrapper: me.$body, page_form: me.$body.find(".sp-dash-panel__filters") },
			},
			{ department },
		);
	},

	department_options(payload) {
		const options = [{ value: "", label: __("All Departments") }];
		(payload.departments || []).forEach((name) => options.push({ value: name, label: name }));
		if ((payload.details || []).some((row) => !row.department)) {
			options.push({ value: "__none__", label: __("No Department") });
		}
		return options;
	},

	set_department_options(payload) {
		const $select = this.$body.find(".sp-inout-dash__department");
		const options = this.department_options(payload);
		if (hrms.ui && typeof hrms.ui.set_dash_select_options === "function") {
			this.department = hrms.ui.set_dash_select_options($select, options) || "";
			return;
		}
		const current = $select.val() || "";
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
		const $list = this.$body.find(".sp-inout-dash__list");
		$list.addClass("is-loading");
		frappe.call({
			method: "hrms.hr.page.in_out_today.in_out_today.get_in_out_today",
			callback(r) {
				$list.removeClass("is-loading");
				me.payload = r.message || { departments: [], totals: {}, summary: [], details: [] };
				me.set_department_options(me.payload);
				me.render_panel();
			},
			error() {
				$list.removeClass("is-loading");
				me.payload = { departments: [], totals: {}, summary: [], details: [] };
				me.$body.find(".sp-inout-dash__totals").empty();
				me.$body.find(".sp-inout-dash__summary").empty().hide();
				$list.html(me.empty_html(__("Could not load today's timeclock.")));
			},
		});
	},

	matches_department(row) {
		if (!this.department) {
			return true;
		}
		if (this.department === "__none__") {
			return !row.department;
		}
		return row.department === this.department;
	},

	scoped_rows() {
		return (this.payload?.details || []).filter((row) => this.matches_department(row));
	},

	filtered_rows() {
		const rows = this.scoped_rows();
		if (this.status === "all") {
			return rows;
		}
		return rows.filter((row) => row.status === this.status);
	},

	render_panel() {
		this.render_totals();
		this.render_summary();
		this.render_rows();
	},

	render_totals() {
		const rows = this.scoped_rows();
		const totals = {
			total: rows.length,
			in_count: rows.filter((row) => row.status === "IN").length,
			out_count: rows.filter((row) => row.status === "OUT").length,
			late: rows.filter((row) => row.late).length,
		};
		this.$body.find(".sp-inout-dash__totals").html(`
			<span><strong>${this.escape(__("Total"))}:</strong> ${totals.total}</span>
			<span><strong>${this.escape(__("IN"))}:</strong> ${totals.in_count}</span>
			<span><strong>${this.escape(__("OUT"))}:</strong> ${totals.out_count}</span>
			<span><strong>${this.escape(__("Late"))}:</strong> ${totals.late}</span>
		`);
	},

	render_summary() {
		const $summary = this.$body.find(".sp-inout-dash__summary");
		const rows = (this.payload?.summary || []).filter((row) => {
			if (!this.department) {
				return true;
			}
			if (this.department === "__none__") {
				return row.department === __("No Department");
			}
			return row.department === this.department;
		});
		if (!rows.length) {
			$summary.empty().hide();
			return;
		}
		$summary
			.html(
				`
			<table class="sp-inout-dash__summary-table">
				<thead>
					<tr>
						<th>${this.escape(__("Department"))}</th>
						<th>${this.escape(__("Employees"))}</th>
						<th>${this.escape(__("IN"))}</th>
						<th>${this.escape(__("OUT"))}</th>
					</tr>
				</thead>
				<tbody>
					${rows
						.map(
							(row) => `
						<tr>
							<td>${this.escape(row.department || __("No Department"))}</td>
							<td>${Number(row.employees || 0)}</td>
							<td>${Number(row.in_count || 0)}</td>
							<td>${Number(row.out_count || 0)}</td>
						</tr>`,
						)
						.join("")}
				</tbody>
			</table>
		`,
			)
			.show();
	},

	status_label(row) {
		if (row.late) {
			return __("LATE");
		}
		return row.status || __("OUT");
	},

	status_class(row) {
		if (row.late) {
			return "is-late";
		}
		if (row.status === "IN") {
			return "is-in";
		}
		return "is-out";
	},

	empty_html(message) {
		return `
			<div class="sp-inout-dash__empty">
				<p>${this.escape(message)}</p>
			</div>
		`;
	},

	render_rows() {
		const $list = this.$body.find(".sp-inout-dash__list");
		const rows = this.filtered_rows();
		if (!rows.length) {
			$list.html(this.empty_html(__("No agents to show for this filter.")));
			return;
		}
		$list.html(
			rows
				.map(
					(row) => `
				<button type="button" class="sp-inout-dash__row" data-employee="${this.escape(row.employee)}">
					<span class="sp-inout-dash__agent">
						<span class="sp-inout-dash__avatar">${this.avatar(row)}</span>
						<span class="sp-inout-dash__agent-meta">
							<span class="sp-inout-dash__name">${this.escape(row.employee_name || row.employee || "")}</span>
							${row.department ? `<span class="sp-inout-dash__dept">${this.escape(row.department)}</span>` : ""}
						</span>
					</span>
					<span class="sp-inout-dash__status-pill ${this.status_class(row)}">${this.escape(this.status_label(row))}</span>
					<span class="sp-inout-dash__time">${this.escape(row.time || "—")}</span>
					<span class="sp-inout-dash__pto">${this.escape(row.pto_code || "—")}</span>
					<span class="sp-inout-dash__device">${this.escape(row.device_id || "—")}</span>
				</button>
			`,
				)
				.join(""),
		);
	},
};
