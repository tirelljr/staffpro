frappe.provide("hrms.time");

function escape_html(text) {
	if (text == null) {
		return "";
	}
	return String(text)
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;");
}

hrms.time.comment_field = function () {
	return {
		fieldname: "comment",
		label: __("Comment"),
		fieldtype: "Small Text",
	};
};

hrms.time.parse_clock = function (value) {
	if (!value) {
		return null;
	}
	const parsed = moment(value);
	if (parsed.isValid()) {
		return parsed;
	}
	const as_time = moment(String(value), ["HH:mm:ss", "HH:mm", "hh:mm a", "hh:mm A"], true);
	return as_time.isValid() ? as_time : null;
};

hrms.time.hours_between = function (in_time, out_time) {
	const start = hrms.time.parse_clock(in_time);
	const end = hrms.time.parse_clock(out_time);
	if (!start || !end) {
		return 0;
	}
	let minutes = end.diff(start, "minutes");
	if (minutes < 0) {
		minutes += 24 * 60;
	}
	return minutes > 0 ? Math.round(minutes) / 60 : 0;
};

hrms.time.hours_for_row = function (row) {
	if (!row) {
		return 0;
	}
	const stored = flt(row.working_hours);
	if (stored) {
		return stored;
	}
	if (row.kind === "lunch") {
		return stored;
	}
	return hrms.time.hours_between(row.in_time, row.out_time);
};

hrms.time.format_hours = function (value) {
	if (value === null || value === undefined || value === "") {
		return "";
	}
	const total_minutes = Math.round(flt(value) * 60);
	const sign = total_minutes < 0 ? "-" : "";
	const abs = Math.abs(total_minutes);
	const hours = Math.floor(abs / 60);
	const minutes = abs % 60;
	return `${sign}${hours}h ${minutes}m`;
};

hrms.time.format_clock = function (value) {
	if (!value) {
		return "";
	}
	const parsed = moment(value);
	return parsed.isValid() ? parsed.format("hh:mm a") : "";
};

hrms.time.format_gps = function (_value, _df, doc) {
	const lat = flt(doc.latitude);
	const lng = flt(doc.longitude);
	if (!lat && !lng) {
		return "";
	}
	return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
};

hrms.time.replace_filter = function (listview, fieldname, condition, value) {
	const others = (listview.filter_area?.get() || []).filter((filter) => filter[1] !== fieldname);
	const next = others.slice();
	if (condition && value !== undefined && value !== null && value !== "") {
		next.push([listview.doctype, fieldname, condition, value]);
	}
	listview.filter_area.clear();
	if (next.length) {
		listview.filter_area.add(next);
	} else {
		listview.refresh();
	}
};

hrms.time.get_filter_value = function (listview, fieldname) {
	const match = (listview?.filter_area?.get() || []).find((filter) => filter[1] === fieldname);
	return match ? match[3] : null;
};

hrms.time.setup_range_filters = function (listview, options) {
	const date_field = options.date_field;
	const datetime = Boolean(options.datetime);
	const today = frappe.datetime.get_today();
	const existing = hrms.time.get_filter_value(listview, date_field);
	let from_date = today;
	let to_date = today;

	if (Array.isArray(existing) && existing.length === 2) {
		from_date = String(existing[0]).slice(0, 10);
		to_date = String(existing[1]).slice(0, 10);
	} else if (typeof existing === "string" && existing) {
		from_date = to_date = existing.slice(0, 10);
	} else if (!(listview.filter_area?.get() || []).length) {
		hrms.time.replace_filter(
			listview,
			date_field,
			"Between",
			datetime ? [`${today} 00:00:00`, `${today} 23:59:59`] : [today, today],
		);
	}

	const apply = () => {
		let start = from_field.get_value();
		let end = to_field.get_value();
		if (!start || !end) {
			return;
		}
		if (start > end) {
			const swap = start;
			start = end;
			end = swap;
			from_field.set_value(start);
			to_field.set_value(end);
		}
		hrms.time.replace_filter(
			listview,
			date_field,
			"Between",
			datetime ? [`${start} 00:00:00`, `${end} 23:59:59`] : [start, end],
		);
	};

	const from_field = listview.page.add_field({
		fieldtype: "Date",
		fieldname: "sp_from_date",
		label: __("From"),
		default: from_date,
		change: apply,
		onchange: apply,
	});
	const to_field = listview.page.add_field({
		fieldtype: "Date",
		fieldname: "sp_to_date",
		label: __("To"),
		default: to_date,
		change: apply,
		onchange: apply,
	});

	listview.page.add_field({
		fieldtype: "Link",
		fieldname: "sp_employee",
		label: __("Employee"),
		options: "Employee",
		change() {
			hrms.time.replace_filter(listview, "employee", this.get_value() ? "=" : null, this.get_value());
		},
	});

	listview.page.add_field({
		fieldtype: "Link",
		fieldname: "sp_department",
		label: __("Department"),
		options: "Department",
		async change() {
			const department = this.get_value();
			if (options.department_field) {
				hrms.time.replace_filter(listview, options.department_field, department ? "=" : null, department);
				return;
			}
			if (!department) {
				hrms.time.replace_filter(listview, "employee", null, null);
				return;
			}
			const employees = await frappe.db.get_list("Employee", {
				filters: { department },
				pluck: "name",
				limit: 500,
			});
			hrms.time.replace_filter(
				listview,
				"employee",
				"in",
				employees.length ? employees : ["__no_match__"],
			);
		},
	});
};

