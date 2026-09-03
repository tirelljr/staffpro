frappe.provide("hrms.attendance_calendar");

const PRESENT_STATUSES = new Set(["Present", "Work From Home", "Half Day"]);
const FACE_LIMIT = 5;
const DEPT_LINE_LIMIT = 4;

function escape_html(value) {
	return frappe.utils.escape_html(value == null ? "" : String(value));
}

function client_label(row) {
	const label = String(row?.client || row?.client_name || "").trim();
	return label || __("Unassigned");
}

function is_past_date(dateStr) {
	return Boolean(dateStr) && dateStr < frappe.datetime.get_today();
}

function inout_status_from_row(row, dateStr) {
	if (row.inout === "IN" || row.inout === "OUT") return row.inout;
	if (row.status === "IN" || row.status === "OUT") return row.status;
	let status = "OUT";
	if (row.in_time && !row.out_time) status = "IN";
	else if (PRESENT_STATUSES.has(record_status(row)) && !row.out_time && dateStr === frappe.datetime.get_today()) {
		status = "IN";
	}
	return status;
}

function employee_initials(name) {
	return String(name || "")
		.trim()
		.split(/\s+/)
		.slice(0, 2)
		.map((part) => part[0] || "")
		.join("")
		.toUpperCase();
}

function status_from_title(title) {
	const text = String(title || "");
	const match = text.match(/:\s*(Present|Work From Home|Half Day|Absent|On Leave)\s*$/i);
	return match ? match[1] : "";
}

function employee_name_from_title(title) {
	const text = String(title || "");
	return text.replace(/\s*:\s*(Present|Work From Home|Half Day|Absent|On Leave)\s*$/i, "").trim();
}

function event_props(event) {
	return Object.assign({}, event, event.extendedProps || {});
}

function event_date(event) {
	const props = event_props(event);
	const start = event.start || props.attendance_date || props.start;
	return start ? moment(start).format("YYYY-MM-DD") : "";
}

function record_status(row) {
	return row.status || status_from_title(row.title) || "";
}

function has_day_entry(row, dateStr) {
	if (PRESENT_STATUSES.has(record_status(row))) return true;
	if (row.inout === "IN" || row.inout === "OUT") return true;
	if (row.status === "IN" || row.status === "OUT") return true;
	if (dateStr && dateStr === frappe.datetime.get_today()) {
		return Boolean(row.employee || row.employee_name);
	}
	return Boolean(row.in_time || row.out_time);
}

function avatar_html(row, className = "sp-att-cal-faces__avatar") {
	const title = escape_html(row.employee_name || row.employee || "");
	if (row.image) {
		return `<span class="${className}" title="${title}"><img src="${escape_html(row.image)}" alt=""></span>`;
	}
	return `<span class="${className}" title="${title}">${escape_html(employee_initials(row.employee_name || row.employee))}</span>`;
}

function faces_html(people) {
	const shown = people.slice(0, FACE_LIMIT);
	const count = people.length;
	return `
		<div class="sp-att-cal-faces" role="button" tabindex="0" title="${escape_html(__("{0} staff", [count]))}">
			<span class="sp-att-cal-faces__stack">
				${shown.map((row) => avatar_html(row)).join("")}
			</span>
			<span class="sp-att-cal-faces__count">${count}</span>
		</div>
	`;
}

function client_counts_html(people, counted) {
	const grouped = {};
	people.forEach((row) => {
		const key = client_label(row);
		if (!grouped[key]) grouped[key] = 0;
	});
	counted.forEach((row) => {
		const key = client_label(row);
		grouped[key] = (grouped[key] || 0) + 1;
	});
	const rows = Object.keys(grouped)
		.sort((a, b) => grouped[b] - grouped[a] || a.localeCompare(b))
		.map((client) => ({
			client,
			count: grouped[client],
		}));
	if (!rows.length) return "";

	const visible = rows.slice(0, DEPT_LINE_LIMIT);
	const hidden = rows.length - visible.length;
	return `
		<div class="sp-att-cal-depts">
			${visible
				.map(
					(row) => `
				<div class="sp-att-cal-dept" title="${escape_html(row.client)}">
					${escape_html(row.client)} - ${row.count}
				</div>`,
				)
				.join("")}
			${hidden > 0 ? `<div class="sp-att-cal-dept sp-att-cal-dept--more">+${hidden}</div>` : ""}
		</div>
	`;
}

