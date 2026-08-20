frappe.provide("hrms");

frappe.pages["day-view"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Day View"),
		single_column: true,
	});
	frappe.breadcrumbs.add("HR");
	hrms.day_view.make(page);
};

frappe.pages["day-view"].on_page_show = function () {
	hrms.day_view.refresh();
};

hrms.day_view = {
	page: null,
	$body: null,
	rows: [],
	totals: {},
	approval: "",
	presets: {},
	employees: [],
	departments: [],
	from_date: "",
	to_date: "",
	employee: "",
	department: "",
	group_by_date: false,
	range_key: "this_week",
	last_people: [],

	make(page) {
		this.page = page;
		const $existing = page.main.find(".sp-dayview");
		if ($existing.length && $existing.find(".sp-dayview__btn-clock").length) {
			this.$body = $existing;
			return;
		}
		$existing.remove();
		this.$body = $('<div class="sp-dayview"></div>').appendTo(page.main);
		this.render_shell();
		this.bind();
		this.paint();
		this.boot();
	},

	render_shell() {
		const today = frappe.datetime.get_today();
		this.from_date = today;
		this.to_date = today;
		this.$body.html(`
			<div class="sp-dayview__toolbar">
				<label class="sp-dayview__date">
					<input type="date" class="sp-dayview__from" value="${frappe.utils.escape_html(today)}" />
				</label>
				<label class="sp-dayview__date">
					<input type="date" class="sp-dayview__to" value="${frappe.utils.escape_html(today)}" />
				</label>
				<div class="sp-dayview__quick">
					<button type="button" class="sp-dayview__quick-btn" aria-haspopup="listbox">${frappe.utils.escape_html(__("Quick Dates"))}</button>
					<div class="sp-dayview__quick-menu" hidden>
						<button type="button" data-range="today">${frappe.utils.escape_html(__("Today"))}</button>
						<button type="button" data-range="this_week">${frappe.utils.escape_html(__("This Week"))}</button>
						<button type="button" data-range="last_week">${frappe.utils.escape_html(__("Last Week"))}</button>
						<button type="button" data-range="this_month">${frappe.utils.escape_html(__("This Month"))}</button>
						<hr />
						<button type="button" data-range="previous_pay_period">${frappe.utils.escape_html(__("Previous Pay Period"))}</button>
						<button type="button" data-range="current_pay_period">${frappe.utils.escape_html(__("Current Pay Period"))}</button>
					</div>
				</div>
				<select class="sp-dayview__select sp-dayview__department" aria-label="${frappe.utils.escape_html(__("Department"))}">
					<option value="">${frappe.utils.escape_html(__("All Departments"))}</option>
				</select>
				<select class="sp-dayview__select sp-dayview__employee" aria-label="${frappe.utils.escape_html(__("Employee"))}">
					<option value="">${frappe.utils.escape_html(__("All Agents"))}</option>
				</select>
				<button type="button" class="sp-dayview__btn-approve">${frappe.utils.escape_html(__("Approve"))}</button>
				<button type="button" class="sp-dayview__btn-delete">${frappe.utils.escape_html(__("Delete Selected"))}</button>
				<button type="button" class="sp-clock-btn sp-dayview__btn-clock">${frappe.utils.escape_html(__("CLOCK"))}</button>
				<span class="sp-dayview__status" aria-live="polite"></span>
				<label class="sp-dayview__group">
					<input type="checkbox" class="sp-dayview__group-by" />
					${frappe.utils.escape_html(__("Group by Date"))}
				</label>
			</div>
			<div class="sp-dayview__board"></div>
			<div class="sp-dayview__summary"></div>
		`);
	},

	bind() {
		const me = this;
		this.$body.on("change", ".sp-dayview__from, .sp-dayview__to", function () {
			me.range_key = "custom";
			me.from_date = me.$body.find(".sp-dayview__from").val();
			me.to_date = me.$body.find(".sp-dayview__to").val();
			me.refresh();
		});
		this.$body.on("click", ".sp-dayview__quick-btn", function (event) {
			event.stopPropagation();
			const $menu = me.$body.find(".sp-dayview__quick-menu");
			$menu.prop("hidden", !$menu.prop("hidden"));
			me.$body.find(".sp-dayview__quick").toggleClass("is-open", !$menu.prop("hidden"));
		});
		this.$body.on("click", ".sp-dayview__quick-menu [data-range]", function (event) {
			event.stopPropagation();
			me.set_range($(this).data("range"));
		});
		$(document)
			.off("click.sp-dayview-quick")
			.on("click.sp-dayview-quick", () => me.close_quick());
		this.$body.on("change", ".sp-dayview__department", function () {
			me.department = $(this).val() || "";
			me.paint_employees();
			me.refresh();
		});
		this.$body.on("change", ".sp-dayview__employee", function () {
			me.employee = $(this).val() || "";
			me.refresh();
		});
		this.$body.on("change", ".sp-dayview__group-by", function () {
			me.group_by_date = this.checked;
			me.paint();
		});
		this.$body.on("change", ".sp-dayview__check-all", function () {
			me.$body.find(".sp-dayview__check:not(:disabled)").prop("checked", this.checked);
		});
		this.$body.on("click", ".sp-dayview__btn-approve", () => me.approve_selected());
		this.$body.on("click", ".sp-dayview__btn-delete", () => me.delete_selected());
		this.$body.on("click", ".sp-dayview__btn-clock", () => me.open_clock());
		this.$body.on("click", ".sp-dayview__link", function () {
			const $btn = $(this);
			const $row = $btn.closest(".sp-dayview__row");
			const act = $btn.data("act");
			const date = $btn.data("date");
			const employee = $btn.data("employee");
			const name = $btn.attr("data-name") || $row.attr("data-name");
			const in_log = $row.attr("data-in-log") || null;
			const out_log = $row.attr("data-out-log") || null;
			const kind = $row.attr("data-kind");
			if (act === "add") {
				me.add_entry(date, employee);
				return;
			}
			if (kind === "lunch") {
				return;
			}
			if (act === "edit" && name) {
				hrms.time.show_edit_entry_dialog(me.listview_stub(), name, { in_log, out_log });
				return;
			}
			if (act === "del" && name) {
				frappe.confirm(__("Remove this hours entry?"), () => {
					frappe.call({
						method: "hrms.hr.doctype.attendance.attendance.cancel_hours_entry",
						args: { name, in_log, out_log },
						callback() {
							me.refresh();
						},
					});
				});
			}
		});
	},

	boot() {
		const me = this;
		frappe.call({
			method: "hrms.hr.doctype.attendance.attendance.get_hours_date_presets",
			callback(r) {
				me.presets = r.message || me.local_presets();
				me.set_range("this_week");
			},
			error() {
				me.presets = me.local_presets();
				me.set_range("this_week");
			},
		});
		frappe.call({
			method: "hrms.hr.doctype.attendance.attendance.get_hours_filter_options",
			callback(r) {
				me.employees = r.message?.employees || [];
				me.departments = r.message?.departments || [];
				me.paint_departments();
				const user_employee = me.employees.find((row) => row.user_id === frappe.session.user);
				if (user_employee) {
					me.employee = user_employee.name;
				}
				me.paint_employees();
				me.refresh();
			},
		});
	},

	local_presets() {
		const fmt = (m) => m.format("YYYY-MM-DD");
		const today = moment();
		return {
			today: [fmt(today), fmt(today)],
			this_week: [fmt(today.clone().startOf("week")), fmt(today.clone().endOf("week"))],
			last_week: [
				fmt(today.clone().subtract(1, "week").startOf("week")),
				fmt(today.clone().subtract(1, "week").endOf("week")),
			],
			this_month: [fmt(today.clone().startOf("month")), fmt(today.clone().endOf("month"))],
		};
	},

	close_quick() {
		this.$body.find(".sp-dayview__quick-menu").prop("hidden", true);
		this.$body.find(".sp-dayview__quick").removeClass("is-open");
	},

	set_range(key, skip_refresh) {
		this.range_key = key;
		this.close_quick();
		const range = this.presets[key];
		if (range) {
			this.from_date = range[0];
			this.to_date = range[1];
			this.$body.find(".sp-dayview__from").val(this.from_date);
			this.$body.find(".sp-dayview__to").val(this.to_date);
		}
		this.$body.find(".sp-dayview__quick-menu [data-range]").removeClass("is-selected");
		this.$body.find(`.sp-dayview__quick-menu [data-range="${key}"]`).addClass("is-selected");
		if (!skip_refresh) this.refresh();
	},

	paint_departments() {
		const $select = this.$body.find(".sp-dayview__department");
		const current = this.department;
		$select.find("option:not(:first)").remove();
		this.departments.forEach((row) => {
			$select.append(
				`<option value="${frappe.utils.escape_html(row.name)}">${frappe.utils.escape_html(row.name)}</option>`,
			);
		});
		$select.val(current);
	},

	paint_employees() {
		const $select = this.$body.find(".sp-dayview__employee");
		const visible = this.employees.filter(
			(row) => !this.department || row.department === this.department,
		);
		const current = visible.some((row) => row.name === this.employee) ? this.employee : "";
		this.employee = current;
		$select.html(`<option value="">${frappe.utils.escape_html(__("All Agents"))}</option>`);
		visible
			.slice()
			.sort((a, b) =>
				this.employee_label(a).localeCompare(this.employee_label(b), undefined, {
					sensitivity: "base",
				}),
			)
			.forEach((row) => {
				$select.append(
					`<option value="${frappe.utils.escape_html(row.name)}">${frappe.utils.escape_html(
						this.employee_label(row),
					)}</option>`,
				);
			});
		$select.val(current);
	},

	employee_label(row) {
		if (hrms.time?.employee_label) return hrms.time.employee_label(row);
		return row.employee_name || row.name || "";
	},

	refresh() {
		if (!this.$body) return;
		this.from_date = this.$body.find(".sp-dayview__from").val() || frappe.datetime.get_today();
		this.to_date = this.$body.find(".sp-dayview__to").val() || this.from_date;
		if (this.from_date > this.to_date) {
			const swap = this.from_date;
			this.from_date = this.to_date;
			this.to_date = swap;
			this.$body.find(".sp-dayview__from").val(this.from_date);
			this.$body.find(".sp-dayview__to").val(this.to_date);
		}
		frappe.call({
			method: "hrms.hr.doctype.attendance.attendance.get_hours_rows",
			args: {
				from_date: this.from_date,
				to_date: this.to_date,
				employee: this.employee || "",
				department: this.department || "",
			},
			callback: (r) => {
				this.rows = r.message?.rows || [];
				this.totals = r.message?.totals || {};
				this.approval = r.message?.approval || "";
				this.paint();
			},
			error: () => {
				this.$body.find(".sp-dayview__status").text(__("Could not load hours."));
			},
		});
	},

	paint() {
		this.$body.find(".sp-dayview__status").text(this.approval ? __(this.approval) : "");
		const groups = this.build_groups();
		this.$body.find(".sp-dayview__board").html(groups.map((group) => this.render_group(group)).join(""));
		this.paint_job_summary();
	},

	people_to_show() {
		if (this.employee) {
			const match = this.employees.find((row) => row.name === this.employee);
			const people = [
				match || {
					name: this.employee,
					employee_name: this.employee,
				},
			];
			this.last_people = people;
			return people;
		}

		const in_scope = this.employees.filter(
			(row) => !this.department || row.department === this.department,
		);
		if (this.department && in_scope.length) {
			this.last_people = in_scope;
			return in_scope;
		}

		const with_hours = new Set((this.rows || []).map((row) => row.employee).filter(Boolean));
		const listed = in_scope.filter((row) => with_hours.has(row.name));
		if (listed.length) {
			this.last_people = listed;
			return listed;
		}
		if (this.last_people.length) {
			return this.last_people;
		}
		return [
			{
				name: "",
				employee_name: this.summary_scope_label(),
			},
		];
	},

	build_groups() {
		if (this.group_by_date) {
			return this.date_groups();
		}
		const by_employee = {};
		this.people_to_show().forEach((person) => {
			const name = person.name || "";
			by_employee[name] = {
				employee: name,
				label: this.employee_label(person),
				rows: [],
			};
		});
		this.rows.forEach((row) => {
			const name = row.employee || "";
			if (!by_employee[name]) {
				by_employee[name] = {
					employee: name,
					label: row.employee_label || row.employee_name || name,
					rows: [],
				};
			}
			by_employee[name].rows.push(row);
		});
		return Object.values(by_employee).sort((a, b) =>
			a.label.localeCompare(b.label, undefined, { sensitivity: "base" }),
		);
	},

	date_groups() {
		const dates = this.dates_in_range();
		const by_date = {};
		dates.forEach((date) => {
			by_date[date] = { date, rows: [] };
		});
		this.rows.forEach((row) => {
			const key = this.iso_date(row.attendance_date);
			if (!by_date[key]) by_date[key] = { date: key, rows: [] };
			by_date[key].rows.push(row);
		});
		return dates.map((date) => by_date[date]);
	},

	dates_in_range() {
		const dates = [];
		let cursor = moment(this.from_date);
		const end = moment(this.to_date);
		while (cursor.isSameOrBefore(end, "day")) {
			dates.push(cursor.format("YYYY-MM-DD"));
			cursor = cursor.clone().add(1, "day");
		}
		return dates;
	},

	iso_date(value) {
		return moment(value).isValid() ? moment(value).format("YYYY-MM-DD") : "";
	},

	render_group(group) {
		if (group.date) {
			return this.render_date_group(group);
		}
		return this.render_employee_group(group);
	},

	render_employee_group(group) {
		const by_date = {};
		group.rows.forEach((row) => {
			const key = this.iso_date(row.attendance_date);
			if (!by_date[key]) by_date[key] = [];
			by_date[key].push(row);
		});
		const dates = this.dates_in_range();
		const days = dates.map((date, index) => {
			const rows = by_date[date] || [null];
			return rows
				.map((row, row_index) => this.render_day_row(date, row, group.employee, row_index === 0, index))
				.join("");
		});
		const totals = this.sum_rows(group.rows);
		return `
			<section class="sp-dayview__person">
				<div class="sp-dayview__person-head">
					<strong>${frappe.utils.escape_html(group.label)}</strong>
					<span>${frappe.utils.escape_html(this.totals_label(totals))}</span>
				</div>
				${this.table_wrap(days.join(""), this.sum_rows(group.rows))}
			</section>`;
	},

	render_date_group(group) {
		const body = (group.rows.length
			? group.rows.map((row) =>
					this.render_day_row(this.iso_date(row.attendance_date), row, row.employee, false, 0, true),
				)
			: [this.render_day_row(group.date, null, this.employee || "", false, 0, false)]
		).join("");
		return `
			<section class="sp-dayview__person">
				<div class="sp-dayview__person-head">
					<strong>${frappe.utils.escape_html(this.date_label(group.date))}</strong>
					<span>${frappe.utils.escape_html(this.totals_label(this.sum_rows(group.rows)))}</span>
				</div>
				${this.table_wrap(body, this.sum_rows(group.rows))}
			</section>`;
	},

	table_wrap(body, totals) {
		const zero = {
			reg: 0,
			ot: 0,
			dt: 0,
			pto: 0,
			paid: 0,
			unpaid: 0,
			total: 0,
			daily_pay: 0,
			ss_deduction: 0,
			tax_deduction: 0,
			net_daily_pay: 0,
		};
		return `
			<div class="sp-dayview__table-wrap">
				<table class="sp-dayview__table">
					<thead>
						<tr>
							<th class="sp-dayview__check-col"><input type="checkbox" class="sp-dayview__check-all" /></th>
							<th class="sp-dayview__day-col"></th>
							<th>${frappe.utils.escape_html(__("Date"))}</th>
							<th>${frappe.utils.escape_html(__("In"))}</th>
							<th>${frappe.utils.escape_html(__("Out"))}</th>
							<th>${frappe.utils.escape_html(__("Reg"))}</th>
							<th>${frappe.utils.escape_html(__("OT"))}</th>
							<th>${frappe.utils.escape_html(__("DT"))}</th>
							<th>${frappe.utils.escape_html(__("PTO"))}</th>
							<th>${frappe.utils.escape_html(__("Paid"))}</th>
							<th>${frappe.utils.escape_html(__("Unpaid"))}</th>
							<th>${frappe.utils.escape_html(__("Total"))}</th>
							<th>${frappe.utils.escape_html(__("Gross"))}</th>
							<th>${frappe.utils.escape_html(__("Net"))}</th>
							<th>${frappe.utils.escape_html(__("SS"))}</th>
							<th>${frappe.utils.escape_html(__("Tax"))}</th>
							<th>${frappe.utils.escape_html(__("Job/Absence"))}</th>
							<th>${frappe.utils.escape_html(__("Shift"))}</th>
							<th></th>
						</tr>
					</thead>
					<tbody>${body}</tbody>
					<tfoot>
						<tr class="sp-dayview__foot sp-dayview__foot--blue">${this.total_cells(totals)}</tr>
						<tr class="sp-dayview__foot sp-dayview__foot--zero">${this.total_cells(zero)}</tr>
						<tr class="sp-dayview__foot sp-dayview__foot--gold">${this.total_cells(totals)}</tr>
					</tfoot>
				</table>
			</div>`;
	},

	render_day_row(date, row, employee, show_day, day_index, show_employee) {
		const moment_date = moment(date);
		const odd = day_index % 2 === 1;
		const name = row?.name || "";
		const kind = row?.kind || (row ? "attendance" : "");
		const is_lunch = kind === "lunch";
		const in_log = row?.in_log || "";
		const out_log = row?.out_log || "";
		const actions = name
			? `<button type="button" class="sp-dayview__link" data-act="add" data-date="${frappe.utils.escape_html(
					date,
				)}" data-employee="${frappe.utils.escape_html(employee)}">${frappe.utils.escape_html(__("add"))}</button>
				${
					is_lunch
						? ""
						: `<button type="button" class="sp-dayview__link" data-act="edit" data-name="${frappe.utils.escape_html(
								name,
							)}">${frappe.utils.escape_html(__("edit"))}</button>
				<button type="button" class="sp-dayview__link" data-act="del" data-name="${frappe.utils.escape_html(
					name,
				)}">${frappe.utils.escape_html(__("del"))}</button>`
				}`
			: `<button type="button" class="sp-dayview__link" data-act="add" data-date="${frappe.utils.escape_html(
					date,
				)}" data-employee="${frappe.utils.escape_html(employee)}">${frappe.utils.escape_html(__("add"))}</button>`;
		const comments = (row?.comments || [])
			.map(
				(comment) =>
					`<div class="sp-dayview__comment">${frappe.utils.escape_html(this.format_comment(comment))}</div>`,
			)
			.join("");
		const label = show_employee ? row.employee_label || row.employee_name || "" : this.date_label(date);
		const check_disabled = !name || is_lunch ? "disabled" : "";
		return `
			<tr class="sp-dayview__row${odd ? " is-alt" : ""}${row ? " has-entry" : ""}${
				is_lunch ? " is-lunch" : ""
			}" data-name="${frappe.utils.escape_html(name)}" data-kind="${frappe.utils.escape_html(
				kind,
			)}" data-in-log="${frappe.utils.escape_html(in_log)}" data-out-log="${frappe.utils.escape_html(out_log)}">
				<td class="sp-dayview__check-col">
					<input type="checkbox" class="sp-dayview__check" ${
						name && !is_lunch ? `value="${frappe.utils.escape_html(name)}"` : check_disabled
					} />
				</td>
				<td class="sp-dayview__day-col">${show_day ? frappe.utils.escape_html(moment_date.format("ddd")) : ""}</td>
				<td>
					${frappe.utils.escape_html(label)}
					${comments}
				</td>
				<td>${frappe.utils.escape_html(this.clock(row?.in_time))}</td>
				<td>${frappe.utils.escape_html(this.clock(row?.out_time))}</td>
				<td>${frappe.utils.escape_html(this.hours(row?.reg))}</td>
				<td>${frappe.utils.escape_html(this.hours(row?.ot))}</td>
				<td>${frappe.utils.escape_html(this.hours(row?.dt))}</td>
				<td>${frappe.utils.escape_html(this.hours(row?.pto))}</td>
				<td>${frappe.utils.escape_html(this.hours(row?.paid))}</td>
				<td>${frappe.utils.escape_html(this.hours(row?.unpaid))}</td>
				<td>${frappe.utils.escape_html(this.hours(this.entry_hours(row)))}</td>
				<td>${frappe.utils.escape_html(this.money(row?.daily_pay))}</td>
				<td>${frappe.utils.escape_html(this.money(row?.net_daily_pay))}</td>
				<td>${frappe.utils.escape_html(this.money(row?.ss_deduction))}</td>
				<td>${frappe.utils.escape_html(this.money(row?.tax_deduction))}</td>
				<td>${frappe.utils.escape_html(row?.job || "")}</td>
				<td>${frappe.utils.escape_html(row?.shift || "")}</td>
				<td class="sp-dayview__actions">${actions}</td>
			</tr>`;
	},

	total_cells(totals) {
		return `
			<td colspan="5"></td>
			<td>${frappe.utils.escape_html(this.hours(totals.reg, true))}</td>
			<td>${frappe.utils.escape_html(this.hours(totals.ot, true))}</td>
			<td>${frappe.utils.escape_html(this.hours(totals.dt, true))}</td>
			<td>${frappe.utils.escape_html(this.hours(totals.pto, true))}</td>
			<td>${frappe.utils.escape_html(this.hours(totals.paid, true))}</td>
			<td>${frappe.utils.escape_html(this.hours(totals.unpaid, true))}</td>
			<td>${frappe.utils.escape_html(this.hours(totals.total, true))}</td>
			<td>${frappe.utils.escape_html(this.money(totals.daily_pay, true))}</td>
			<td>${frappe.utils.escape_html(this.money(totals.net_daily_pay, true))}</td>
			<td>${frappe.utils.escape_html(this.money(totals.ss_deduction, true))}</td>
			<td>${frappe.utils.escape_html(this.money(totals.tax_deduction, true))}</td>
			<td colspan="3"></td>`;
	},

	sum_rows(rows) {
		const totals = {
			reg: 0,
			ot: 0,
			dt: 0,
			pto: 0,
			paid: 0,
			unpaid: 0,
			total: 0,
			daily_pay: 0,
			ss_deduction: 0,
			tax_deduction: 0,
			net_daily_pay: 0,
		};
		const seen_weeks = new Set();
		(rows || []).forEach((row) => {
			totals.reg += Number(row?.reg || 0);
			totals.ot += Number(row?.ot || 0);
			totals.dt += Number(row?.dt || 0);
			totals.pto += Number(row?.pto || 0);
			totals.paid += Number(row?.paid || 0);
			totals.unpaid += Number(row?.unpaid || 0);
			totals.total += Number(row?.total || this.entry_hours(row) || 0);
			totals.daily_pay += Number(row?.daily_pay || 0);
			const week_key = `${row?.employee || ""}|${row?.week_start || ""}`;
			if (row?.week_start && !seen_weeks.has(week_key)) {
				seen_weeks.add(week_key);
				totals.ss_deduction += Number(row.week_ss || 0);
				totals.tax_deduction += Number(row.week_tax || 0);
			}
		});
		totals.net_daily_pay = totals.daily_pay - totals.ss_deduction - totals.tax_deduction;
		return totals;
	},

	job_label(row) {
		const job = String(row?.job || "").trim();
		return job || __("NO JOB");
	},

	job_summaries() {
		const by_job = {};
		(this.rows || []).forEach((row) => {
			const job = this.job_label(row);
			if (!by_job[job]) {
				by_job[job] = { job, total: 0, reg: 0, ot: 0, dt: 0 };
			}
			by_job[job].total += Number(row.total || 0);
			by_job[job].reg += Number(row.reg || 0);
			by_job[job].ot += Number(row.ot || 0);
			by_job[job].dt += Number(row.dt || 0);
		});
		const no_job = __("NO JOB");
		return Object.values(by_job).sort((a, b) => {
			if (a.job === no_job) return -1;
			if (b.job === no_job) return 1;
			return a.job.localeCompare(b.job, undefined, { sensitivity: "base" });
		});
	},

	summary_scope_label() {
		return this.department || __("All Departments");
	},

	paint_job_summary() {
		const jobs = this.job_summaries();
		this.$body.find(".sp-dayview__summary").html(
			this.render_job_summary(
				jobs.length ? jobs : [{ job: __("NO JOB"), total: 0, reg: 0, ot: 0, dt: 0 }],
			),
		);
	},

	render_job_summary(jobs) {
		const rows = jobs
			.map(
				(job) => `
				<tr>
					<td>${frappe.utils.escape_html(job.job)}</td>
					<td class="sp-dayview__summary-hours">${frappe.utils.escape_html(this.hours(job.total, true))}</td>
					<td class="sp-dayview__summary-hours">${frappe.utils.escape_html(this.hours(job.reg, true))}</td>
					<td${Number(job.ot) ? ' class="sp-dayview__summary-hours"' : ""}>${frappe.utils.escape_html(this.hours(job.ot, true))}</td>
					<td${Number(job.dt) ? ' class="sp-dayview__summary-hours"' : ""}>${frappe.utils.escape_html(this.hours(job.dt, true))}</td>
				</tr>`,
			)
			.join("");
		return `
			<div class="sp-dayview__summary-head">${frappe.utils.escape_html(this.summary_scope_label())}</div>
			<table class="sp-dayview__summary-table">
				<thead>
					<tr>
						<th>${frappe.utils.escape_html(__("Hours for Job"))}</th>
						<th>${frappe.utils.escape_html(__("Totals"))}</th>
						<th>${frappe.utils.escape_html(__("Regular"))}</th>
						<th>${frappe.utils.escape_html(__("Overtime"))}</th>
						<th>${frappe.utils.escape_html(__("Doubletime"))}</th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>`;
	},

	totals_label(totals) {
		return __("Total Hours: {0} | Paid: {1} | Gross: {2} | Net: {3} | SS: {4} | Tax: {5}", [
			this.hours(totals.total, true),
			this.hours(totals.paid, true),
			this.money(totals.daily_pay, true),
			this.money(totals.net_daily_pay, true),
			this.money(totals.ss_deduction, true),
			this.money(totals.tax_deduction, true),
		]);
	},

	date_label(value) {
		const parsed = moment(value);
		return parsed.isValid() ? parsed.format("MM/DD") : value || "";
	},

	clock(value) {
		if (hrms.time?.format_clock) return hrms.time.format_clock(value);
		return value || "";
	},

	hours(value, keep_zero) {
		if (!keep_zero && !Number(value)) return "";
		if (hrms.time?.format_hours) return hrms.time.format_hours(value || 0);
		return value == null ? "" : String(value);
	},

	entry_hours(row) {
		if (!row) return 0;
		if (Number(row.total)) return row.total;
		if (Number(row.working_hours)) return row.working_hours;
		if (hrms.time?.hours_for_row) return hrms.time.hours_for_row(row);
		return 0;
	},

	money(value, keep_zero) {
		if (!keep_zero && !Number(value)) return "";
		const amount = Number(value || 0);
		if (format_currency) return format_currency(amount);
		return amount.toFixed(2);
	},

	format_comment(comment) {
		if (hrms.time) {
			const when = moment(comment.creation);
			const time = when.isValid() ? when.format("hh:mm A") : "";
			const date = when.isValid() ? when.format("MM/DD/YYYY") : "";
			return __("Comment ({0}, {1}, {2}): {3}", [
				comment.comment_by || __("Admin"),
				time,
				date,
				comment.content || "",
			]);
		}
		return comment.content || "";
	},

	selected_names() {
		return this.$body
			.find(".sp-dayview__check:checked")
			.map(function () {
				return this.value;
			})
			.get()
			.filter(Boolean);
	},

	approve_selected() {
		const selected = this.selected_names();
		const names = [
			...new Set(
				selected.length
					? selected
					: this.rows
							.filter((row) => row.name && row.kind !== "lunch" && !Number(row.hours_paid))
							.map((row) => row.name),
			),
		];
		if (!names.length) {
			frappe.msgprint(__("There is nothing to approve."));
			return;
		}
		frappe.call({
			method: "hrms.hr.doctype.attendance.attendance.approve_hours_entries",
			args: { names },
			freeze: true,
			callback: (r) => {
				const count = r.message?.approved?.length || 0;
				frappe.show_alert({
					message: count
						? __("{0} entries approved as paid hours", [count])
						: __("Nothing to approve"),
					indicator: "green",
				});
				this.refresh();
			},
		});
	},

	delete_selected() {
		const names = [...new Set(this.selected_names())];
		if (!names.length) {
			frappe.msgprint(__("Select at least one entry."));
			return;
		}
		frappe.confirm(__("Delete the selected hours entries?"), () => {
			frappe.call({
				method: "hrms.hr.doctype.attendance.attendance.cancel_hours_entries",
				args: { names },
				freeze: true,
				callback: () => this.refresh(),
			});
		});
	},

	add_entry(date, employee) {
		hrms.time.show_add_entry_dialog(this.listview_stub({ date, employee }));
	},

	open_clock() {
		if (hrms.time?.show_add_entry_dialog) {
			hrms.time.show_add_entry_dialog(this.listview_stub());
			return;
		}
		frappe.set_route("List", "Attendance");
	},

	listview_stub(extra = {}) {
		const from_date = extra.date || this.from_date;
		const to_date = extra.date || this.to_date;
		const employee = extra.employee || this.employee;
		const me = this;
		return {
			doctype: "Attendance",
			refresh() {
				me.refresh();
			},
			filter_area: {
				get() {
					const rows = [["Attendance", "attendance_date", "Between", [from_date, to_date]]];
					if (employee) rows.push(["Attendance", "employee", "=", employee]);
					if (me.department) rows.push(["Attendance", "department", "=", me.department]);
					return rows;
				},
			},
			page: { wrapper: me.$body, page_form: me.$body.find(".sp-dayview__toolbar") },
		};
	},
};