hrms.time.render_totals = function (listview, text) {
	let $totals = listview.page.wrapper.find(".sp-hours-totals");
	if (!$totals.length) {
		$totals = $('<span class="text-muted sp-hours-totals ml-2"></span>');
		listview.page.page_form.append($totals);
	}
	$totals.text(text || "");
};

hrms.time.refresh_hours_totals = function (listview) {
	const range = hrms.time.get_filter_value(listview, "attendance_date");
	let from_date = frappe.datetime.get_today();
	let to_date = from_date;
	if (Array.isArray(range) && range.length === 2) {
		from_date = String(range[0]).slice(0, 10);
		to_date = String(range[1]).slice(0, 10);
	}
	const employee = hrms.time.get_filter_value(listview, "employee");
	const department = hrms.time.get_filter_value(listview, "department");

	frappe.call({
		method: "hrms.hr.doctype.attendance.attendance.get_hours_totals",
		args: {
			from_date,
			to_date,
			employee: typeof employee === "string" ? employee : "",
			department: typeof department === "string" ? department : "",
		},
		callback(r) {
			const totals = r.message || {};
			hrms.time.render_totals(
				listview,
				__("Total Hours: {0}    Paid Hours: {1}    Gross: {2}    SS: {3}    Net: {4}", [
					hrms.time.format_hours(totals.total),
					hrms.time.format_hours(totals.paid),
					format_currency(Number(totals.daily_pay || 0)),
					format_currency(Number(totals.ss_deduction || 0)),
					format_currency(Number(totals.net_daily_pay || 0)),
				]),
			);
		},
	});
};

hrms.time.escape_html = escape_html;

hrms.time.employee_label = function (employee) {
	const last = String(employee?.last_name || "").trim();
	const first = String(employee?.first_name || "").trim();
	if (last && first) {
		return `${last}, ${first}`;
	}
	return employee?.employee_name || employee?.name || "";
};

hrms.time.employee_in_department = function (employee, department) {
	if (!department) {
		return true;
	}
	const value = String(employee?.department || "");
	const selected = String(department);
	if (value === selected) {
		return true;
	}
	return value.startsWith(`${selected} - `) || selected.startsWith(`${value} - `);
};

hrms.time.mount_dialog_html = function (dialog, fieldname, $content) {
	const $host = dialog?.fields_dict?.[fieldname]?.$wrapper;
	if ($host?.length) {
		$host.empty().append($content);
	} else {
		dialog.$body.empty().append($content);
	}
	dialog.$wrapper.find(".modal-footer").hide();
};

hrms.time.refresh_hours_views = function (listview) {
	if (listview?.refresh) {
		listview.refresh();
	} else if (cur_list?.doctype === "Attendance") {
		cur_list.refresh();
	}
	if (hrms.day_view?.$body?.length && listview?.refresh !== hrms.day_view.refresh) {
		hrms.day_view.refresh();
	}
};

hrms.time.to_hhmm = function (value) {
	if (!value) {
		return "";
	}
	const text = String(value);
	if (text.includes("T")) {
		return text.split("T")[1].slice(0, 5);
	}
	if (text.includes(" ")) {
		return text.split(" ")[1].slice(0, 5);
	}
	return text.slice(0, 5);
};

hrms.time.to_clock = function (value) {
	if (!value) {
		return "";
	}
	return value.length === 5 ? `${value}:00` : value;
};

hrms.time.to_date_string = function (value) {
	if (!value) {
		return "";
	}
	const parsed = moment(value);
	return parsed.isValid() ? parsed.format("YYYY-MM-DD") : String(value).slice(0, 10);
};

hrms.time.default_entry_date = function (listview) {
	const range = hrms.time.get_filter_value(listview, "attendance_date");
	if (Array.isArray(range) && range[0]) {
		return hrms.time.to_date_string(range[0]) || frappe.datetime.get_today();
	}
	if (typeof range === "string" && range) {
		return hrms.time.to_date_string(range) || frappe.datetime.get_today();
	}
	return frappe.datetime.get_today();
};

hrms.time.ATTENDANCE_PORTAL_ROUTE = ["day-view"];

