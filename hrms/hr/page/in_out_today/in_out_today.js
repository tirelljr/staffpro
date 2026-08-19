frappe.pages["in-out-today"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("In / Out today"),
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
	include_in: true,
	include_out: true,
	include_summary: true,

	make(page) {
		this.page = page;
		const $existing = page.main.find(".sp-inout-page");
		if ($existing.length) {
			this.$body = $existing;
			return;
		}
		this.$body = $('<div class="sp-inout-page"></div>').appendTo(page.main);
		this.render_shell();
		this.bind();
	},

	render_shell() {
		this.$body.html(`
			<div class="sp-inout-toolbar">
				<div class="sp-inout-dept">
					<button type="button" class="sp-inout-dept__toggle" aria-haspopup="listbox">
						<span class="sp-inout-dept__label">${frappe.utils.escape_html(__("All Departments"))}</span>
						<span class="sp-inout-dept__caret">▾</span>
					</button>
					<div class="sp-inout-dept__menu" hidden>
						<input type="search" class="sp-inout-dept__search" placeholder="${frappe.utils.escape_html(__("Search"))}" />
						<div class="sp-inout-dept__options" role="listbox"></div>
					</div>
				</div>
				<button type="button" class="btn btn-primary btn-sm sp-inout-refresh">${frappe.utils.escape_html(__("Refresh"))}</button>
				<label class="sp-inout-check">
					<input type="checkbox" class="sp-inout-include-in" checked />
					${frappe.utils.escape_html(__("Include IN"))}
				</label>
				<label class="sp-inout-check">
					<input type="checkbox" class="sp-inout-include-out" checked />
					${frappe.utils.escape_html(__("Include OUT"))}
				</label>
				<label class="sp-inout-check">
					<input type="checkbox" class="sp-inout-include-summary" checked />
					${frappe.utils.escape_html(__("Summary"))}
				</label>
				<div class="sp-inout-totals" aria-live="polite"></div>
			</div>
			<div class="sp-inout-summary-wrap"></div>
			<div class="sp-inout-detail-wrap"></div>
		`);
	},

	bind() {
		const me = this;
		this.$body.on("click", ".sp-inout-refresh", () => me.refresh());
		this.$body.on("change", ".sp-inout-include-in", function () {
			me.include_in = this.checked;
			me.render_tables();
		});
		this.$body.on("change", ".sp-inout-include-out", function () {
			me.include_out = this.checked;
			me.render_tables();
		});
		this.$body.on("change", ".sp-inout-include-summary", function () {
			me.include_summary = this.checked;
			me.render_tables();
		});
		this.$body.on("click", ".sp-inout-dept__toggle", (event) => {
			event.stopPropagation();
			me.toggle_dept_menu();
		});
		this.$body.on("input", ".sp-inout-dept__search", function () {
			me.render_dept_options(this.value);
		});
		this.$body.on("click", ".sp-inout-dept__option", function () {
			me.department = $(this).attr("data-department") || "";
			me.$body.find(".sp-inout-dept__label").text($(this).text());
			me.close_dept_menu();
			me.render_tables();
		});
		$(document)
			.off("click.in-out-today")
			.on("click.in-out-today", (event) => {
				if (!$(event.target).closest(".sp-inout-dept").length) {
					me.close_dept_menu();
				}
			});
	},

	toggle_dept_menu() {
		const $menu = this.$body.find(".sp-inout-dept__menu");
		if ($menu.prop("hidden")) {
			this.render_dept_options("");
			this.$body.find(".sp-inout-dept__search").val("");
			$menu.prop("hidden", false);
			this.$body.find(".sp-inout-dept__search").trigger("focus");
		} else {
			this.close_dept_menu();
		}
	},

	close_dept_menu() {
		this.$body.find(".sp-inout-dept__menu").prop("hidden", true);
	},

	render_dept_options(query) {
		const needle = (query || "").toLowerCase();
		const departments = (this.payload && this.payload.departments) || [];
		const options = [{ value: "", label: __("All Departments") }].concat(
			departments.map((name) => ({ value: name, label: name })),
		);
		const html = options
			.filter((option) => option.label.toLowerCase().includes(needle))
			.map((option) => {
				const selected = (this.department || "") === (option.value || "");
				return `<button type="button" class="sp-inout-dept__option${selected ? " is-selected" : ""}" data-department="${frappe.utils.escape_html(option.value)}">${frappe.utils.escape_html(option.label)}</button>`;
			})
			.join("");
		this.$body.find(".sp-inout-dept__options").html(html || `<div class="sp-inout-empty">${frappe.utils.escape_html(__("No departments"))}</div>`);
	},

	refresh() {
		const me = this;
		if (!this.$body) {
			return;
		}
		this.$body.addClass("is-loading");
		return frappe
			.call({
				method: "hrms.hr.page.in_out_today.in_out_today.get_in_out_today",
				freeze: true,
				freeze_message: __("Loading today's timeclock..."),
			})
			.then((r) => {
				me.payload = r.message || { departments: [], totals: {}, summary: [], details: [] };
				me.render_dept_options(me.$body.find(".sp-inout-dept__search").val());
				me.render_tables();
			})
			.then(null, () => {})
			.then(() => {
				me.$body.removeClass("is-loading");
			});
	},

	filtered_payload() {
		const payload = this.payload || { totals: {}, summary: [], details: [], departments: [] };
		const details = (payload.details || []).filter((row) => {
			if (this.department && row.department !== this.department) {
				return false;
			}
			if (row.status === "IN" && !this.include_in) {
				return false;
			}
			if (row.status === "OUT" && !this.include_out) {
				return false;
			}
			return true;
		});
		const summary = (payload.summary || []).filter((row) => {
			if (!this.department) {
				return true;
			}
			return row.department === this.department;
		});
		return { ...payload, details, summary };
	},

	render_tables() {
		if (!this.payload) {
			return;
		}
		const data = this.filtered_payload();
		const totals = this.payload.totals || {};
		this.$body.find(".sp-inout-totals").html(`
			<span><strong>${frappe.utils.escape_html(__("Total"))}:</strong> ${cint(totals.total)}</span>
			<span><strong>${frappe.utils.escape_html(__("IN"))}:</strong> ${cint(totals.in_count)}</span>
			<span><strong>${frappe.utils.escape_html(__("OUT"))}:</strong> ${cint(totals.out_count)}</span>
			<span><strong>${frappe.utils.escape_html(__("Late"))}:</strong> ${cint(totals.late)}</span>
		`);

		if (this.include_summary) {
			this.$body.find(".sp-inout-summary-wrap").html(this.summary_table(data.summary)).show();
		} else {
			this.$body.find(".sp-inout-summary-wrap").hide().empty();
		}
		this.$body.find(".sp-inout-detail-wrap").html(this.detail_table(data.details));
	},

	summary_table(rows) {
		const body =
			(rows || [])
				.map(
					(row, index) => `
				<tr>
					<td>${index + 1}</td>
					<td>${frappe.utils.escape_html(row.department || __("No Department"))}</td>
					<td>${cint(row.employees)}</td>
					<td>${cint(row.in_count)}</td>
					<td>${cint(row.out_count)}</td>
				</tr>`,
				)
				.join("") || `<tr><td colspan="5">${frappe.utils.escape_html(__("No departments to show"))}</td></tr>`;

		return `
			<table class="sp-inout-table sp-inout-table--summary">
				<thead>
					<tr>
						<th></th>
						<th>${frappe.utils.escape_html(__("Name"))}</th>
						<th>${frappe.utils.escape_html(__("Number of Employees"))}</th>
						<th>${frappe.utils.escape_html(__("Working Now (IN)"))}</th>
						<th>${frappe.utils.escape_html(__("Not Working (OUT)"))}</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>`;
	},

	detail_table(rows) {
		const body =
			(rows || [])
				.map((row, index) => {
					const status_class = row.late ? "is-late" : row.status === "IN" ? "is-in" : "is-out";
					const status_label = row.late ? __("LATE") : row.status;
					return `
				<tr>
					<td>${index + 1}</td>
					<td>${frappe.utils.escape_html(row.employee_name || "")}</td>
					<td class="sp-inout-status ${status_class}">${frappe.utils.escape_html(status_label)}</td>
					<td>${frappe.utils.escape_html(row.date || "")}</td>
					<td>${frappe.utils.escape_html(row.time || "")}</td>
					<td>${frappe.utils.escape_html(row.pto_code || "")}</td>
					<td>${frappe.utils.escape_html(row.device_id || "")}</td>
				</tr>`;
				})
				.join("") || `<tr><td colspan="7">${frappe.utils.escape_html(__("No agents to show"))}</td></tr>`;

		return `
			<table class="sp-inout-table sp-inout-table--detail">
				<thead>
					<tr>
						<th></th>
						<th>${frappe.utils.escape_html(__("Name"))}</th>
						<th>${frappe.utils.escape_html(__("In / Out"))}</th>
						<th>${frappe.utils.escape_html(__("Date"))}</th>
						<th>${frappe.utils.escape_html(__("Time"))}</th>
						<th>${frappe.utils.escape_html(__("Job / Pto Code"))}</th>
						<th>${frappe.utils.escape_html(__("Device ID"))}</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>`;
	},
};

function cint(value) {
	return frappe.utils.cint(value) || 0;
}
