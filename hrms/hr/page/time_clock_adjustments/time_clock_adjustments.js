frappe.provide("hrms.ui");

const TCA_PAGE_SIZE = 9;
const TCA_STATUS_OPTIONS = ["Pending", "Approved", "Rejected", "All"];

frappe.pages["time-clock-adjustments"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Time Clock Adjustment"),
		single_column: true,
	});

	frappe.breadcrumbs.add("HR");
	frappe.time_clock_adjustments.make(page);
};

frappe.pages["time-clock-adjustments"].on_page_show = function () {
	frappe.time_clock_adjustments.refresh();
};

frappe.time_clock_adjustments = {
	page: null,
	$body: null,
	payload: null,
	status: "Pending",
	department: "",
	date: "",
	query: "",
	current_page: 1,

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

	select_html() {
		const options = [{ value: "", label: __("All Departments") }];
		if (hrms.ui?.dash_select_html) {
			return hrms.ui.dash_select_html({
				className: "sp-tca__department",
				variant: "outline",
				label: __("Department"),
				options,
				value: "",
			});
		}
		return `
			<select class="sp-tca__department" aria-label="${this.escape(__("Department"))}">
				<option value="">${this.escape(__("All Departments"))}</option>
			</select>`;
	},

	render_shell() {
		const search_icon = `
			<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
				<circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="1.8"></circle>
				<path d="m16 16 4 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path>
			</svg>`;
		const filter_icon = `
			<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
				<path d="M4 7h16M7 12h10M10 17h4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path>
			</svg>`;
		const calendar_icon = `
			<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
				<rect x="3.5" y="5" width="17" height="15" rx="2" stroke="currentColor" stroke-width="1.6"></rect>
				<path d="M8 3v4M16 3v4M3.5 9h17" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"></path>
			</svg>`;

		this.$body.html(`
			<section class="sp-tca-panel" aria-label="${this.escape(__("Time Clock Adjustment"))}">
				<div class="sp-attendance__card sp-tca__card">
					<div class="sp-attendance__toolbar sp-tca__toolbar">
						<label class="sp-attendance__search">
							<span class="sp-attendance__search-icon">${search_icon}</span>
							<input type="search" class="sp-attendance__search-input sp-tca__search"
								placeholder="${this.escape(__("Search by name, role, department..."))}" autocomplete="off">
							<button type="button" class="sp-attendance__search-clear sp-tca__search-clear" hidden
								aria-label="${this.escape(__("Clear search"))}">×</button>
						</label>
						<div class="sp-attendance__filter">
							<button type="button" class="sp-attendance__filter-btn sp-tca__filter-btn"
								aria-haspopup="listbox" aria-expanded="false">
								${filter_icon}
								<span class="sp-tca__filter-label">${this.escape(__("Pending"))}</span>
							</button>
							<div class="sp-attendance__filter-menu sp-tca__filter-menu" hidden role="listbox">
								${TCA_STATUS_OPTIONS.map(
									(status) => `
										<button type="button" class="sp-attendance__filter-option sp-tca__filter-option${
											status === this.status ? " is-selected" : ""
										}" data-value="${this.escape(status)}" role="option">
											${this.escape(__(status))}
										</button>`,
								).join("")}
							</div>
						</div>
						<div class="sp-attendance__toolbar-end">
							<div class="sp-attendance__field">${this.select_html()}</div>
							<label class="sp-attendance__date sp-tca__date">
								<span class="sp-attendance__date-icon">${calendar_icon}</span>
								<input type="date" class="sp-tca__date-input" aria-label="${this.escape(__("Date"))}">
								<button type="button" class="sp-tca__date-clear" hidden
									aria-label="${this.escape(__("Clear date"))}">×</button>
							</label>
						</div>
					</div>
					<div class="sp-tca__summary" aria-live="polite"></div>
					<div class="sp-attendance__table-wrap">
						<div class="sp-tca__table-head">
							<span>${this.escape(__("Date"))}</span>
							<span>${this.escape(__("Employee"))}</span>
							<span>${this.escape(__("Role"))}</span>
							<span>${this.escape(__("Employment type"))}</span>
							<span>${this.escape(__("Status"))}</span>
							<span>${this.escape(__("Check In"))}</span>
							<span>${this.escape(__("Check Out"))}</span>
							<span>${this.escape(__("Hours"))}</span>
							<span>${this.escape(__("Actions"))}</span>
						</div>
						<div class="sp-tca__list"></div>
					</div>
					<div class="sp-attendance__pager sp-tca__pager">
						<button type="button" class="sp-attendance__pager-btn sp-tca__prev">${this.escape(__("Previous"))}</button>
						<span class="sp-attendance__pager-label sp-tca__pager-label"></span>
						<button type="button" class="sp-attendance__pager-btn sp-tca__next">${this.escape(__("Next"))}</button>
					</div>
				</div>
			</section>
		`);
		if (hrms.ui?.bind_dash_selects) {
			hrms.ui.bind_dash_selects(this.$body);
		}
	},

	bind() {
		const me = this;
		this.$body.on("input", ".sp-tca__search", function () {
			me.query = String($(this).val() || "").trim().toLowerCase();
			me.current_page = 1;
			me.$body.find(".sp-tca__search-clear").prop("hidden", !me.query);
			me.render_rows();
		});
		this.$body.on("click", ".sp-tca__search-clear", () => {
			this.query = "";
			this.current_page = 1;
			this.$body.find(".sp-tca__search").val("").trigger("focus");
			this.$body.find(".sp-tca__search-clear").prop("hidden", true);
			this.render_rows();
		});
		this.$body.on("click", ".sp-tca__filter-btn", function () {
			const $menu = me.$body.find(".sp-tca__filter-menu");
			const will_open = $menu.prop("hidden");
			$menu.prop("hidden", !will_open);
			$(this).attr("aria-expanded", will_open ? "true" : "false");
		});
		this.$body.on("click", ".sp-tca__filter-option", function () {
			me.status = $(this).data("value") || "Pending";
			me.current_page = 1;
			me.$body.find(".sp-tca__filter-label").text(__(me.status));
			me.$body.find(".sp-tca__filter-option").removeClass("is-selected");
			$(this).addClass("is-selected");
			me.$body.find(".sp-tca__filter-menu").prop("hidden", true);
			me.$body.find(".sp-tca__filter-btn").attr("aria-expanded", "false");
			me.refresh();
		});
		this.$body.on("change", ".sp-tca__department", function () {
			me.department = $(this).val() || "";
			me.current_page = 1;
			me.refresh();
		});
		this.$body.on("change", ".sp-tca__date-input", function () {
			me.date = $(this).val() || "";
			me.current_page = 1;
			me.$body.find(".sp-tca__date-clear").prop("hidden", !me.date);
			me.refresh();
		});
		this.$body.on("click", ".sp-tca__date-clear", () => {
			this.date = "";
			this.current_page = 1;
			this.$body.find(".sp-tca__date-input").val("");
			this.$body.find(".sp-tca__date-clear").prop("hidden", true);
			this.refresh();
		});
		this.$body.on("click", ".sp-tca__prev", () => {
			if (this.current_page > 1) {
				this.current_page -= 1;
				this.render_rows();
			}
		});
		this.$body.on("click", ".sp-tca__next", () => {
			const pages = Math.max(1, Math.ceil(this.filtered_rows().length / TCA_PAGE_SIZE));
			if (this.current_page < pages) {
				this.current_page += 1;
				this.render_rows();
			}
		});
		if (hrms.time?.bind_adjustment_actions) {
			hrms.time.bind_adjustment_actions(this.$body, () => me.refresh());
		}
	},

	set_department_options(payload) {
		const options = [{ value: "", label: __("All Departments") }];
		(payload.departments || []).forEach((name) => options.push({ value: name, label: name }));
		const $select = this.$body.find(".sp-tca__department");
		if (hrms.ui?.set_dash_select_options) {
			this.department = hrms.ui.set_dash_select_options($select, options) || "";
			return;
		}
		$select.html(
			options
				.map(
					(option) =>
						`<option value="${this.escape(option.value)}">${this.escape(option.label)}</option>`,
				)
				.join(""),
		);
		$select.val(this.department);
	},

	refresh() {
		if (!this.$body) return;
		const $list = this.$body.find(".sp-tca__list");
		$list.addClass("is-loading");
		frappe.call({
			method: "hrms.hr.page.time_clock_adjustments.time_clock_adjustments.get_adjustments",
			args: {
				status: this.status,
				department: this.department || undefined,
				from_date: this.date || undefined,
				to_date: this.date || undefined,
			},
			callback: (response) => {
				$list.removeClass("is-loading");
				this.payload = response.message || { rows: [], departments: [] };
				this.set_department_options(this.payload);
				this.render_rows();
			},
			error: () => {
				$list.removeClass("is-loading");
				this.payload = { rows: [], departments: [] };
				this.render_rows();
			},
		});
	},

	filtered_rows() {
		const rows = this.payload?.rows || [];
		if (!this.query) return rows;
		return rows.filter((row) => {
			const haystack = [
				row.employee_name,
				row.employee,
				row.designation,
				row.employment_type,
				row.department,
				row.note,
			]
				.filter(Boolean)
				.join(" ")
				.toLowerCase();
			return haystack.includes(this.query);
		});
	},

	initials(name) {
		return String(name || "")
			.trim()
			.split(/\s+/)
			.slice(0, 2)
			.map((part) => part.charAt(0))
			.join("")
			.toUpperCase();
	},

	avatar(row) {
		if (row.image) {
			return `<img class="sp-tca__avatar-img" src="${this.escape(row.image)}" alt="">`;
		}
		return `<span class="sp-tca__avatar-fallback">${this.escape(this.initials(row.employee_name))}</span>`;
	},

	clock(value) {
		if (hrms.time?.format_clock) {
			return hrms.time.format_clock(value) || "—";
		}
		return value || "—";
	},

	time_cell(requested, current) {
		const primary = this.clock(requested || current);
		const changed = requested && this.clock(requested) !== this.clock(current);
		return `
			<span class="sp-tca__time-primary">${this.escape(primary)}</span>
			${
				changed
					? `<span class="sp-tca__time-current">${this.escape(__("Was {0}", [this.clock(current)]))}</span>`
					: ""
			}`;
	},

	render_rows() {
		const rows = this.filtered_rows();
		const pages = Math.max(1, Math.ceil(rows.length / TCA_PAGE_SIZE));
		this.current_page = Math.min(Math.max(this.current_page, 1), pages);
		const start = (this.current_page - 1) * TCA_PAGE_SIZE;
		const visible = rows.slice(start, start + TCA_PAGE_SIZE);
		const pending = rows.filter((row) => row.status === "Pending").length;

		this.$body
			.find(".sp-tca__summary")
			.text(__("{0} requests · {1} pending", [rows.length, pending]));
		this.$body
			.find(".sp-tca__pager-label")
			.text(__("Page {0} of {1}", [this.current_page, pages]));
		this.$body.find(".sp-tca__prev").prop("disabled", this.current_page <= 1);
		this.$body.find(".sp-tca__next").prop("disabled", this.current_page >= pages);
		this.$body.find(".sp-tca__pager").prop("hidden", rows.length <= TCA_PAGE_SIZE);

		if (!visible.length) {
			this.$body.find(".sp-tca__list").html(`
				<div class="sp-attendance__empty sp-tca__empty">
					<p>${this.escape(__("No time clock adjustments for this filter."))}</p>
				</div>`);
			return;
		}

		this.$body.find(".sp-tca__list").html(
			visible
				.map((row) => {
					const status = String(row.status || "Pending");
					const status_class = status.toLowerCase();
					const employment_type = row.employment_type || "—";
					const employment_class = employment_type.toLowerCase().replace(/[^a-z0-9]+/g, "-");
					const actions =
						status === "Pending" && hrms.time?.render_adjustment_actions
							? hrms.time.render_adjustment_actions(row)
							: '<span class="sp-tca__no-action">—</span>';
					return `
						<div class="sp-tca__row" data-name="${this.escape(row.name)}">
							<span class="sp-tca__date-cell">${this.escape(row.date_label || "")}</span>
							<span class="sp-tca__employee">
								<span class="sp-tca__avatar">${this.avatar(row)}</span>
								<span class="sp-tca__employee-copy">
									<strong>${this.escape(row.employee_name || row.employee || "")}</strong>
									${
										row.note
											? `<span class="sp-tca__note" title="${this.escape(row.note)}">${this.escape(row.note)}</span>`
											: ""
									}
								</span>
							</span>
							<span class="sp-tca__role">${this.escape(row.designation || "—")}</span>
							<span><span class="sp-tca__employment is-${this.escape(employment_class)}">${this.escape(
								employment_type.toUpperCase(),
							)}</span></span>
							<span><span class="sp-tca__status is-${this.escape(status_class)}">${this.escape(
								__(status),
							)}</span></span>
							<span class="sp-tca__time">${this.time_cell(row.requested_in_time, row.current_in_time)}</span>
							<span class="sp-tca__time">${this.time_cell(row.requested_out_time, row.current_out_time)}</span>
							<span class="sp-tca__hours">${this.escape(row.requested_hours_label || "—")}</span>
							<span class="sp-tca__actions">${actions}</span>
						</div>`;
				})
				.join(""),
		);
	},
};