hrms.time.route_parts_from_value = function (value) {
	if (Array.isArray(value)) {
		return value.map((part) => String(part || ""));
	}
	if (value == null) {
		return [];
	}
	let path = String(value);
	if (path.startsWith("/desk/") || path.startsWith("/app/")) {
		path = path.replace(/^\/(desk|app)\//, "");
	} else if (path.startsWith("/")) {
		path = path.replace(/^\//, "");
	}
	return path.split("/").filter(Boolean).map((part) => {
		try {
			return decodeURIComponent(part);
		} catch (error) {
			return part;
		}
	});
};

hrms.time.normalize_route_args = function (args) {
	const parts = Array.prototype.slice.call(args);
	if (parts.length === 1) {
		return hrms.time.route_parts_from_value(parts[0]);
	}
	return parts.map((part) => String(part || ""));
};

hrms.time.is_blocked_attendance_list_route = function (parts) {
	if (!parts?.length) {
		return false;
	}
	const tokens = parts.map((part) => String(part || ""));
	const lower = tokens.map((part) => part.toLowerCase());
	if (lower[0] === "list" && lower[1] === "attendance") {
		return (lower[2] || "list") !== "calendar";
	}
	if (lower[0] === "attendance") {
		if (tokens.length === 1) {
			return true;
		}
		if (lower[1] === "view") {
			return (lower[2] || "list") !== "calendar";
		}
		if (lower[1] === "new") {
			return true;
		}
		return false;
	}
	return false;
};

hrms.time.rewrite_nav_item = function (item) {
	if (!item?.route) {
		return item;
	}
	const parts = hrms.time.route_parts_from_value(item.route);
	if (!hrms.time.is_blocked_attendance_list_route(parts)) {
		return item;
	}
	return Object.assign({}, item, {
		route: hrms.time.ATTENDANCE_PORTAL_ROUTE.slice(),
		route_options: null,
	});
};

hrms.time.go_attendance_portal = function () {
	return frappe.set_route(...hrms.time.ATTENDANCE_PORTAL_ROUTE);
};

hrms.time.attendance_listview = function () {
	return cur_list?.doctype === "Attendance" ? cur_list : null;
};

hrms.time.open_add_attendance = function (opts) {
	hrms.time.show_add_entry_dialog(hrms.time.attendance_listview(), opts || {});
};

hrms.time.should_open_entry_dialog = function (doc) {
	if (!doc || doc.amended_from) {
		return false;
	}
	if (doc.in_time || doc.out_time || flt(doc.working_hours)) {
		return false;
	}
	return true;
};

hrms.time.redirect_new_attendance_form = function (frm) {
	if (!frm?.is_new?.() || frm._sp_entry_dialog || !hrms.time.should_open_entry_dialog(frm.doc)) {
		return false;
	}
	frm._sp_entry_dialog = true;
	const opts = {
		employee: frm.doc.employee,
		department: frm.doc.department,
		attendance_date: frm.doc.attendance_date,
		shift: frm.doc.shift,
		in_time: frm.doc.in_time,
		out_time: frm.doc.out_time,
	};
	frappe.model.clear_doc(frm.doctype, frm.docname || frm.doc.name);
	const prev = frappe.get_prev_route?.() || [];
	if (
		prev.length &&
		!(prev[0] === "Form" && prev[1] === "Attendance") &&
		!hrms.time.is_blocked_attendance_list_route(prev)
	) {
		frappe.set_route(prev);
	} else {
		hrms.time.go_attendance_portal();
	}
	hrms.time.open_add_attendance(opts);
	return true;
};

hrms.time.show_add_entry_dialog = function (listview, opts) {
	opts = opts || {};
	if ($(document).find(".modal.sp-entry-dialog.show").length) {
		return;
	}
	const preset_employee = opts.employee || hrms.time.get_filter_value(listview, "employee");
	const preset_department = opts.department || hrms.time.get_filter_value(listview, "department") || "";
	const preset_date =
		hrms.time.to_date_string(opts.attendance_date) || hrms.time.default_entry_date(listview);
	const preset_start = hrms.time.to_hhmm(opts.in_time) || "09:00";
	const preset_end = hrms.time.to_hhmm(opts.out_time) || "18:00";
	const preset_shift = opts.shift || "";
	const calendar_icon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`;
	const clock_icon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/></svg>`;

	const dialog = new frappe.ui.Dialog({
		title: __("Add Working Entry"),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "entry_body" }],
	});
	dialog.$wrapper.addClass("sp-entry-dialog");

	const $root = $(`
		<div class="sp-entry-shell">
			<div class="sp-entry">
				<div class="sp-entry__col sp-entry__col--users">
					<select class="sp-entry__department" aria-label="${hrms.time.escape_html(__("Department"))}">
						<option value="">${hrms.time.escape_html(__("All Departments"))}</option>
					</select>
					<div class="sp-entry__users" role="list"></div>
				</div>
				<div class="sp-entry__col sp-entry__col--date">
					<div class="sp-entry__date-wrap">
						<input type="date" class="sp-entry__date" value="${hrms.time.escape_html(preset_date)}" />
						<button type="button" class="sp-entry__icon-btn sp-entry__date-btn" aria-label="${hrms.time.escape_html(__("Pick date"))}">${calendar_icon}</button>
					</div>
					<div class="sp-entry__picked" aria-live="polite"></div>
				</div>
				<div class="sp-entry__col sp-entry__col--job">
					<label class="sp-entry__label">${hrms.time.escape_html(__("Job:"))}</label>
					<select class="sp-entry__job" aria-label="${hrms.time.escape_html(__("Job"))}">
						<option value=""></option>
					</select>
					<div class="sp-entry__times">
						<div class="sp-entry__time-field">
							<label class="sp-entry__label">${hrms.time.escape_html(__("Start Time"))}</label>
							<div class="sp-entry__time-wrap">
								<input type="time" class="sp-entry__start" value="${hrms.time.escape_html(preset_start)}" />
								<button type="button" class="sp-entry__icon-btn" data-time="start" aria-label="${hrms.time.escape_html(__("Pick start time"))}">${clock_icon}</button>
							</div>
						</div>
						<div class="sp-entry__time-field">
							<label class="sp-entry__label">${hrms.time.escape_html(__("End Time"))}</label>
							<div class="sp-entry__time-wrap">
								<input type="time" class="sp-entry__end" value="${hrms.time.escape_html(preset_end)}" />
								<button type="button" class="sp-entry__icon-btn" data-time="end" aria-label="${hrms.time.escape_html(__("Pick end time"))}">${clock_icon}</button>
							</div>
						</div>
					</div>
					<label class="sp-entry__check">
						<input type="checkbox" class="sp-entry__working-now" />
						${hrms.time.escape_html(__("Working Now"))}
					</label>
					<textarea class="sp-entry__comment" placeholder="${hrms.time.escape_html(__("comment"))}"></textarea>
				</div>
			</div>
			<div class="sp-entry__footer">
				<button type="button" class="sp-entry__btn-primary" data-act="add">${hrms.time.escape_html(__("Add"))}</button>
				<button type="button" class="sp-entry__btn-primary" data-act="next">${hrms.time.escape_html(__("Add & Next"))}</button>
				<button type="button" class="sp-entry__btn-cancel" data-act="cancel">${hrms.time.escape_html(__("Cancel"))}</button>
			</div>
		</div>
	`);

	$root.find(".sp-entry__users").html(
		`<div class="sp-entry__user">${hrms.time.escape_html(__("Loading..."))}</div>`,
	);

	const state = {
		employees: [],
		departments: [],
		shifts: [],
		selected: new Set(),
		department: typeof preset_department === "string" ? preset_department : "",
	};
	if (typeof preset_employee === "string" && preset_employee) {
		state.selected.add(preset_employee);
	}

	const visible_employees = () => {
		const rows = state.employees.filter((row) =>
			hrms.time.employee_in_department(row, state.department),
		);
		rows.sort((a, b) =>
			hrms.time.employee_label(a).localeCompare(hrms.time.employee_label(b), undefined, {
				sensitivity: "base",
			}),
		);
		return rows;
	};

	const render_users = () => {
		const visible = visible_employees();
		const all_checked = visible.length > 0 && visible.every((row) => state.selected.has(row.name));
		const rows = [
			`<label class="sp-entry__user"><input type="checkbox" data-user="__all__"${
				all_checked ? " checked" : ""
			}> ${hrms.time.escape_html(__("All Users"))}</label>`,
		];
		visible.forEach((row) => {
			rows.push(
				`<label class="sp-entry__user"><input type="checkbox" data-user="${hrms.time.escape_html(
					row.name,
				)}"${state.selected.has(row.name) ? " checked" : ""}> ${hrms.time.escape_html(
					hrms.time.employee_label(row),
				)}</label>`,
			);
		});
		$root.find(".sp-entry__users").html(rows.join(""));
	};

	const render_selected = () => {
		const picked = state.employees.filter((row) => state.selected.has(row.name));
		picked.sort((a, b) =>
			hrms.time.employee_label(a).localeCompare(hrms.time.employee_label(b), undefined, {
				sensitivity: "base",
			}),
		);
		$root.find(".sp-entry__picked").html(
			picked
				.map(
					(row) =>
						`<div class="sp-entry__picked-item">${hrms.time.escape_html(
							hrms.time.employee_label(row),
						)}</div>`,
				)
				.join(""),
		);
	};

	const toggle_working_now = () => {
		const on = $root.find(".sp-entry__working-now").is(":checked");
		$root.find(".sp-entry__end").prop("disabled", on);
		$root.find('.sp-entry__icon-btn[data-time="end"]').prop("disabled", on);
		$root.find(".sp-entry__time-field").eq(1).toggleClass("is-disabled", on);
	};

	const collect = () => {
		if (!state.selected.size) {
			frappe.msgprint(__("Select at least one user."));
			return null;
		}
		const attendance_date = $root.find(".sp-entry__date").val();
		const in_time = $root.find(".sp-entry__start").val();
		const working_now = $root.find(".sp-entry__working-now").is(":checked") ? 1 : 0;
		const out_time = $root.find(".sp-entry__end").val();
		if (!attendance_date) {
			frappe.msgprint(__("Date is required."));
			return null;
		}
		if (!in_time) {
			frappe.msgprint(__("Start time is required."));
			return null;
		}
		if (!working_now && !out_time) {
			frappe.msgprint(__("End time is required."));
			return null;
		}
		return {
			employees: Array.from(state.selected),
			attendance_date,
			in_time: hrms.time.to_clock(in_time),
			out_time: working_now ? null : hrms.time.to_clock(out_time),
			shift: $root.find(".sp-entry__job").val() || null,
			comment: $root.find(".sp-entry__comment").val(),
			working_now,
		};
	};

	const submit = (add_next) => {
		const values = collect();
		if (!values) {
			return;
		}
		frappe.call({
			method: "hrms.hr.doctype.attendance.attendance.add_hours_entries",
			args: values,
			freeze: true,
			callback(r) {
				if (!r.message) {
					return;
				}
				const count = Array.isArray(r.message) ? r.message.length : 1;
				frappe.show_alert({
					message: count === 1 ? __("Entry added") : __("{0} entries added", [count]),
					indicator: "green",
				});
				hrms.time.refresh_hours_views(listview);
				if (add_next) {
					$root.find(".sp-entry__comment").val("");
					return;
				}
				dialog.hide();
			},
		});
	};

	$root.on("change", ".sp-entry__department", function () {
		state.department = $(this).val() || "";
		render_users();
	});
	$root.on("change", ".sp-entry__users input[type=checkbox]", function () {
		const value = $(this).data("user");
		const checked = $(this).is(":checked");
		if (value === "__all__") {
			visible_employees().forEach((row) => {
				if (checked) {
					state.selected.add(row.name);
				} else {
					state.selected.delete(row.name);
				}
			});
		} else if (checked) {
			state.selected.add(String(value));
		} else {
			state.selected.delete(String(value));
		}
		render_users();
		render_selected();
	});
	$root.on("change", ".sp-entry__job", function () {
		const name = $(this).val();
		const shift = state.shifts.find((row) => row.name === name);
		if (!shift) {
			return;
		}
		const start = hrms.time.to_hhmm(shift.start_time);
		const end = hrms.time.to_hhmm(shift.end_time);
		if (start) {
			$root.find(".sp-entry__start").val(start);
		}
		if (end) {
			$root.find(".sp-entry__end").val(end);
		}
	});
	$root.on("change", ".sp-entry__working-now", toggle_working_now);
	$root.on("click", ".sp-entry__date-btn", () => {
		const input = $root.find(".sp-entry__date").get(0);
		if (input?.showPicker) {
			input.showPicker();
		} else {
			input?.focus();
		}
	});
	$root.on("click", ".sp-entry__icon-btn[data-time]", function () {
		const which = $(this).data("time");
		const input = $root.find(which === "end" ? ".sp-entry__end" : ".sp-entry__start").get(0);
		if (input?.disabled) {
			return;
		}
		if (input?.showPicker) {
			input.showPicker();
		} else {
			input?.focus();
		}
	});
	$root.on("click", "[data-act=add]", () => submit(false));
	$root.on("click", "[data-act=next]", () => submit(true));
	$root.on("click", "[data-act=cancel]", () => dialog.hide());

	dialog.show();
	hrms.time.mount_dialog_html(dialog, "entry_body", $root);

	frappe.call({
		method: "hrms.hr.doctype.attendance.attendance.get_hours_filter_options",
		callback(r) {
			state.employees = r.message?.employees || [];
			state.departments = r.message?.departments || [];
			state.shifts = r.message?.shifts || [];
			const $dept = $root.find(".sp-entry__department");
			state.departments.forEach((row) => {
				$dept.append(
					`<option value="${hrms.time.escape_html(row.name)}">${hrms.time.escape_html(row.name)}</option>`,
				);
			});
			if (state.department) {
				$dept.val(state.department);
			}
			const $job = $root.find(".sp-entry__job");
			state.shifts.forEach((row) => {
				$job.append(
					`<option value="${hrms.time.escape_html(row.name)}">${hrms.time.escape_html(row.name)}</option>`,
				);
			});
			if (preset_shift && state.shifts.some((row) => row.name === preset_shift)) {
				$job.val(preset_shift);
			} else if (state.shifts.length) {
				$job.val(state.shifts[0].name);
			}
			$job.trigger("change");
			if (opts.in_time) {
				const start = hrms.time.to_hhmm(opts.in_time);
				if (start) {
					$root.find(".sp-entry__start").val(start);
				}
			}
			if (opts.out_time) {
				const end = hrms.time.to_hhmm(opts.out_time);
				if (end) {
					$root.find(".sp-entry__end").val(end);
				}
			}
			render_users();
			render_selected();
		},
	});
};

