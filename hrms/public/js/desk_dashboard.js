frappe.provide("hrms.ui");

if (typeof window !== "undefined" && typeof window.__ !== "function") {
	window.__ = (text) => text;
}

const ICONS = {
	users: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
	userPlus: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="16" y1="11" x2="22" y2="11"/></svg>`,
	userMinus: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="22" y1="11" x2="16" y2="11"/></svg>`,
	spark: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l1.6 5.2L19 10l-5.4 1.8L12 17l-1.6-5.2L5 10l5.4-1.8L12 3z"/></svg>`,
	calendar: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
	clock: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/></svg>`,
	check: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>`,
	alert: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
	wallet: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="14" rx="2"/><path d="M2 10h20"/><circle cx="16" cy="15" r="1.4"/></svg>`,
	briefcase: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`,
	upload: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 16V4m0 0 4 4m-4-4-4 4"/><path d="M4 20h16"/></svg>`,
	org: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="3" width="6" height="6" rx="1"/><rect x="3" y="15" width="6" height="6" rx="1"/><rect x="15" y="15" width="6" height="6" rx="1"/><path d="M12 9v3m0 0H6v3m6-3h6v3"/></svg>`,
	chart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19V5"/><path d="M4 19h16"/><rect x="7" y="11" width="3" height="8" rx="1"/><rect x="12" y="7" width="3" height="12" rx="1"/><rect x="17" y="13" width="3" height="6" rx="1"/></svg>`,
	file: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>`,
};

const DASHBOARDS = {
	"Human Resource": {
		kicker: __("People"),
		subtitle: __("Headcount, hiring, and movement across the company."),
		empty_text: __("Add employees and these cards fill with live hiring, exits, and diversity."),
		create_label: __("Add Employee"),
		create_doctype: "Employee",
		pills: [
			{ label: __("Add Agent"), icon: "userPlus", hue: "#4DB0F5", doctype: "Employee" },
			{ label: __("Import Agents"), icon: "upload", hue: "#4DB0F5", action: "import-employee" },
			{ label: __("Agents"), icon: "users", hue: "#3DDCB0", route: ["List", "Employee"] },
			{ label: __("Team Structure"), icon: "org", hue: "#3DDCB0", route: ["organizational-chart"] },
			{ label: __("New Hire Onboarding"), icon: "spark", hue: "#60A5FA", route: ["List", "Employee Onboarding"] },
			{ label: __("Offboarding"), icon: "userMinus", hue: "#F472B6", route: ["List", "Employee Separation"] },
			{ label: __("Concerns"), icon: "alert", hue: "#F5C43C", route: ["List", "Employee Grievance"] },
		],
	},
	Attendance: {
		kicker: __("Time"),
		subtitle: __("Who is in, who is out, and how the month is tracking."),
		empty_text: __("Mark attendance or sync check-ins and this view turns into a daily pulse."),
		create_label: __("Mark Attendance"),
		create_doctype: "Attendance",
		pills: [
			{ label: __("Mark Attendance"), icon: "check", hue: "#3DDCB0", route: ["List", "Attendance"] },
			{ label: __("Clock In/Out"), icon: "clock", hue: "#3DD6E8", route: ["List", "Employee Checkin"] },
			{ label: __("Shift Schedule"), icon: "calendar", hue: "#3DD6E8", route: ["List", "Shift Assignment"] },
			{ label: __("Schedule Correction"), icon: "file", hue: "#F5C43C", route: ["List", "Attendance Request"] },
		],
	},
	Payroll: {
		kicker: __("Pay"),
		subtitle: __("Salary structures, payouts, and incentives at a glance."),
		empty_text: __("Create a salary structure and this page starts showing outflow and coverage."),
		create_label: __("New Salary Structure"),
		create_doctype: "Salary Structure",
		pills: [
			{ label: __("Pay Structure"), icon: "briefcase", hue: "#3DDCB0", route: ["List", "Salary Structure"] },
			{ label: __("Run Payroll"), icon: "wallet", hue: "#3DDCB0", route: ["List", "Payroll Entry"] },
			{ label: __("Pay Stubs"), icon: "file", hue: "#3DDCB0", route: ["List", "Salary Slip"] },
			{ label: __("Incentives"), icon: "spark", hue: "#F5C43C", route: ["List", "Employee Incentive"] },
		],
	},
	Recruitment: {
		kicker: __("Talent"),
		subtitle: __("Open roles, pipeline health, and how fast you hire."),
		empty_text: __("Post a job opening and applicants, offers, and time-to-fill appear here."),
		create_label: __("New Job Opening"),
		create_doctype: "Job Opening",
		pills: [
			{ label: __("Open Positions"), icon: "briefcase", hue: "#60A5FA", doctype: "Job Opening" },
			{ label: __("Candidates"), icon: "users", hue: "#60A5FA", route: ["List", "Job Applicant"] },
			{ label: __("Offer Letters"), icon: "spark", hue: "#3DDCB0", route: ["List", "Job Offer"] },
			{ label: __("Interviews"), icon: "calendar", hue: "#60A5FA", route: ["List", "Interview"] },
		],
	},
};

const LIST_EMPTY = {
	Employee: {
		title: __("No people on the roster yet"),
		text: __("Add your first employee and Staff Pro starts tracking headcount, hiring, and org structure."),
		button: __("Add Employee"),
		doctype: "Employee",
	},
	Attendance: {
		title: __("No attendance recorded"),
		text: __("Mark today's attendance or import check-ins to see who is present, late, or away."),
		button: __("Mark Attendance"),
		doctype: "Attendance",
	},
	"Employee Checkin": {
		title: __("No check-ins yet"),
		text: __("The first check-in turns this list into a live time clock."),
		button: __("Add Checkin"),
		doctype: "Employee Checkin",
	},
	"Job Opening": {
		title: __("No open roles"),
		text: __("Create a job opening and the talent pipeline starts here."),
		button: __("New Job Opening"),
		doctype: "Job Opening",
	},
	"Salary Slip": {
		title: __("No salary slips yet"),
		text: __("Run payroll and slips will land in this list automatically."),
		button: __("Open Payroll Entry"),
		route: ["List", "Payroll Entry"],
	},
};

const DASHBOARD_ALIASES = {
	Workforce: "Human Resource",
	People: "Human Resource",
	Time: "Attendance",
	Pay: "Payroll",
	Talent: "Recruitment",
};

function dashboard_name() {
	const route = frappe.get_route?.() || [];
	if (route[0] === "dashboard-view" || route[0] === "dashboard") {
		const name = route[1] || "";
		return DASHBOARD_ALIASES[name] || name;
	}
	return "";
}

function dashboard_config() {
	const name = dashboard_name();
	return DASHBOARDS[name] || {
		kicker: name || __("Dashboard"),
		subtitle: __("A live snapshot of this area."),
		empty_text: __("Add records and the numbers and charts will fill in."),
		create_label: __("Get started"),
		create_doctype: "Employee",
		pills: [],
	};
}

function escape_html(text) {
	const esc = frappe.utils && frappe.utils.escape_html;
	if (typeof esc === "function" && esc !== escape_html) return esc(text);
	return $("<div>").text(text || "").html();
}

function go(route) {
	if (!route) return;
	frappe.set_route(...route);
}

function new_doc(doctype) {
	if (!doctype) return;
	if (frappe.new_doc) {
		frappe.new_doc(doctype);
		return;
	}
	frappe.set_route("Form", doctype, "new");
}

function start_action(cfg) {
	if (cfg.create_doctype) {
		new_doc(cfg.create_doctype);
		return;
	}
	go(cfg.create_route);
}

function open_import_employee() {
	if (frappe.views.data_import) {
		frappe.set_route("List", "Data Import", "List");
		return;
	}
	frappe.set_route("List", "Employee", "List");
}

function run_pill(pill) {
	if (pill.action === "import-employee") {
		open_import_employee();
		return;
	}
	if (pill.doctype) {
		new_doc(pill.doctype);
		return;
	}
	go(pill.route);
}

function page_root() {
	const route = frappe.get_route?.() || [];
	if (route[0] === "dashboard-view" || route[0] === "dashboard") {
		return $("#page-dashboard-view, .page-container[data-page-route='dashboard-view']").first();
	}
	if (route[0] === "List") {
		return $(".page-container[id^='page-List/']").filter(":visible").first();
	}
	return $("#page-Workspaces").filter(":visible").first();
}

const CELEBRATION_PERIODS = {
	weekly: __("Weekly"),
	monthly: __("Monthly"),
	yearly: __("Yearly"),
};

const CELEBRATION_TYPES = {
	all: __("All"),
	birthday: __("Birthdays"),
	anniversary: __("Anniversaries"),
};

function celebration_empty_message(eventType) {
	if (eventType === "birthday") {
		return __("No upcoming birthdays in this period.");
	}
	if (eventType === "anniversary") {
		return __("No upcoming anniversaries in this period.");
	}
	return __("No upcoming birthdays or anniversaries in this period.");
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

function celebration_avatar(row) {
	if (row.image) {
		return `<img class="sp-celebrations__avatar-img" src="${escape_html(row.image)}" alt="">`;
	}
	return `<span class="sp-celebrations__avatar-fallback">${escape_html(employee_initials(row.employee_name))}</span>`;
}

function celebration_type_label(row) {
	const isAnniversary = row.event_type === "anniversary";
	const icon = isAnniversary ? "🏅" : "🎂";
	let label = row.event_label || (isAnniversary ? __("Work Anniversary") : __("Birthday"));

	if (isAnniversary && row.years_completed) {
		label = __("{0} Year Work Anniversary", [row.years_completed]);
	}

	return `
		<span class="sp-celebrations__type sp-celebrations__type--${escape_html(row.event_type)}">
			<span class="sp-celebrations__type-icon" aria-hidden="true">${icon}</span>
			<span class="sp-celebrations__type-label">${escape_html(label)}</span>
		</span>
	`;
}

function parse_celebration_response(message) {
	if (Array.isArray(message)) {
		return { rows: message, fallback: false };
	}

	return {
		rows: message?.events || [],
		fallback: Boolean(message?.fallback),
	};
}

function render_celebration_rows(rows, fallback = false, eventType = "all") {
	if (!rows.length) {
		return `
			<div class="sp-celebrations__empty">
				<p>${escape_html(celebration_empty_message(eventType))}</p>
			</div>
		`;
	}

	const fallbackNote = fallback
		? `<p class="sp-celebrations__fallback-note">${escape_html(__("None in this period. Next up:"))}</p>`
		: "";

	const rowsHtml = rows
		.map(
			(row) => `
			<button type="button" class="sp-celebrations__row sp-celebrations__row--${row.event_type}" data-employee="${escape_html(row.employee)}">
				<span class="sp-celebrations__avatar">${celebration_avatar(row)}</span>
				<span class="sp-celebrations__meta">
					<span class="sp-celebrations__name">${escape_html(row.employee_name)}</span>
					<span class="sp-celebrations__details">
						${celebration_type_label(row)}
						${row.subtitle ? `<span class="sp-celebrations__role">${escape_html(row.subtitle)}</span>` : ""}
					</span>
				</span>
				<span class="sp-celebrations__date">
					<span class="sp-celebrations__day">${escape_html(String(row.day))}</span>
					<span class="sp-celebrations__month">${escape_html(row.month)}</span>
				</span>
			</button>
		`
		)
		.join("");

	return `${fallbackNote}${rowsHtml}`;
}

function reload_celebrations($widget) {
	const period = $widget.find(".sp-celebrations__period").val() || "weekly";
	const eventType = $widget.find(".sp-celebrations__type-filter").val() || "all";
	load_celebrations($widget, period, eventType);
}

function load_celebrations($widget, period, eventType = "all") {
	const $list = $widget.find(".sp-celebrations__list");
	$list.addClass("is-loading");

	frappe.call({
		method: "hrms.hr.desk_dashboard.get_upcoming_celebrations",
		args: { period, event_type: eventType },
		callback(r) {
			$list.removeClass("is-loading");
			const { rows, fallback } = parse_celebration_response(r.message);
			$list.html(render_celebration_rows(rows, fallback, eventType));
			$list.find(".sp-celebrations__row").on("click", function () {
				const employee = $(this).data("employee");
				if (employee) frappe.set_route("Form", "Employee", employee);
			});
		},
		error() {
			$list.removeClass("is-loading");
			$list.html(`
				<div class="sp-celebrations__empty">
					<p>${escape_html(__("Could not load upcoming celebrations."))}</p>
				</div>
			`);
		},
	});
}

function inject_celebrations($root) {
	if (dashboard_name() !== "Human Resource") {
		$root.find(".sp-dash-split, .sp-dash-celebrations, .sp-dash-payroll").remove();
		return;
	}

	if ($root.find(".sp-dash-split").length) return;

	const $pills = $root.find(".sp-dash-pills").first();
	if (!$pills.length) return;

	const $split = $(`
		<section class="sp-dash-split">
			<section class="sp-dash-panel sp-dash-celebrations" aria-label="${escape_html(__("Birthdays & Anniversaries"))}">
				<div class="sp-dash-panel__head">
					<h2 class="sp-dash-panel__title">${escape_html(__("Birthdays & Anniversaries"))}</h2>
					<div class="sp-dash-panel__filters">
						<label class="sp-dash-panel__filter">
							<span class="sr-only">${escape_html(__("Type"))}</span>
							<select class="sp-celebrations__type-filter sp-dash-panel__select">
								<option value="all">${escape_html(CELEBRATION_TYPES.all)}</option>
								<option value="birthday">${escape_html(CELEBRATION_TYPES.birthday)}</option>
								<option value="anniversary">${escape_html(CELEBRATION_TYPES.anniversary)}</option>
							</select>
						</label>
						<label class="sp-dash-panel__filter">
							<span class="sr-only">${escape_html(__("Period"))}</span>
							<select class="sp-celebrations__period sp-dash-panel__select">
								<option value="weekly">${escape_html(CELEBRATION_PERIODS.weekly)}</option>
								<option value="monthly">${escape_html(CELEBRATION_PERIODS.monthly)}</option>
								<option value="yearly">${escape_html(CELEBRATION_PERIODS.yearly)}</option>
							</select>
						</label>
					</div>
				</div>
				<div class="sp-celebrations__list"></div>
			</section>
			<section class="sp-dash-panel sp-dash-payroll" aria-label="${escape_html(__("Upcoming Payroll"))}">
				<div class="sp-dash-panel__head">
					<h2 class="sp-dash-panel__title">${escape_html(__("Upcoming Payroll"))}</h2>
					<div class="sp-dash-panel__filters">
						<label class="sp-dash-panel__filter">
							<span class="sr-only">${escape_html(__("Period"))}</span>
							<select class="sp-payroll__period sp-dash-panel__select">
								<option value="monthly">${escape_html(__("Monthly"))}</option>
								<option value="weekly">${escape_html(__("Weekly"))}</option>
								<option value="yearly">${escape_html(__("Yearly"))}</option>
							</select>
						</label>
					</div>
				</div>
				<div class="sp-payroll__table-wrap">
					<div class="sp-payroll__table-head">
						<span>${escape_html(__("Agent"))}</span>
						<span>${escape_html(__("Status"))}</span>
						<span>${escape_html(__("Pay Date"))}</span>
						<span>${escape_html(__("Hours"))}</span>
						<span>${escape_html(__("Net Pay"))}</span>
					</div>
					<div class="sp-payroll__list"></div>
				</div>
			</section>
		</section>
	`);

	$pills.after($split);

	const $celebrations = $split.find(".sp-dash-celebrations");
	reload_celebrations($celebrations);
	$celebrations.find(".sp-celebrations__period, .sp-celebrations__type-filter").on("change", function () {
		reload_celebrations($celebrations);
	});

	const $payroll = $split.find(".sp-dash-payroll");
	reload_payroll($payroll);
	$payroll.find(".sp-payroll__period").on("change", function () {
		reload_payroll($payroll);
	});
}

function format_hours(value) {
	const hours = Number(value || 0);
	if (!hours) return "—";
	return `${hours.toFixed(1)}h`;
}

function format_pay_amount(row) {
	if (row.net_pay == null || row.net_pay === "") return "—";
	if (typeof frappe.format === "function") {
		return frappe.format(row.net_pay, { fieldtype: "Currency", options: row.currency || "" });
	}
	return String(row.net_pay);
}

function render_payroll_rows(rows) {
	if (!rows.length) {
		return `
			<div class="sp-payroll__empty">
				<p>${escape_html(__("No payroll activity for this period yet."))}</p>
			</div>
		`;
	}

	return rows
		.map(
			(row) => `
			<button type="button" class="sp-payroll__row" data-employee="${escape_html(row.employee)}" data-slip="${escape_html(row.salary_slip || "")}">
				<span class="sp-payroll__agent">
					<span class="sp-payroll__avatar">${celebration_avatar(row)}</span>
					<span class="sp-payroll__agent-meta">
						<span class="sp-payroll__name">${escape_html(row.employee_name)}</span>
						${row.subtitle ? `<span class="sp-payroll__subtitle">${escape_html(row.subtitle)}</span>` : ""}
					</span>
				</span>
				<span class="sp-payroll__status sp-payroll__status--${escape_html(row.status)}">
					<span class="sp-payroll__status-dot" aria-hidden="true"></span>
					<span class="sp-payroll__status-label">${escape_html(row.status_label)}</span>
				</span>
				<span class="sp-payroll__date">${escape_html(row.pay_date_label || "")}</span>
				<span class="sp-payroll__hours">${escape_html(format_hours(row.hours_worked))}</span>
				<span class="sp-payroll__amount">${escape_html(format_pay_amount(row))}</span>
			</button>
		`
		)
		.join("");
}

function reload_payroll($widget) {
	const period = $widget.find(".sp-payroll__period").val() || "monthly";
	load_payroll($widget, period);
}

function load_payroll($widget, period) {
	const $list = $widget.find(".sp-payroll__list");
	$list.addClass("is-loading");

	frappe.call({
		method: "hrms.hr.desk_dashboard.get_upcoming_payroll",
		args: { period },
		callback(r) {
			$list.removeClass("is-loading");
			const rows = r.message?.rows || [];
			$list.html(render_payroll_rows(rows));
			$list.find(".sp-payroll__row").on("click", function () {
				const slip = $(this).data("slip");
				const employee = $(this).data("employee");
				if (slip) {
					frappe.set_route("Form", "Salary Slip", slip);
					return;
				}
				if (employee) frappe.set_route("Form", "Employee", employee);
			});
		},
		error() {
			$list.removeClass("is-loading");
			$list.html(`
				<div class="sp-payroll__empty">
					<p>${escape_html(__("Could not load upcoming payroll."))}</p>
				</div>
			`);
		},
	});
}

function inject_quick_actions($root) {
	$root.find(".sp-dash-hero").remove();
	$root.removeClass("staff-pro-has-hero");

	const $existing = $root.find(".sp-dash-pills").first();
	if ($existing.length && !$existing.hasClass("sp-dash-pills--v4")) {
		$existing.remove();
	}

	if (!$root.length || $root.find(".sp-dash-pills").length) return;
	const cfg = dashboard_config();
	let $host = $root.find(".dashboard-view").first();
	if (!$host.length) $host = $root.find(".dashboard").first();
	if (!$host.length) $host = $root.find(".layout-main-section").first();
	if (!$host.length) $host = $root;

	const $pills = $(`<nav class="sp-dash-pills sp-dash-pills--v4" aria-label="${escape_html(__("Quick actions"))}"></nav>`);
	cfg.pills.forEach((pill) => {
		const $btn = $(`
			<button type="button" class="sp-dash-pill">
				<span class="sp-dash-pill__icon" style="--sp-icon-accent:${pill.hue || "#3DDCB0"}">${ICONS[pill.icon] || ICONS.spark}</span>
				<span class="sp-dash-pill__label">${escape_html(pill.label)}</span>
			</button>
		`);
		$btn.on("click", () => run_pill(pill));
		$pills.append($btn);
	});

	$host.prepend($pills);
}

function clean_number_cards($root) {
	$root.find(".sp-kpi-icon, .sp-kpi-hint").remove();
	$root
		.find(".number-widget-box, .number-card-container .widget, .number-widget-area .widget")
		.each(function () {
			$(this).removeData("sp-themed").css("--sp-kpi", "");
		});
}

function enhance_empty_charts($root) {
	$root.find(".chart-widget, .dashboard-graph .widget, .widget-chart-box").each(function () {
		const $widget = $(this).closest(".widget");
		if (!$widget.length || $widget.data("sp-empty")) return;

		const body_text = $widget.find(".widget-body, .chart-container, .widget-chart-box").text();
		const is_empty = /no data/i.test(body_text);
		if (!is_empty) return;

		$widget.data("sp-empty", 1);
		const cfg = dashboard_config();
		const $body = $widget.find(".widget-body").first();
		if (!$body.length) return;
		$body.find(".chart-container, .widget-chart-box, .flex.justify-center").hide();
		$body.append(`
			<div class="sp-empty-chart">
				<div class="sp-empty-chart__art">${ICONS.chart}</div>
				<p class="sp-empty-chart__title">${__("Nothing to plot yet")}</p>
				<p class="sp-empty-chart__text">${escape_html(cfg.empty_text)}</p>
				<button type="button" class="sp-empty-chart__btn">${escape_html(cfg.create_label)}</button>
			</div>
		`);
		$body.find(".sp-empty-chart__btn").on("click", () => start_action(cfg));
	});
}

function enhance_list_empty() {
	const route = frappe.get_route?.() || [];
	if (route[0] !== "List") return;

	const doctype = route[1];
	const copy = LIST_EMPTY[doctype] || {
		title: __("Nothing here yet"),
		text: __("Create the first record and this list starts working for you."),
		button: __("Create"),
		doctype,
	};

	$(".no-result, .list-empty-state").each(function () {
		const $box = $(this);
		if ($box.find(".sp-empty-list").length) return;
		if (!$box.text().trim()) return;

		const filtered = /filter/i.test($box.text());
		const current = filtered
			? {
					title: __("Nothing matches these filters"),
					text: __("Clear the filters to see every record, or create a new one."),
					button: __("Clear filters"),
					action: "clear-filters",
				}
			: copy;

		$box.find("svg, img, .icon").first().hide();
		const $card = $(`
			<div class="sp-empty-list">
				<div class="sp-empty-list__art">${ICONS.users}</div>
				<h2 class="sp-empty-list__title">${escape_html(current.title)}</h2>
				<p class="sp-empty-list__text">${escape_html(current.text)}</p>
				<button type="button" class="sp-empty-list__btn">${escape_html(current.button)}</button>
			</div>
		`);
		$card.find(".sp-empty-list__btn").on("click", () => {
			if (current.action === "clear-filters") {
				cur_list?.filter_area?.clear?.();
				return;
			}
			if (copy.doctype) {
				new_doc(copy.doctype);
				return;
			}
			go(copy.route);
		});
		$box.prepend($card);
		$box.children().not(".sp-empty-list").hide();
	});
}

function enhance() {
	document.body.classList.add("staff-pro-alive");
	const route = frappe.get_route?.() || [];
	const $root = page_root();
	if (!$root.length) return;

	if (route[0] === "dashboard-view" || route[0] === "dashboard") {
		$root.find(".sp-dash-celebrations:not(.sp-dash-panel)").remove();
		inject_quick_actions($root);
		inject_celebrations($root);
		$root.find(".sp-dash-start").remove();
		clean_number_cards($root);
		enhance_empty_charts($root);
	}

	if (route[0] === "List") {
		enhance_list_empty();
	}
}

function watch() {
	enhance();
	const root = document.getElementById("body") || document.body;
	if (!root || root._staff_pro_dash_watch) return;
	root._staff_pro_dash_watch = true;

	let timer = null;
	const observer = new MutationObserver(() => {
		clearTimeout(timer);
		timer = setTimeout(enhance, 80);
	});
	observer.observe(root, { childList: true, subtree: true });
}

hrms.ui.refresh_desk_dashboard = enhance;

$(document).on("app_ready", watch);
$(document).on("page-change", () => setTimeout(enhance, 60));

if (typeof frappe !== "undefined" && document.body) {
	watch();
}