function counted_people(people, dateStr) {
	if (is_past_date(dateStr)) return people;
	const inout_filter = hrms.attendance_calendar.inout_filter || "IN";
	return people.filter((row) => row.inout === inout_filter);
}

function day_cell_html(people, dateStr) {
	if (!people.length) return "";
	return `
		<div class="sp-att-cal-day">
			${client_counts_html(people, counted_people(people, dateStr))}
			${faces_html(people)}
		</div>
	`;
}

function calendar_api() {
	return cur_list?.calendar?.fullCalendar || null;
}

function calendar_root(api) {
	return api?.el || document.getElementById("fc-calendar-wrapper");
}

function roster_row_to_event(row, date) {
	const inout = row.inout || (row.status === "IN" || row.status === "OUT" ? row.status : "");
	return {
		employee: row.employee,
		employee_name: row.employee_name,
		image: row.image,
		department: row.department || "",
		client: row.client || row.client_name || "",
		status: row.attendance_status || (PRESENT_STATUSES.has(row.status) ? row.status : "Present"),
		in_time: row.in_time,
		out_time: row.out_time,
		inout: inout || inout_status_from_row(row, date),
		title: `${row.employee_name || row.employee || ""} : ${row.attendance_status || "Present"}`,
	};
}

function collect_people() {
	const byDate = {};
	const add = (row, date) => {
		if (!date || !has_day_entry(row, date)) return;
		const employee = row.employee || row.employee_name || row.title;
		const already = (byDate[date] || []).some((item) => item.employee === employee);
		if (already) return;
		const person = {
			employee,
			employee_name: row.employee_name || employee_name_from_title(row.title) || employee,
			image: row.image,
			department: row.department || "",
			client: row.client || row.client_name || "",
			status: record_status(row),
			in_time: row.in_time,
			out_time: row.out_time,
		};
		person.inout = inout_status_from_row({ ...person, inout: row.inout, status: row.inout || row.status }, date);
		(byDate[date] ||= []).push(person);
	};

	(hrms.attendance_calendar.raw || []).forEach((row) => {
		if (row.doctype === "Holiday") return;
		add(row, moment(row.attendance_date || row.start).format("YYYY-MM-DD"));
	});

	const api = calendar_api();
	if (typeof api?.getEvents === "function") {
		api.getEvents().forEach((event) => {
			const props = event_props(event);
			if (props.doctype === "Holiday") return;
			add(props, event_date(event));
		});
	}

	const todayRoster = hrms.attendance_calendar.today_roster;
	const today = frappe.datetime.get_today();
	if (todayRoster?.details?.length && (!todayRoster.date || todayRoster.date === today)) {
		todayRoster.details.forEach((row) => {
			add(roster_row_to_event(row, today), today);
		});
	}

	Object.keys(byDate).forEach((date) => {
		byDate[date].sort((a, b) =>
			String(a.employee_name || "").localeCompare(String(b.employee_name || "")),
		);
	});
	return byDate;
}

function paint_faces(api) {
	const root = calendar_root(api);
	if (!root) return;
	const $root = $(root);
	$root.addClass("sp-att-cal");
	$("body").addClass("sp-att-cal-page");

	const byDate = collect_people();
	const inout_filter = hrms.attendance_calendar.inout_filter || "IN";
	const signature = JSON.stringify([
		inout_filter,
		Object.keys(byDate)
			.sort()
			.map((date) => [
				date,
				byDate[date].map((row) => row.employee),
				counted_people(byDate[date], date).map((row) => [client_label(row), row.employee]),
			]),
	]);
	if ($root.data("sp-att-sig") === signature && $root.find(".sp-att-cal-day").length) {
		return;
	}
	$root.data("sp-att-sig", signature);
	$root.find(".sp-att-cal-day").remove();

	Object.keys(byDate).forEach((date) => {
		const html = day_cell_html(byDate[date], date);
		const $frames = $root.find(`.fc-daygrid-day[data-date="${date}"] .fc-daygrid-day-frame`);
		if ($frames.length) {
			$frames.append(html);
			return;
		}
		$root.find(`.fc-col-header-cell[data-date="${date}"]`).append(html);
	});
}

function format_clock(value) {
	if (!value) return "";
	if (hrms.time?.format_clock) {
		const formatted = hrms.time.format_clock(value);
		if (formatted) return formatted;
	}
	const parsed = moment(value);
	return parsed.isValid() ? parsed.format("h:mm A") : String(value);
}