hrms.time.show_edit_entry_dialog = function (listview, name, pair = {}) {
	const args = { name };
	if (pair && pair.in_log) {
		args.in_log = pair.in_log;
		args.out_log = pair.out_log || null;
	}
	frappe.call({
		method: "hrms.hr.doctype.attendance.attendance.get_hours_entry",
		args,
		callback(r) {
			const row = r.message || {};
			const dialog = new frappe.ui.Dialog({
				title: __("Modify Working Entry"),
				fields: [
					{
						fieldname: "shift",
						label: __("Shift"),
						fieldtype: "Link",
						options: "Shift Type",
						default: row.shift,
					},
					{
						fieldname: "attendance_date",
						label: __("Date"),
						fieldtype: "Date",
						reqd: 1,
						default: row.attendance_date,
					},
					{
						fieldname: "in_time",
						label: __("Time"),
						fieldtype: "Time",
						reqd: 1,
						default: row.in_time,
					},
					{ fieldtype: "Column Break" },
					{
						fieldname: "out_time",
						label: __("To"),
						fieldtype: "Time",
						default: row.out_time,
					},
					{ fieldtype: "Column Break" },
					{
						fieldname: "working_now",
						label: __("Working Now"),
						fieldtype: "Check",
						default: row.working_now,
					},
					{ fieldtype: "Section Break" },
					{
						fieldname: "comment",
						label: __("Comment"),
						fieldtype: "Small Text",
						default: row.comment,
					},
				],
				primary_action_label: __("Save"),
				secondary_action_label: __("Cancel"),
				secondary_action() {
					dialog.hide();
				},
				primary_action(values) {
					const payload = Object.assign({ name }, values);
					if (row.in_log) {
						payload.in_log = row.in_log;
						payload.out_log = row.out_log || null;
					}
					frappe.call({
						method: "hrms.hr.doctype.attendance.attendance.update_hours_entry",
						args: payload,
						freeze: true,
						callback(res) {
							if (res.message) {
								dialog.hide();
								frappe.show_alert({ message: __("Entry updated"), indicator: "green" });
								listview.refresh();
							}
						},
					});
				},
			});

			const toggle_out = () => {
				const on = cint(dialog.get_value("working_now"));
				dialog.set_df_property("out_time", "reqd", on ? 0 : 1);
				dialog.set_df_property("out_time", "hidden", on ? 1 : 0);
			};
			dialog.fields_dict.working_now.df.onchange = toggle_out;
			dialog.show();
			toggle_out();
		},
	});
};

