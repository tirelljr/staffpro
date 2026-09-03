frappe.provide("hrms");

frappe.pages["paid-time-off"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Paid Time Off"),
		single_column: true,
	});
	frappe.breadcrumbs.add("HR");
	hrms.paid_time_off.make(page);
};

frappe.pages["paid-time-off"].on_page_show = function () {
	hrms.paid_time_off.refresh();
};

hrms.paid_time_off = {
	page: null,
	$body: null,
	payload: null,
	employee: "",
	leave_type: "",
	busy: false,

	make(page) {
		this.page = page;
		const $existing = page.main.find(".sp-pto-page");
		if ($existing.length) {
			this.$body = $existing;
			this.refresh();
			return;
		}
		this.$body = $('<div class="sp-pto-page"></div>').appendTo(page.main);
		this.render_shell();
		this.bind();
		this.refresh();
	},

	escape(value) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
	},

	today() {
		return frappe.datetime.get_today();
	},

	render_shell() {
		const today = this.today();
		this.$body.html(`
			<section class="sp-dash-panel sp-pto-form" aria-label="${this.escape(__("Book Time Off"))}">
				<div class="sp-dash-panel__head">
					<h2 class="sp-dash-panel__title">${this.escape(__("Paid Time Off"))}</h2>
				</div>
				<p class="sp-pto-form__hint">${this.escape(__("Pick an agent, the days they will be out, and the reason. Their PTO balance updates here and on Upcoming Absences."))}</p>
				<div class="sp-pto-form__grid">
					<label class="sp-pto-field">
						<span>${this.escape(__("Agent"))}</span>
						<select class="sp-pto-agent" aria-label="${this.escape(__("Agent"))}">
							<option value="">${this.escape(__("Select agent"))}</option>
						</select>
					</label>
					<label class="sp-pto-field">
						<span>${this.escape(__("From"))}</span>
						<input type="date" class="sp-pto-from" value="${this.escape(today)}" />
					</label>
					<label class="sp-pto-field">
						<span>${this.escape(__("To"))}</span>
						<input type="date" class="sp-pto-to" value="${this.escape(today)}" />
					</label>
					<label class="sp-pto-field">
						<span>${this.escape(__("Reason"))}</span>
						<select class="sp-pto-reason" aria-label="${this.escape(__("Reason"))}">
							<option value="">${this.escape(__("Vacation, sick leave…"))}</option>
						</select>
					</label>
					<label class="sp-pto-field sp-pto-field--days">
						<span>${this.escape(__("Days to add"))}</span>
						<input type="number" class="sp-pto-days" min="0.5" step="0.5" value="10" />
					</label>
				</div>
				<div class="sp-pto-form__actions">
					<button type="button" class="sp-pto-allocate">${this.escape(__("Allocate PTO"))}</button>
					<button type="button" class="sp-pto-book">${this.escape(__("Book Time Off"))}</button>
				</div>
			</section>
			<section class="sp-dash-panel sp-pto-balance" aria-label="${this.escape(__("PTO Balance"))}">
				<div class="sp-dash-panel__head">
					<h2 class="sp-dash-panel__title">${this.escape(__("PTO Balance"))}</h2>
					<p class="sp-pto-period"></p>
				</div>
				<div class="sp-pto-table-wrap">
					<div class="sp-pto-table-head">
						<span>${this.escape(__("Leave Type"))}</span>
						<span>${this.escape(__("Agent"))}</span>
						<span>${this.escape(__("Opening"))}</span>
						<span>${this.escape(__("Allocated"))}</span>
						<span>${this.escape(__("Taken"))}</span>
						<span>${this.escape(__("Expired"))}</span>
						<span>${this.escape(__("Closing"))}</span>
					</div>
					<div class="sp-pto-balance-list"></div>
				</div>
			</section>
			<section class="sp-dash-panel sp-pto-absences" aria-label="${this.escape(__("Upcoming Absences"))}">
				<div class="sp-dash-panel__head">
					<h2 class="sp-dash-panel__title">${this.escape(__("Upcoming Absences"))}</h2>
				</div>
				<div class="sp-pto-table-wrap">
					<div class="sp-pto-absence-head">
						<span>${this.escape(__("Agent"))}</span>
						<span>${this.escape(__("Absence Type"))}</span>
						<span>${this.escape(__("Dates"))}</span>
						<span>${this.escape(__("Status"))}</span>
					</div>
					<div class="sp-pto-absence-list"></div>
				</div>
			</section>
		`);
	},

	bind() {
		const me = this;
		this.$body.on("change", ".sp-pto-agent", function () {
			me.employee = $(this).val() || "";
			me.refresh();
		});
		this.$body.on("change", ".sp-pto-reason", function () {
			me.leave_type = $(this).val() || "";
		});
		this.$body.on("change", ".sp-pto-from", function () {
			const from = $(this).val();
			const $to = me.$body.find(".sp-pto-to");
			if (from && (!$to.val() || $to.val() < from)) {
				$to.val(from);
			}
		});
		this.$body.on("click", ".sp-pto-book", () => me.book());
		this.$body.on("click", ".sp-pto-allocate", () => me.allocate());
		this.$body.on("click", ".sp-pto-balance-row, .sp-pto-absence-row", function () {
			const leave = $(this).data("leave");
			const employee = $(this).data("employee");
			if (leave) {
				frappe.set_route("Form", "Leave Application", leave);
				return;
			}
			if (employee) {
				frappe.set_route("Form", "Employee", employee);
			}
		});
	},

	form_values() {
		return {
			employee: this.$body.find(".sp-pto-agent").val() || this.employee,
			leave_type: this.$body.find(".sp-pto-reason").val() || this.leave_type,
			from_date: this.$body.find(".sp-pto-from").val(),
			to_date: this.$body.find(".sp-pto-to").val(),
			days: this.$body.find(".sp-pto-days").val(),
		};
	},

	require_form(need_days = false) {
		const values = this.form_values();
		if (!values.employee) {
			frappe.msgprint(__("Select an agent."));
			return null;
		}
		if (!values.leave_type) {
			frappe.msgprint(__("Select a reason."));
			return null;
		}
		if (need_days && (!values.days || Number(values.days) <= 0)) {
			frappe.msgprint(__("Enter how many PTO days to allocate."));
			return null;
		}
		return values;
	},

	set_busy(busy) {
		this.busy = busy;
		this.$body.find(".sp-pto-book, .sp-pto-allocate").prop("disabled", busy);
	},

	book() {
		if (this.busy) return;
		const values = this.require_form();
		if (!values) return;
		this.set_busy(true);
		frappe.call({
			method: "hrms.hr.page.paid_time_off.paid_time_off.book_time_off",
			args: {
				employee: values.employee,
				leave_type: values.leave_type,
				from_date: values.from_date,
				to_date: values.to_date || values.from_date,
			},
			callback: (r) => {
				this.set_busy(false);
				frappe.show_alert({ message: r.message?.message || __("Time off booked"), indicator: "green" });
				this.refresh();
			},
			error: () => this.set_busy(false),
		});
	},

	allocate() {
		if (this.busy) return;
		const values = this.require_form(true);
		if (!values) return;
		this.set_busy(true);
		frappe.call({
			method: "hrms.hr.page.paid_time_off.paid_time_off.allocate_pto",
			args: {
				employee: values.employee,
				leave_type: values.leave_type,
				days: values.days,
			},
			callback: (r) => {
				this.set_busy(false);
				frappe.show_alert({ message: r.message?.message || __("PTO allocated"), indicator: "green" });
				this.refresh();
			},
			error: () => this.set_busy(false),
		});
	},

	refresh() {
		if (!this.$body) return;
		this.employee = this.$body.find(".sp-pto-agent").val() || this.employee;
		this.leave_type = this.$body.find(".sp-pto-reason").val() || this.leave_type;
		this.$body.find(".sp-pto-balance-list, .sp-pto-absence-list").addClass("is-loading");
		frappe.call({
			method: "hrms.hr.page.paid_time_off.paid_time_off.get_page_context",
			args: { employee: this.employee || undefined },
			callback: (r) => {
				this.payload = r.message || {};
				this.paint();
			},
			error: () => {
				this.$body.find(".sp-pto-balance-list, .sp-pto-absence-list").removeClass("is-loading");
			},
		});
	},

	paint() {
		const data = this.payload || {};
		this.fill_select(
			this.$body.find(".sp-pto-agent"),
			(data.employees || []).map((row) => ({
				value: row.name,
				label: row.employee_name || row.name,
			})),
			this.employee,
			__("Select agent"),
		);
		this.fill_select(
			this.$body.find(".sp-pto-reason"),
			(data.leave_types || []).map((row) => ({
				value: row.name,
				label: row.leave_type_name || row.name,
			})),
			this.leave_type,
			__("Vacation, sick leave…"),
		);
		this.$body.find(".sp-pto-period").text(data.period_label || "");
		this.render_balances(data.balances || []);
		this.render_absences(data.absences || []);
	},

	fill_select($select, options, value, placeholder) {
		const current = value || $select.val() || "";
		const html = [`<option value="">${this.escape(placeholder)}</option>`]
			.concat(
				options.map(
					(opt) =>
						`<option value="${this.escape(opt.value)}"${opt.value === current ? " selected" : ""}>${this.escape(opt.label)}</option>`,
				),
			)
			.join("");
		$select.html(html);
		if (current && options.some((opt) => opt.value === current)) {
			$select.val(current);
		}
	},

	number(value) {
		const amount = Number(value || 0);
		if (!Number.isFinite(amount)) return "0";
		return amount.toLocaleString(undefined, { maximumFractionDigits: 2 });
	},

	empty_html(message) {
		return `<div class="sp-pto-empty"><p>${this.escape(message)}</p></div>`;
	},

	render_balances(rows) {
		const $list = this.$body.find(".sp-pto-balance-list").removeClass("is-loading");
		if (!rows.length) {
			$list.html(this.empty_html(__("No PTO balances yet. Allocate PTO to get started.")));
			return;
		}
		$list.html(
			rows
				.map(
					(row) => `
				<button type="button" class="sp-pto-balance-row" data-employee="${this.escape(row.employee || "")}">
					<span>${this.escape(row.leave_type || "—")}</span>
					<span>${this.escape(row.employee_name || row.employee || "—")}</span>
					<span>${this.escape(this.number(row.opening_balance))}</span>
					<span>${this.escape(this.number(row.leaves_allocated))}</span>
					<span>${this.escape(this.number(row.leaves_taken))}</span>
					<span>${this.escape(this.number(row.leaves_expired))}</span>
					<span>${this.escape(this.number(row.closing_balance))}</span>
				</button>`,
				)
				.join(""),
		);
	},

	render_absences(rows) {
		const $list = this.$body.find(".sp-pto-absence-list").removeClass("is-loading");
		if (!rows.length) {
			$list.html(this.empty_html(__("No upcoming time off for this selection.")));
			return;
		}
		$list.html(
			rows
				.map(
					(row) => `
				<button type="button" class="sp-pto-absence-row" data-employee="${this.escape(row.employee || "")}" data-leave="${this.escape(row.leave_application || "")}">
					<span>${this.escape(row.employee_name || row.employee || "—")}</span>
					<span>${this.escape(row.leave_type || "—")}</span>
					<span>${this.escape(row.date_label || "")}</span>
					<span class="sp-payroll__status sp-payroll__status--${this.escape(row.status_class || "open")}">
						<span class="sp-payroll__status-dot" aria-hidden="true"></span>
						<span class="sp-payroll__status-label">${this.escape(row.status_label || row.status || "")}</span>
					</span>
				</button>`,
				)
				.join(""),
		);
	},
};