function roster_from_calendar(dateStr) {
	const rows = (hrms.attendance_calendar.raw || []).filter((row) => {
		if (row.doctype === "Holiday") return false;
		return moment(row.attendance_date || row.start).format("YYYY-MM-DD") === dateStr;
	});
	const details = rows.map((props) => {
		const inTime = format_clock(props.in_time);
		const outTime = format_clock(props.out_time);
		let status = "OUT";
		if (props.in_time && !props.out_time) status = "IN";
		else if (PRESENT_STATUSES.has(record_status(props)) && !props.out_time && dateStr === frappe.datetime.get_today()) {
			status = "IN";
		}
		return {
			employee: props.employee,
			employee_name: props.employee_name || employee_name_from_title(props.title),
			image: props.image,
			department: props.department || "",
			client: props.client || "",
			status,
			late: Boolean(props.late || props.late_entry),
			late_minutes: Number(props.late_minutes || 0),
			late_label: props.late_label || "",
			attendance_status: record_status(props),
			attendance: props.name || props.id,
			in_time: inTime,
			out_time: outTime,
			time: outTime || inTime,
			leave_type: props.leave_type || (record_status(props) === "On Leave" ? "On Leave" : ""),
			pto_code: record_status(props) === "On Leave" ? "On Leave" : "",
			device_id: "",
		};
	});
	return {
		date: dateStr,
		departments: [...new Set(details.map((row) => row.department).filter(Boolean))].sort(),
		details,
		summary: [],
		totals: {
			total: details.length,
			in_count: details.filter((row) => row.status === "IN").length,
			out_count: details.filter((row) => row.status === "OUT").length,
			late: details.filter((row) => row.late).length,
		},
	};
}

function select_html(className, variant, label, options, value) {
	if (hrms.ui?.dash_select_html) {
		return hrms.ui.dash_select_html({ className, variant, label, options, value });
	}
	const selected = options.find((opt) => opt.value === value) || options[0];
	return `
		<select class="${escape_html(className)} sp-dash-panel__select sp-dash-panel__select--${escape_html(variant)}" aria-label="${escape_html(label)}">
			${options
				.map(
					(opt) =>
						`<option value="${escape_html(opt.value)}"${opt.value === selected.value ? " selected" : ""}>${escape_html(opt.label)}</option>`,
				)
				.join("")}
		</select>`;
}

function status_label(row) {
	if (hrms.ui?.late_status_label) {
		return hrms.ui.late_status_label(row);
	}
	if (row.late) return row.late_label ? `${__("LATE")} ${row.late_label}` : __("LATE");
	return row.status || __("OUT");
}

function status_class(row) {
	if (row.late) return "is-late";
	if (row.status === "IN") return "is-in";
	return "is-out";
}

function department_options(payload) {
	const options = [{ value: "", label: __("All Departments") }];
	(payload.departments || []).forEach((name) => options.push({ value: name, label: name }));
	if ((payload.details || []).some((row) => !row.department)) {
		options.push({ value: "__none__", label: __("No Department") });
	}
	return options;
}

function observe_calendar(api) {
	const root = calendar_root(api);
	if (!root || root._sp_att_obs) return;
	let timer = null;
	root._sp_att_obs = new MutationObserver(() => {
		if (hrms.attendance_calendar._painting) return;
		clearTimeout(timer);
		timer = setTimeout(() => hrms.attendance_calendar.paint(api), 40);
	});
	root._sp_att_obs.observe(root, { childList: true, subtree: true });
}

function ensure_calendar_toolbar(cal) {
	const $toolbar = cal?.$toolbar;
	if (!$toolbar?.length || $toolbar.find(".sp-att-cal-toolbar__toggle").length) return;
	const $toggle = $(hrms.ui.inout_toggle_html({ className: "sp-att-cal-toolbar__toggle", value: "IN" }));
	$toolbar.find(".grow").after($('<div class="sp-att-cal-toolbar__filters"></div>').append($toggle));
	hrms.ui.bind_inout_toggle($toggle, (value) => {
		hrms.attendance_calendar.inout_filter = value;
		$(calendar_root(cal.fullCalendar)).removeData("sp-att-sig");
		hrms.attendance_calendar.paint(cal.fullCalendar);
	});
}