hrms.time.show_add_absence_dialog = function (listview) {
	const dialog = new frappe.ui.Dialog({
		title: __("Add Absence"),
		fields: [
			{
				fieldname: "employee",
				label: __("Employee"),
				fieldtype: "Link",
				options: "Employee",
				reqd: 1,
				default: hrms.time.get_filter_value(listview, "employee") || undefined,
			},
			{
				fieldname: "from_date",
				label: __("From"),
				fieldtype: "Date",
				reqd: 1,
				default: hrms.time.default_entry_date(listview),
			},
			{
				fieldname: "to_date",
				label: __("To"),
				fieldtype: "Date",
				reqd: 1,
				default: hrms.time.default_entry_date(listview),
			},
			{
				fieldname: "leave_type",
				label: __("Leave Type"),
				fieldtype: "Link",
				options: "Leave Type",
				description: __("Leave empty to mark Absent."),
			},
			hrms.time.comment_field(),
		],
		primary_action_label: __("Add Absence"),
		primary_action(values) {
			frappe.call({
				method: "hrms.hr.doctype.attendance.attendance.add_absence",
				args: values,
				freeze: true,
				callback(r) {
					if (r.message) {
						dialog.hide();
						frappe.show_alert({ message: r.message.message || __("Absence added"), indicator: "green" });
						listview.refresh();
					}
				},
			});
		},
	});
	dialog.show();
};