function hook_calendar() {
	let route = "";
	try {
		route = frappe.get_route_str?.() || "";
	} catch (e) {
		route = "";
	}
	if (!route.includes("Attendance/Calendar")) {
		$("body").removeClass("sp-att-cal-page");
		return false;
	}
	const cal = cur_list?.calendar;
	if (!cal?.fullCalendar || !cal.prepare_events) return false;

	if (!cal._sp_att_hooked) {
		cal._sp_att_hooked = true;
		const original = cal.prepare_events.bind(cal);
		cal.prepare_events = (events) => {
			const prepared = original(events);
			hrms.attendance_calendar.raw = prepared;
			return prepared.map((row) => {
				if (row.doctype === "Holiday") return row;
				return Object.assign({}, row, {
					display: "none",
					classNames: [].concat(row.classNames || [], ["sp-att-cal-hidden"]),
				});
			});
		};

		const api = cal.fullCalendar;
		api.setOption("dateClick", (info) => {
			hrms.attendance_calendar.show_day_roster(info.dateStr || moment(info.date).format("YYYY-MM-DD"));
		});
		api.setOption("eventClick", (info) => {
			info.jsEvent?.preventDefault?.();
			info.jsEvent?.stopPropagation?.();
			hrms.attendance_calendar.show_day_roster(moment(event_date(info.event) || info.event.startStr).format("YYYY-MM-DD"));
		});
		api.setOption("select", (info) => {
			if (hrms.attendance_calendar.is_day_select(info)) {
				hrms.attendance_calendar.show_day_roster(moment(info.start).format("YYYY-MM-DD"));
				api.unselect?.();
				return;
			}
			hrms.attendance_calendar.open_add_entry(info);
		});
		observe_calendar(api);
		ensure_calendar_toolbar(cal);
		cal.refresh?.();
	}

	ensure_calendar_toolbar(cal);
	hrms.attendance_calendar.load_today_roster();
	hrms.attendance_calendar.paint(cal.fullCalendar);
	return true;
}