hrms.time.ADJUST_TYPES_KEY = "sp_hours_adjust_types";

hrms.time.default_adjust_types = function () {
	return [{ id: "1", label: "1", unit: "Hours", direction: "Addition", hours: 8 }];
};

hrms.time.load_adjust_types = function () {
	try {
		const stored = JSON.parse(localStorage.getItem(hrms.time.ADJUST_TYPES_KEY) || "[]");
		if (Array.isArray(stored) && stored.length) {
			return stored;
		}
	} catch (_err) {
		/* use defaults */
	}
	return hrms.time.default_adjust_types();
};

hrms.time.save_adjust_types = function (types) {
	localStorage.setItem(hrms.time.ADJUST_TYPES_KEY, JSON.stringify(types));
};

hrms.time.employee_sort_name = hrms.time.employee_label;

hrms.time.option_html = function (value, label, selected) {
	return `<option value="${escape_html(value)}"${selected ? " selected" : ""}>${escape_html(
		label,
	)}</option>`;
};

hrms.time.show_add_adjustment_dialog = function (listview) {
	const today = frappe.datetime.get_today();
	const date_filter = hrms.time.get_filter_value(listview, "attendance_date");
	let default_date = today;
	if (Array.isArray(date_filter) && date_filter[0]) {
		default_date = String(date_filter[0]).slice(0, 10);
	} else if (typeof date_filter === "string" && date_filter) {
		default_date = date_filter.slice(0, 10);
	}
	const preselect_employee = hrms.time.get_filter_value(listview, "employee");
	const preselect_department = hrms.time.get_filter_value(listview, "department") || "";
	const radio_name = `sp-adj-mode-${Date.now()}`;
	const calendar_icon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`;

	const dialog = new frappe.ui.Dialog({
		title: __("Add Adjustment"),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "layout" }],
	});
	dialog.$wrapper.addClass("sp-adj-modal");
	dialog.fields_dict.layout.$wrapper.html(`
		<div class="sp-adj">
			<div class="sp-adj__cols">
				<div class="sp-adj__col sp-adj__col--users">
					<select class="sp-adj__select sp-adj__dept" aria-label="${escape_html(__("Department"))}">
						<option value="">${escape_html(__("All Departments"))}</option>
					</select>
					<div class="sp-adj__users" role="group" aria-label="${escape_html(__("Users"))}"></div>
				</div>
				<div class="sp-adj__col sp-adj__col--date">
					<div class="sp-adj__date-row">
						<input type="date" class="sp-adj__date" value="${escape_html(default_date)}" />
						<button type="button" class="sp-adj__cal" aria-label="${escape_html(__("Pick date"))}">${calendar_icon}</button>
					</div>
					<div class="sp-adj__preview"></div>
				</div>
				<div class="sp-adj__col sp-adj__col--form">
					<div class="sp-adj__radios">
						<label class="sp-adj__radio">
							<input type="radio" name="${radio_name}" value="adjustment" checked />
							${escape_html(__("Adjustment"))}
						</label>
						<label class="sp-adj__radio">
							<input type="radio" name="${radio_name}" value="job" />
							${escape_html(__("Adjustment (Job&Shift)"))}
						</label>
					</div>
					<div class="sp-adj__mode sp-adj__mode--adjustment">
						<div class="sp-adj__labeled-row">
							<span class="sp-adj__label">${escape_html(__("Adjust Type:"))}</span>
							<select class="sp-adj__select sp-adj__type"></select>
							<button type="button" class="sp-adj__edit">${escape_html(__("Edit"))}</button>
						</div>
						<div class="sp-adj__labeled-row">
							<span class="sp-adj__label">${escape_html(__("Type:"))}</span>
							<select class="sp-adj__select sp-adj__unit">
								<option value="Hours">${escape_html(__("Hours"))}</option>
							</select>
							<select class="sp-adj__select sp-adj__direction">
								<option value="Addition">${escape_html(__("Addition"))}</option>
								<option value="Deduction">${escape_html(__("Deduction"))}</option>
							</select>
							<input type="number" class="sp-adj__input sp-adj__hours" min="0.01" step="0.1" value="8.0" />
						</div>
					</div>
					<div class="sp-adj__mode sp-adj__mode--job" hidden>
						<label class="sp-adj__stack">
							<span class="sp-adj__label">${escape_html(__("Job:"))}</span>
							<select class="sp-adj__select sp-adj__job"></select>
						</label>
						<label class="sp-adj__stack">
							<span class="sp-adj__label">${escape_html(__("Hours:"))}</span>
							<span class="sp-adj__hours-row">
								<select class="sp-adj__select sp-adj__job-direction">
									<option value="Addition">${escape_html(__("Addition"))}</option>
									<option value="Deduction">${escape_html(__("Deduction"))}</option>
								</select>
								<input type="number" class="sp-adj__input sp-adj__job-hours" min="0.01" step="0.01" value="8.00" />
							</span>
						</label>
					</div>
					<textarea class="sp-adj__comment" rows="6" placeholder="${escape_html(__("comment"))}"></textarea>
				</div>
			</div>
			<div class="sp-adj__footer">
				<button type="button" class="sp-adj__btn sp-adj__btn--primary sp-adj__add">${escape_html(__("Add"))}</button>
				<button type="button" class="sp-adj__btn sp-adj__btn--primary sp-adj__add-next">${escape_html(__("Add & Next"))}</button>
				<button type="button" class="sp-adj__btn sp-adj__btn--muted sp-adj__cancel">${escape_html(__("Cancel"))}</button>
			</div>
		</div>
	`);

	const $root = dialog.fields_dict.layout.$wrapper.find(".sp-adj");
	const $dept = $root.find(".sp-adj__dept");
	const $users = $root.find(".sp-adj__users");
	const $preview = $root.find(".sp-adj__preview");
	const $type = $root.find(".sp-adj__type");
	const $job = $root.find(".sp-adj__job");
	let employees = [];
	let types = hrms.time.load_adjust_types();

	const selected_employees = () =>
		$users
			.find(".sp-adj__user:not(.sp-adj__user--all) input:checked")
			.map((_, el) => el.value)
			.get();

	const render_types = () => {
		$type.html(types.map((row) => hrms.time.option_html(row.id, row.label, row.id === types[0]?.id)).join(""));
		apply_type($type.val());
	};

	const apply_type = (id) => {
		const row = types.find((item) => String(item.id) === String(id)) || types[0];
		if (!row) {
			return;
		}
		$root.find(".sp-adj__unit").val(row.unit || "Hours");
		$root.find(".sp-adj__direction").val(row.direction || "Addition");
		$root.find(".sp-adj__hours").val(flt(row.hours) || 8);
	};

	const update_preview = () => {
		const names = $users
			.find(".sp-adj__user:not(.sp-adj__user--all) input:checked")
			.map((_, el) => $(el).closest("label").text().trim())
			.get();
		if (!names.length) {
			$preview.html("");
			return;
		}
		$preview.html(names.map((name) => `<div>${escape_html(name)}</div>`).join(""));
	};

	const render_users = () => {
		const department = $dept.val() || "";
		const visible = employees
			.filter((row) => hrms.time.employee_in_department(row, department))
			.slice()
			.sort((a, b) =>
				hrms.time.employee_label(a).localeCompare(hrms.time.employee_label(b), undefined, {
					sensitivity: "base",
				}),
			);
		const selected = new Set(selected_employees());
		if (typeof preselect_employee === "string" && preselect_employee && !selected.size) {
			selected.add(preselect_employee);
		}
		const all_checked = visible.length && visible.every((row) => selected.has(row.name));
		const rows = [
			`<label class="sp-adj__user sp-adj__user--all"><input type="checkbox"${all_checked ? " checked" : ""} /> ${escape_html(
				__("All Users"),
			)}</label>`,
		];
		visible.forEach((row) => {
			const label = hrms.time.employee_sort_name(row);
			rows.push(
				`<label class="sp-adj__user"><input type="checkbox" value="${escape_html(row.name)}"${
					selected.has(row.name) ? " checked" : ""
				} /> ${escape_html(label)}</label>`,
			);
		});
		$users.html(rows.join(""));
		update_preview();
	};

	const set_mode = () => {
		const job_mode = $root.find(`input[name="${radio_name}"]:checked`).val() === "job";
		$root.find(".sp-adj__mode--adjustment").prop("hidden", job_mode);
		$root.find(".sp-adj__mode--job").prop("hidden", !job_mode);
	};

	const current_values = () => {
		const job_mode = $root.find(`input[name="${radio_name}"]:checked`).val() === "job";
		return {
			employees: selected_employees(),
			attendance_date: $root.find(".sp-adj__date").val(),
			mode: job_mode ? "job" : "adjustment",
			job: job_mode ? $job.val() : "",
			adjust_type: job_mode ? "" : $type.find("option:selected").text(),
			direction: job_mode ? $root.find(".sp-adj__job-direction").val() : $root.find(".sp-adj__direction").val(),
			hours: job_mode ? $root.find(".sp-adj__job-hours").val() : $root.find(".sp-adj__hours").val(),
			comment: $root.find(".sp-adj__comment").val(),
		};
	};

	const save = (close_after) => {
		const values = current_values();
		if (!values.employees.length) {
			frappe.msgprint(__("Select at least one user."));
			return;
		}
		if (!values.attendance_date) {
			frappe.msgprint(__("Date is required."));
			return;
		}
		if (values.mode === "job" && !values.job) {
			frappe.msgprint(__("Select a job."));
			return;
		}
		if (!flt(values.hours)) {
			frappe.msgprint(__("Hours cannot be zero."));
			return;
		}
		frappe.call({
			method: "hrms.hr.doctype.attendance.attendance.add_hours_adjustment",
			args: Object.assign({}, values, { employees: JSON.stringify(values.employees) }),
			freeze: true,
			callback(r) {
				if (!r.message) {
					return;
				}
				frappe.show_alert({ message: __("Adjustment added"), indicator: "green" });
				listview.refresh();
				if (close_after) {
					dialog.hide();
					return;
				}
				$root.find(".sp-adj__comment").val("");
			},
		});
	};

	$root.on("change", ".sp-adj__dept", render_users);
	$root.on("change", ".sp-adj__user--all input", function () {
		$users.find(".sp-adj__user:not(.sp-adj__user--all) input").prop("checked", this.checked);
		update_preview();
	});
	$root.on("change", ".sp-adj__user:not(.sp-adj__user--all) input", function () {
		const $boxes = $users.find(".sp-adj__user:not(.sp-adj__user--all) input");
		$users.find(".sp-adj__user--all input").prop("checked", $boxes.length && $boxes.length === $boxes.filter(":checked").length);
		update_preview();
	});
	$root.on("change", `input[name="${radio_name}"]`, set_mode);
	$root.on("change", ".sp-adj__type", function () {
		apply_type(this.value);
	});
	$root.find(".sp-adj__cal").on("click", () => {
		const input = $root.find(".sp-adj__date").get(0);
		if (input?.showPicker) {
			input.showPicker();
		} else {
			input?.focus();
		}
	});
	$root.find(".sp-adj__add").on("click", () => save(true));
	$root.find(".sp-adj__add-next").on("click", () => save(false));
	$root.find(".sp-adj__cancel").on("click", () => dialog.hide());
	$root.find(".sp-adj__edit").on("click", () => {
		const current = types.find((row) => String(row.id) === String($type.val())) || types[0] || hrms.time.default_adjust_types()[0];
		const editor = new frappe.ui.Dialog({
			title: __("Edit Adjust Type"),
			fields: [
				{ fieldname: "label", label: __("Name"), fieldtype: "Data", reqd: 1, default: current.label },
				{
					fieldname: "unit",
					label: __("Type"),
					fieldtype: "Select",
					options: "Hours",
					default: current.unit || "Hours",
				},
				{
					fieldname: "direction",
					label: __("Direction"),
					fieldtype: "Select",
					options: "Addition\nDeduction",
					default: current.direction || "Addition",
				},
				{ fieldname: "hours", label: __("Hours"), fieldtype: "Float", default: current.hours || 8 },
			],
			primary_action_label: __("Save"),
			primary_action(values) {
				const next = types.map((row) =>
					String(row.id) === String(current.id) ? Object.assign({}, row, values) : row,
				);
				if (!next.some((row) => String(row.id) === String(current.id))) {
					next.push(Object.assign({ id: values.label || String(next.length + 1) }, values));
				}
				types = next;
				hrms.time.save_adjust_types(types);
				render_types();
				$type.val(current.id);
				apply_type(current.id);
				editor.hide();
			},
		});
		editor.show();
	});

	render_types();
	dialog.show();
	hrms.time.mount_dialog_html(dialog, "layout", $root);

	frappe.call({
		method: "hrms.hr.doctype.attendance.attendance.get_hours_filter_options",
		callback(r) {
			const payload = r.message || {};
			employees = payload.employees || [];
			(payload.departments || []).forEach((row) => {
				$dept.append(hrms.time.option_html(row.name, row.name, row.name === preselect_department));
			});
			if (preselect_department) {
				$dept.val(preselect_department);
			}
			const job_rows = [];
			const seen = new Set();
			(payload.jobs || []).concat(payload.shifts || []).forEach((row) => {
				if (row?.name && !seen.has(row.name)) {
					seen.add(row.name);
					job_rows.push(row);
				}
			});
			job_rows.forEach((row, index) => {
				$job.append(hrms.time.option_html(row.name, row.name, index === 0));
			});
			if (!$job.children().length) {
				$job.append(hrms.time.option_html("", __("No jobs"), true));
			}
			render_users();
		},
	});
};

hrms.time.show_add_hours_comment_dialog = function (listview, name) {
	const dialog = new frappe.ui.Dialog({
		title: __("Add Comment"),
		fields: [hrms.time.comment_field()],
		primary_action_label: __("Add Comment"),
		primary_action(values) {
			frappe.call({
				method: "hrms.hr.doctype.attendance.attendance.add_hours_comment",
				args: { name, comment: values.comment },
				freeze: true,
				callback() {
					dialog.hide();
					frappe.show_alert({ message: __("Comment added"), indicator: "green" });
					listview.refresh();
				},
			});
		},
	});
	dialog.show();
};

(function patch_new_attendance() {
	if (!frappe.new_doc || frappe.new_doc.__sp_attendance_patched) {
		return;
	}
	const original_new_doc = frappe.new_doc;
	frappe.new_doc = function (doctype, opts, init_callback) {
		if (doctype === "Attendance" && (opts == null || $.isPlainObject(opts))) {
			hrms.time.open_add_attendance(opts || {});
			return;
		}
		return original_new_doc.apply(this, arguments);
	};
	frappe.new_doc.__sp_attendance_patched = true;
})();

function patch_attendance_list_routes() {
	if (!frappe.set_route || frappe.set_route.__sp_hide_attendance_list) {
		return;
	}
	const original = frappe.set_route;
	frappe.set_route = function () {
		if (hrms.time.is_blocked_attendance_list_route(hrms.time.normalize_route_args(arguments))) {
			return original.apply(this, hrms.time.ATTENDANCE_PORTAL_ROUTE);
		}
		return original.apply(this, arguments);
	};
	frappe.set_route.__sp_hide_attendance_list = true;
}

function redirect_attendance_list_if_needed() {
	if (window._staff_pro_attendance_list_redirecting) {
		return;
	}
	const route = frappe.get_route?.() || [];
	const parts = route.length
		? route
		: hrms.time.route_parts_from_value(window.location.pathname || "");
	if (!hrms.time.is_blocked_attendance_list_route(parts)) {
		return;
	}
	window._staff_pro_attendance_list_redirecting = true;
	Promise.resolve(hrms.time.go_attendance_portal()).finally(() => {
		window._staff_pro_attendance_list_redirecting = false;
	});
}

patch_attendance_list_routes();
$(document).on("app_ready", () => {
	patch_attendance_list_routes();
	redirect_attendance_list_if_needed();
});
$(document).on("page-change", redirect_attendance_list_if_needed);