hrms.attendance_calendar = Object.assign(hrms.attendance_calendar || {}, {
	raw: [],
	today_roster: null,
	dialog: null,
	payload: null,
	date: "",
	department: "",
	status: "IN",
	inout_filter: "IN",
	sort: "department",
	query: "",
	_painting: false,
	_today_roster_loading: false,

	load_today_roster() {
		const today = frappe.datetime.get_today();
		if (this._today_roster_loading) return;
		if (this.today_roster?.date === today && this.today_roster?.details) return;
		this._today_roster_loading = true;
		frappe.call({
			method: "hrms.hr.doctype.attendance.attendance.get_calendar_day_roster",
			args: { attendance_date: today },
			callback: (r) => {
				this._today_roster_loading = false;
				if (!r.message?.details) return;
				this.today_roster = r.message;
				$(calendar_root()).removeData("sp-att-sig");
				this.paint();
			},
			error: () => {
				this._today_roster_loading = false;
			},
		});
	},

	paint(api) {
		this._painting = true;
		try {
			paint_faces(api || calendar_api());
		} catch (error) {
			console.error("Attendance calendar paint failed", error);
		} finally {
			this._painting = false;
		}
	},

	open_add_entry(info) {
		const start = info?.start;
		const end = info?.end;
		const opts = {
			attendance_date: start ? moment(start).format("YYYY-MM-DD") : frappe.datetime.get_today(),
		};
		const seconds = start && end ? end - start : 0;
		if (start && seconds !== 86400000) {
			opts.in_time = moment(start).format("HH:mm:ss");
			if (end) {
				opts.out_time = moment(end).format("HH:mm:ss");
			}
		}
		hrms.time.show_add_entry_dialog?.(cur_list, opts);
		calendar_api()?.unselect?.();
	},

	is_day_select(info) {
		if (!info?.start) return false;
		if (info.allDay === false) return false;
		if (info.start && info.end) {
			const days = moment(info.end).diff(moment(info.start), "days", true);
			if (days > 1.01) return false;
			if (days >= 0.9) return true;
		}
		return Boolean(info.allDay);
	},

	show_day_roster(dateStr) {
		if (!dateStr) return;
		this.date = moment(dateStr).format("YYYY-MM-DD");
		this.department = "";
		this.status = this.inout_filter || "IN";
		this.sort = "department";
		this.query = "";
		this.payload = roster_from_calendar(this.date);
		this.ensure_dialog();
		this.dialog.set_title(__("Attendance — {0}", [frappe.datetime.str_to_user(this.date)]));
		this.render_shell();
		this.dialog.show();
		this.load_roster();
	},

	ensure_dialog() {
		if (this.dialog) return;
		this.dialog = new frappe.ui.Dialog({
			title: __("Attendance"),
			size: "extra-large",
			fields: [{ fieldtype: "HTML", fieldname: "roster" }],
		});
		this.dialog.$wrapper.addClass("sp-att-cal-dialog");
	},

	$body() {
		return this.dialog?.fields_dict?.roster?.$wrapper;
	},

	render_shell() {
		const $body = this.$body();
		if (!$body) return;
		$body.html(`
			<section class="sp-att-cal-roster" aria-label="${escape_html(__("Daily attendance"))}">
				<div class="sp-att-cal-roster__filters">
					<label class="sp-att-cal-roster__search">
						<span class="sr-only">${escape_html(__("Search name"))}</span>
						<input type="search" class="sp-att-cal-roster__query" placeholder="${escape_html(__("Search name"))}" />
					</label>
					${select_html(
						"sp-att-cal-roster__department",
						"outline",
						__("Department"),
						department_options(this.payload || {}),
						this.department,
					)}
					${hrms.ui.inout_toggle_html({ className: "sp-att-cal-roster__toggle", value: this.status || "IN" })}
					${select_html("sp-att-cal-roster__sort", "outline", __("Sort"), [
						{ value: "department", label: __("Department") },
						{ value: "name", label: __("Name") },
						{ value: "time", label: __("Time") },
						{ value: "status", label: __("In / Out") },
					], this.sort)}
				</div>
				<div class="sp-inout-dash__totals" aria-live="polite"></div>
				<div class="sp-att-cal-roster__table">
					<div class="sp-att-cal-roster__head">
						<span>${escape_html(__("Name"))}</span>
						<span>${escape_html(__("In / Out"))}</span>
						<span>${escape_html(__("In"))}</span>
						<span>${escape_html(__("Out"))}</span>
						<span>${escape_html(__("Status"))}</span>
					</div>
					<div class="sp-att-cal-roster__list"></div>
				</div>
			</section>
		`);
		if (hrms.ui?.bind_dash_selects) {
			hrms.ui.bind_dash_selects($body);
		}
		this.bind_filters($body);
		this.render_rows();
	},

	bind_filters($body) {
		const me = this;
		$body.off(".attCalRoster");
		$body.on("input.attCalRoster", ".sp-att-cal-roster__query", function () {
			me.query = String($(this).val() || "").trim().toLowerCase();
			me.render_rows();
		});
		$body.on("change.attCalRoster", ".sp-att-cal-roster__department", function () {
			me.department = $(this).val() || "";
			me.render_rows();
		});
		hrms.ui.bind_inout_toggle($body.find(".sp-att-cal-roster__toggle"), (value) => {
			me.status = value;
			me.render_rows();
		});
		$body.on("change.attCalRoster", ".sp-att-cal-roster__sort", function () {
			me.sort = $(this).val() || "department";
			me.render_rows();
		});
		$body.on("click.attCalRoster", ".sp-att-cal-roster__row", function () {
			const attendance = $(this).data("attendance");
			const employee = $(this).data("employee");
			me.dialog.hide();
			if (attendance && frappe.model.can_read("Attendance")) {
				frappe.set_route("Form", "Attendance", attendance);
			} else if (employee) {
				frappe.set_route("Form", "Employee", employee);
			}
		});
	},

	load_roster() {
		const $list = this.$body()?.find(".sp-att-cal-roster__list");
		$list?.addClass("is-loading");
		frappe.call({
			method: "hrms.hr.doctype.attendance.attendance.get_calendar_day_roster",
			args: { attendance_date: this.date },
			callback: (r) => {
				$list?.removeClass("is-loading");
				if (r.message?.details) {
					this.payload = r.message;
				}
				this.refresh_department_options();
				this.render_rows();
			},
			error: () => {
				$list?.removeClass("is-loading");
				this.render_rows();
			},
		});
	},

	refresh_department_options() {
		const $select = this.$body()?.find(".sp-att-cal-roster__department");
		if (!$select?.length) return;
		const options = department_options(this.payload || {});
		if (hrms.ui?.set_dash_select_options) {
			this.department = hrms.ui.set_dash_select_options($select, options) || "";
			return;
		}
		$select.html(
			options
				.map(
					(opt) =>
						`<option value="${escape_html(opt.value)}"${opt.value === this.department ? " selected" : ""}>${escape_html(opt.label)}</option>`,
				)
				.join(""),
		);
	},

	filtered_rows() {
		let rows = [...(this.payload?.details || [])];
		if (this.department === "__none__") {
			rows = rows.filter((row) => !row.department);
		} else if (this.department) {
			rows = rows.filter((row) => row.department === this.department);
		}
		if (this.status) {
			rows = rows.filter((row) => row.status === this.status);
		}
		if (this.query) {
			rows = rows.filter((row) =>
				String(row.employee_name || row.employee || "")
					.toLowerCase()
					.includes(this.query),
			);
		}
		const key = this.sort;
		rows.sort((a, b) => {
			if (key === "time") {
				return String(a.time || a.in_time || "").localeCompare(String(b.time || b.in_time || ""));
			}
			if (key === "status") {
				return String(a.status || "").localeCompare(String(b.status || ""));
			}
			if (key === "name") {
				return String(a.employee_name || "").localeCompare(String(b.employee_name || ""));
			}
			const dept = String(a.department || "").localeCompare(String(b.department || ""));
			if (dept) return dept;
			return String(a.employee_name || "").localeCompare(String(b.employee_name || ""));
		});
		return rows;
	},

	render_rows() {
		const $body = this.$body();
		if (!$body) return;
		const rows = this.filtered_rows();
		const totals = {
			total: rows.length,
			in_count: rows.filter((row) => row.status === "IN").length,
			out_count: rows.filter((row) => row.status === "OUT").length,
			late: rows.filter((row) => row.late).length,
		};
		$body.find(".sp-inout-dash__totals").html(`
			<span><strong>${escape_html(__("Total"))}:</strong> ${totals.total}</span>
			<span><strong>${escape_html(__("IN"))}:</strong> ${totals.in_count}</span>
			<span><strong>${escape_html(__("OUT"))}:</strong> ${totals.out_count}</span>
			<span><strong>${escape_html(__("Late"))}:</strong> ${totals.late}</span>
		`);
		const $list = $body.find(".sp-att-cal-roster__list");
		if (!rows.length) {
			$list.html(`<div class="sp-inout-dash__empty"><p>${escape_html(__("No staff to show for this day."))}</p></div>`);
			return;
		}
		$list.html(
			rows
				.map(
					(row) => `
				<button type="button" class="sp-att-cal-roster__row" data-employee="${escape_html(row.employee || "")}" data-attendance="${escape_html(row.attendance || "")}">
					<span class="sp-inout-dash__agent">
						<span class="sp-inout-dash__avatar">${avatar_html(row, "sp-att-cal-roster__avatar")}</span>
						<span class="sp-inout-dash__agent-meta">
							<span class="sp-inout-dash__name">${escape_html(row.employee_name || row.employee || "")}</span>
							${row.department ? `<span class="sp-inout-dash__dept">${escape_html(row.department)}</span>` : ""}
						</span>
					</span>
					<span class="sp-inout-dash__status-pill ${status_class(row)}">${escape_html(status_label(row))}</span>
					<span>${escape_html(row.in_time || "—")}</span>
					<span>${escape_html(row.out_time || "—")}</span>
					<span>${escape_html(row.attendance_status || row.pto_code || "—")}</span>
				</button>
			`,
				)
				.join(""),
		);
	},
});

function date_from_target(target) {
	const cell = target?.closest?.("[data-date]");
	return cell?.getAttribute?.("data-date") || "";
}

function try_hook() {
	if (hook_calendar()) return;
	let tries = 0;
	const timer = setInterval(() => {
		tries += 1;
		if (hook_calendar() || tries > 40) {
			clearInterval(timer);
		}
	}, 150);
}

$(document).on("click", ".sp-att-cal-day, .sp-att-cal-faces, .sp-att-cal-page .fc-daygrid-day-frame, .sp-att-cal-page .fc-daygrid-day-top", function (e) {
	const date = date_from_target(e.currentTarget);
	if (!date) return;
	if ($(e.target).closest(".fc-event").length && !$(e.target).closest(".sp-att-cal-faces").length) {
		return;
	}
	e.preventDefault();
	e.stopPropagation();
	hrms.attendance_calendar.show_day_roster(date);
});

$(document).on("app_ready page-change", () => setTimeout(try_hook, 50));
setTimeout(try_hook, 200);
