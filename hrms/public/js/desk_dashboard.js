frappe.provide("hrms.ui");

if (typeof window !== "undefined" && typeof window.__ !== "function") {
	window.__ = (text) => text;
}

const ICONS = {
	users: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
	userPlus: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="16" y1="11" x2="22" y2="11"/></svg>`,
	userMinus: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="22" y1="11" x2="16" y2="11"/></svg>`,
	spark: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l1.6 5.2L19 10l-5.4 1.8L12 17l-1.6-5.2L5 10l5.4-1.8L12 3z"/></svg>`,
	calendar: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
	clock: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/></svg>`,
	check: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>`,
	alert: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
	wallet: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="14" rx="2"/><path d="M2 10h20"/><circle cx="16" cy="15" r="1.4"/></svg>`,
	briefcase: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`,
	upload: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 16V4m0 0 4 4m-4-4-4 4"/><path d="M4 20h16"/></svg>`,
	org: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="3" width="6" height="6" rx="1"/><rect x="3" y="15" width="6" height="6" rx="1"/><rect x="15" y="15" width="6" height="6" rx="1"/><path d="M12 9v3m0 0H6v3m6-3h6v3"/></svg>`,
	chart: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19V5"/><path d="M4 19h16"/><rect x="7" y="11" width="3" height="8" rx="1"/><rect x="12" y="7" width="3" height="12" rx="1"/><rect x="17" y="13" width="3" height="6" rx="1"/></svg>`,
	file: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>`,
	arrowUpRight: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M7 17 17 7"/><path d="M8 7h9v9"/></svg>`,
	sortDesc: `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M4.2 2.2c.4 0 .7.3.7.7v7.1l1.3-1.3.9.9-2.4 2.4c-.3.3-.7.3-1 0L1.3 9.6l.9-.9 1.3 1.3V2.9c0-.4.3-.7.7-.7z"/><rect x="8.2" y="2.8" width="6.4" height="1.45" rx=".45"/><rect x="8.2" y="5.7" width="4.9" height="1.45" rx=".45"/><rect x="8.2" y="8.6" width="3.4" height="1.45" rx=".45"/><rect x="8.2" y="11.5" width="1.9" height="1.45" rx=".45"/></svg>`,
	sortAsc: `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M4.2 13.8c-.4 0-.7-.3-.7-.7V6l-1.3 1.3-.9-.9 2.4-2.4c.3-.3.7-.3 1 0l2.4 2.4-.9.9-1.3-1.3v7.1c0 .4-.3.7-.7.7z"/><rect x="8.2" y="2.8" width="6.4" height="1.45" rx=".45"/><rect x="8.2" y="5.7" width="4.9" height="1.45" rx=".45"/><rect x="8.2" y="8.6" width="3.4" height="1.45" rx=".45"/><rect x="8.2" y="11.5" width="1.9" height="1.45" rx=".45"/></svg>`,
};

function empty_face({ bg, skin, hair, path, extra = "" }) {
	return `<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><circle cx="20" cy="20" r="20" fill="${bg}"/><path d="M6.5 40c2.2-11.5 7.2-15.5 13.5-15.5S31.3 28.5 33.5 40" fill="${bg}"/><ellipse cx="20" cy="17.2" rx="7.1" ry="8" fill="${skin}"/><path d="${path}" fill="${hair}"/>${extra}</svg>`;
}

const EMPTY_FACES = [
	{
		slot: "tl",
		svg: empty_face({
			bg: "#e8a598",
			skin: "#e8b896",
			hair: "#2c1a12",
			path: "M10.2 19c.5-9.2 19.1-9.2 19.6 0-.6-6.8-4.6-11.8-9.8-11.8S10.8 12.2 10.2 19z",
		}),
	},
	{
		slot: "tr",
		svg: empty_face({
			bg: "#1f3a5f",
			skin: "#c68642",
			hair: "#1a120c",
			path: "M12 17.8c.2-7.4 15.8-7.4 16 0-.4-5.2-15.6-5.2-16 0z",
		}),
	},
	{
		slot: "l",
		fade: true,
		svg: empty_face({
			bg: "#90ba93",
			skin: "#f1c27d",
			hair: "#4a2c14",
			path: "M11.4 18.4c.4-8 16.8-8 17.2 0-.6-5.6-16.6-5.6-17.2 0z",
			extra: '<circle cx="20" cy="6.4" r="3.1" fill="#4a2c14"/>',
		}),
	},
	{
		slot: "r",
		svg: empty_face({
			bg: "#11a5dd",
			skin: "#ffdbac",
			hair: "#3b2314",
			path: "M12.4 17.2c0-7.2 15.2-7.2 15.2 0C27 12.2 13 12.2 12.4 17.2z",
		}),
	},
	{
		slot: "bl",
		fade: true,
		svg: empty_face({
			bg: "#d9a5b3",
			skin: "#8d5524",
			hair: "#1b0f0a",
			path: "M9.6 20c.2-10.4 20.6-10.4 20.8 0-1.2-8-19.6-8-20.8 0z",
		}),
	},
	{
		slot: "br",
		svg: empty_face({
			bg: "#a7c8cc",
			skin: "#e0ac69",
			hair: "#2a1b10",
			path: "M12.2 17.6c.3-7 15.3-7 15.6 0-.5-4.8-15.1-4.8-15.6 0z",
			extra: '<g fill="none" stroke="#2a2a2a" stroke-width="1.1"><circle cx="16.6" cy="18.2" r="2.3"/><circle cx="23.4" cy="18.2" r="2.3"/><path d="M18.9 18.2h2.2"/></g>',
		}),
	},
	{
		slot: "tc",
		fade: true,
		svg: empty_face({
			bg: "#c4b5a5",
			skin: "#f3d1b3",
			hair: "#5c4033",
			path: "M11.8 18c.5-8.2 15.9-8.2 16.4 0-.6-6-15.8-6-16.4 0z",
		}),
	},
];

function empty_state_art(size = "") {
	const size_class = size ? ` sp-empty-illus--${size}` : "";
	const faces = EMPTY_FACES.map(
		(face) =>
			`<span class="sp-empty-illus__face sp-empty-illus__face--${face.slot}${
				face.fade ? " is-fade" : ""
			}">${face.svg}</span>`
	).join("");
	return `<div class="sp-empty-illus${size_class}" aria-hidden="true"><div class="sp-empty-illus__rings"><i></i><i></i><i></i></div>${faces}<div class="sp-empty-illus__stack"><div class="sp-empty-illus__card"><i></i><span><b></b><b></b></span></div><div class="sp-empty-illus__card is-accent"><i></i><span><b></b><b></b></span></div><div class="sp-empty-illus__card"><i></i><span><b></b><b></b></span></div></div></div>`;
}

function empty_state_card({ title, text, button, size = "" }) {
	const action = button
		? `<button type="button" class="sp-empty-list__btn">${escape_html(button)}</button>`
		: "";
	return `<div class="sp-empty-list${size ? ` sp-empty-list--${size}` : ""}">${empty_state_art(
		size
	)}<h2 class="sp-empty-list__title">${escape_html(title)}</h2><p class="sp-empty-list__text">${escape_html(
		text
	)}</p>${action}</div>`;
}

const DASH_PILL_CSS = `
.sp-dash-pills{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:16px 32px;margin:8px 0 40px;padding:0;width:100%;max-width:100%;overflow:hidden}
.sp-dash-pill{display:inline-flex;align-items:center;gap:8px;max-width:100%;padding:0;border:0;border-radius:0;background:transparent;box-shadow:none;color:#111;font:inherit;font-size:13px;font-weight:500;line-height:1;cursor:pointer}
.sp-dash-pill__icon{display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;width:24px;height:24px;max-width:24px;max-height:24px;overflow:hidden;border-radius:50%;background:#0f1b2d;color:var(--sp-icon-accent,#90ba93)}
.sp-dash-pill__icon svg{width:12px!important;height:12px!important;max-width:12px;max-height:12px;stroke:currentColor;fill:none}
.sp-dash-pill__label{white-space:nowrap}
`;

const LIST_META_CSS = `
.frappe-list .list-row-head > .level-right,
.frappe-list .list-row > .level-right,
.frappe-list .list-row-head .level-right,
.frappe-list .list-row .level-right,
.frappe-list .list-count,
.frappe-list .list-liked-by-me,
.frappe-list .list-row-activity,
.frappe-list .list-row-likes,
.result-list .list-row-head > .level-right,
.result-list .list-row > .level-right,
.result-list .list-count,
.result-list .list-row-activity,
.result-list .list-row-likes,
.page-container[id^="page-List/"] .list-row-head > .level-right,
.page-container[id^="page-List/"] .list-row > .level-right {
	display:none!important;
	width:0!important;
	min-width:0!important;
	max-width:0!important;
	padding:0!important;
	margin:0!important;
	overflow:hidden!important;
	visibility:hidden!important;
	pointer-events:none!important;
	border:0!important;
	flex:0 0 0!important;
}
`;

function inject_dash_css() {
	if (!document.getElementById("staff-pro-dash-css")) {
		const style = document.createElement("style");
		style.id = "staff-pro-dash-css";
		style.textContent = DASH_PILL_CSS;
		document.head.appendChild(style);
	}
	if (!document.getElementById("staff-pro-list-meta-css")) {
		const style = document.createElement("style");
		style.id = "staff-pro-list-meta-css";
		style.textContent = LIST_META_CSS;
		document.head.appendChild(style);
	}
}

function patch_list_view_meta() {
	const proto = window.frappe?.views?.ListView?.prototype;
	if (!proto || proto._staff_pro_hide_list_meta) return;
	proto._staff_pro_hide_list_meta = true;

	proto.get_meta_html = function () {
		return "";
	};

	if (typeof proto.render_count === "function") {
		proto.render_count = function () {};
	}

	if (typeof proto.get_header_html_skeleton === "function") {
		const original = proto.get_header_html_skeleton;
		proto.get_header_html_skeleton = function (left = "", _right = "") {
			return original.call(this, left, "");
		};
	}
}

const HOURS_SORT_COLUMNS = [
	["employee_name", "Full Name"],
	["attendance_date", "Date"],
	["in_time", "In"],
	["out_time", "Out"],
	["working_hours", "Hours"],
	["status", "Status"],
	["shift", "Shift"],
	["daily_pay", "Gross"],
	["week_ss", "SS"],
	["net_daily_pay", "Net"],
];
const HOURS_DEFAULT_SORT = { field: "attendance_date", order: "desc" };

const KPI_ACCENTS = [
	{ accent: "#c47a4a", soft: "#f0e0d4" },
	{ accent: "#3b82c4", soft: "#d6e6f5", ring: true },
	{ accent: "#d4708a", soft: "#f5d6de" },
	{ accent: "#0f766e", soft: "#d7ebe7" },
	{ accent: "#7c6bc4", soft: "#e4dff5" },
];

const kpi_sparkline_cache = {};
let kpi_sparkline_request = null;

const DASHBOARDS = {
	"Human Resource": {
		kicker: __("People"),
		subtitle: __("Add agents, see who's celebrating, and check upcoming payroll."),
		empty_text: __("Use the shortcuts above to add agents or open the roster."),
		create_label: __("Add Employee"),
		create_doctype: "Employee",
		pills: [
			{ label: __("Add Agent"), icon: "userPlus", hue: "#11A5DD", doctype: "Employee" },
			{ label: __("Import Agents"), icon: "upload", hue: "#11A5DD", action: "import-employee" },
			{ label: __("Agents"), icon: "users", hue: "#90BA93", route: ["List", "Employee", "Image"] },
			{ label: __("Who Is In"), icon: "clock", hue: "#11A5DD", route: ["in-out-today"] },
			{ label: __("Team Structure"), icon: "org", hue: "#90BA93", route: ["organizational-chart"] },
			{ label: __("New Hire Onboarding"), icon: "spark", hue: "#11A5DD", route: ["List", "Employee Onboarding"] },
			{ label: __("Offboarding"), icon: "userMinus", hue: "#16678C", route: ["List", "Employee Separation"] },
			{ label: __("Concerns"), icon: "alert", hue: "#205B76", route: ["List", "Employee Grievance"] },
		],
	},
	"Data Analytics": {
		kicker: __("People"),
		subtitle: __("Headcount, hiring, and movement across the company."),
		empty_text: __("Add employees and these cards fill with live hiring, exits, and diversity."),
		create_label: __("Add Employee"),
		create_doctype: "Employee",
		pills: [
			{ label: __("Add Agent"), icon: "userPlus", hue: "#11A5DD", doctype: "Employee" },
			{ label: __("Agents"), icon: "users", hue: "#90BA93", route: ["List", "Employee", "Image"] },
			{ label: __("Headcount Analytics"), icon: "chart", hue: "#11A5DD", route: ["query-report", "Employee Analytics"] },
		],
	},
	Attendance: {
		kicker: __("Time"),
		subtitle: __("Today's hours, who's in, and the rest of the Time tools."),
		empty_text: __("Add an entry or clock in and today's hours show up here."),
		create_label: __("Add Entry"),
		create_doctype: "Attendance",
		pills: [
			{ label: __("Hours"), icon: "clock", hue: "#11A5DD", action: "scroll-hours" },
			{ label: __("Day View"), icon: "calendar", hue: "#11A5DD", route: ["day-view"] },
			{ label: __("Attendance Calendar"), icon: "calendar", hue: "#11A5DD", route: ["List", "Attendance", "Calendar"] },
			{ label: __("Who Is In"), icon: "clock", hue: "#11A5DD", route: ["in-out-today"] },
			{ label: __("Clock In/Out"), icon: "check", hue: "#90BA93", action: "add-entry" },
			{ label: __("Time Off Request"), icon: "file", hue: "#16678C", route: ["List", "Leave Application"] },
			{ label: __("Schedule Correction"), icon: "file", hue: "#16678C", route: ["List", "Attendance Request"] },
			{ label: __("Shift Swap"), icon: "spark", hue: "#90BA93", route: ["List", "Shift Request"] },
			{ label: __("PTO Balance"), icon: "chart", hue: "#11A5DD", route: ["query-report", "Employee Leave Balance"] },
		],
	},
	Payroll: {
		kicker: __("Payroll"),
		subtitle: __("Salary structures, payouts, and incentives at a glance."),
		empty_text: __("Create a salary structure and this page starts showing outflow and coverage."),
		create_label: __("New Salary Structure"),
		create_doctype: "Salary Structure",
		pills: [
			{ label: __("Pay Structure"), icon: "briefcase", hue: "#90BA93", route: ["List", "Salary Structure"] },
			{ label: __("Run Payroll"), icon: "wallet", hue: "#90BA93", route: ["List", "Payroll Entry"] },
			{ label: __("Current Pay Stubs"), icon: "file", hue: "#90BA93", route: ["List", "Salary Slip"] },
			{ label: __("Incentives"), icon: "spark", hue: "#11A5DD", route: ["List", "Employee Incentive"] },
		],
	},
	"SS and Taxes": {
		kicker: __("SS and Taxes"),
		subtitle: __("Social Security contributions by week, team, and agent."),
		empty_text: __("Run payroll and employee and employer SS amounts appear here."),
		create_label: __("Open Social Security"),
		create_doctype: "Salary Slip",
		pills: [
			{ label: __("Social Security"), icon: "file", hue: "#0f766e", route: ["query-report", "Social Security Deductions"] },
			{ label: __("Current Pay Stubs"), icon: "wallet", hue: "#90BA93", route: ["List", "Salary Slip"] },
			{ label: __("SS Contribution Table"), icon: "briefcase", hue: "#11A5DD", route: ["List", "Social Security Contribution Table"] },
			{ label: __("Run Payroll"), icon: "spark", hue: "#16678C", route: ["List", "Payroll Entry"] },
		],
	},
	Recruitment: {
		kicker: __("Talent"),
		subtitle: __("Open roles, pipeline health, and how fast you hire."),
		empty_text: __("Post a job opening and applicants, offers, and time-to-fill appear here."),
		create_label: __("New Job Opening"),
		create_doctype: "Job Opening",
		pills: [
			{ label: __("Open Positions"), icon: "briefcase", hue: "#11A5DD", doctype: "Job Opening" },
			{ label: __("Candidates"), icon: "users", hue: "#11A5DD", route: ["List", "Job Applicant"] },
			{ label: __("Offer Letters"), icon: "spark", hue: "#90BA93", route: ["List", "Job Offer"] },
			{ label: __("Interviews"), icon: "calendar", hue: "#11A5DD", route: ["List", "Interview"] },
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
		text: __("Payroll runs on the schedule set in Payroll Settings. Slips land here after each run."),
		button: __("Open Payroll Entry"),
		route: ["List", "Payroll Entry"],
	},
	"Payroll Entry": {
		title: __("Payroll runs on a schedule"),
		text: __("Entries are created automatically every 10 days, or however often you set in Payroll Settings. You can still add one by hand if you need to."),
		button: __("Open Payroll Settings"),
		route: ["Form", "Payroll Settings"],
	},
};

const DASHBOARD_ALIASES = {
	Workforce: "Human Resource",
	People: "Human Resource",
	Time: "Attendance",
	Pay: "Payroll",
	Talent: "Recruitment",
	"SS and Taxes": "SS and Taxes",
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

function open_hours_add_entry() {
	if (hrms.time?.show_add_entry_dialog) {
		const $panel = $(".sp-dash-hours").first();
		hrms.time.show_add_entry_dialog($panel.length ? hours_listview_stub($panel) : null);
		return;
	}
	hrms.time?.go_attendance_portal?.();
}

function open_inout_clock_entry($widget) {
	if (!hrms.time?.show_add_entry_dialog) {
		hrms.time?.go_attendance_portal?.();
		return;
	}
	const department = inout_department_value($widget);
	const preset = department && department !== inout_none_department() ? department : "";
	hrms.time.show_add_entry_dialog(
		{
			doctype: "Attendance",
			refresh() {
				load_inout($widget);
				const $hours = $(".sp-dash-hours").first();
				if ($hours.length) load_hours($hours);
			},
			filter_area: {
				get() {
					return preset ? [["Attendance", "department", "=", preset]] : [];
				},
			},
			page: { wrapper: $widget, page_form: $widget.find(".sp-dash-panel__filters") },
		},
		{ department: preset },
	);
}

function run_pill(pill) {
	if (pill.action === "import-employee") {
		open_import_employee();
		return;
	}
	if (pill.action === "scroll-hours") {
		const node = document.querySelector(".sp-dash-hours");
		if (node) node.scrollIntoView({ behavior: "smooth", block: "start" });
		return;
	}
	if (pill.action === "add-entry") {
		open_hours_add_entry();
		return;
	}
	if (pill.url) {
		window.location.href = pill.url;
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

function dash_select_html({ className, variant, label, options, value }) {
	const selected = options.find((opt) => opt.value === value) || options[0];
	return `
		<div class="sp-dash-select sp-dash-select--${escape_html(variant)}">
			<select class="${escape_html(className)}" tabindex="-1" aria-hidden="true">
				${options
					.map(
						(opt) =>
							`<option value="${escape_html(opt.value)}"${opt.value === selected.value ? " selected" : ""}>${escape_html(opt.label)}</option>`,
					)
					.join("")}
			</select>
			<button type="button" class="sp-dash-select__btn sp-dash-panel__select sp-dash-panel__select--${escape_html(variant)}" aria-haspopup="listbox" aria-expanded="false" aria-label="${escape_html(label)}">${escape_html(selected.label)}</button>
			<div class="sp-dash-select__menu" hidden role="listbox" aria-label="${escape_html(label)}">
				${options
					.map((opt) => {
						const isSelected = opt.value === selected.value;
						return `<button type="button" class="sp-dash-select__option${isSelected ? " is-selected" : ""}" role="option" data-value="${escape_html(opt.value)}" aria-selected="${isSelected ? "true" : "false"}">${escape_html(opt.label)}</button>`;
					})
					.join("")}
			</div>
		</div>
	`;
}

function close_dash_selects($except) {
	$(".sp-dash-select")
		.not($except || $())
		.each(function () {
			const $wrap = $(this);
			$wrap.removeClass("is-open");
			$wrap.find(".sp-dash-select__menu").prop("hidden", true);
			$wrap.find(".sp-dash-select__btn").attr("aria-expanded", "false");
		});
}

function sync_dash_select_menu($wrap) {
	const $select = $wrap.children("select");
	const $btn = $wrap.children(".sp-dash-select__btn");
	const $menu = $wrap.children(".sp-dash-select__menu");
	const value = String($select.val() ?? "");
	const html = $select
		.find("option")
		.map(function () {
			const optValue = String($(this).attr("value") ?? $(this).val() ?? "");
			const optLabel = $(this).text();
			const selected = optValue === value;
			return `<button type="button" class="sp-dash-select__option${selected ? " is-selected" : ""}" role="option" data-value="${escape_html(optValue)}" aria-selected="${selected ? "true" : "false"}">${escape_html(optLabel)}</button>`;
		})
		.get()
		.join("");
	$menu.html(html);
	const selectedText = $select.find("option:selected").text();
	if (selectedText) $btn.text(selectedText);
}

function set_dash_select_options($select, options, keepValue = true) {
	const current = keepValue ? String($select.val() ?? "") : "";
	const values = options.map((opt) => String(opt.value));
	const selected = values.includes(current) ? current : String(options[0]?.value ?? "");
	$select.html(
		options
			.map(
				(opt) =>
					`<option value="${escape_html(opt.value)}"${String(opt.value) === selected ? " selected" : ""}>${escape_html(opt.label)}</option>`,
			)
			.join(""),
	);
	$select.val(selected);
	const $wrap = $select.closest(".sp-dash-select");
	if ($wrap.length) sync_dash_select_menu($wrap);
	return selected;
}

function bind_dash_selects($root) {
	$root.find(".sp-dash-select").each(function () {
		const $wrap = $(this);
		if ($wrap.data("sp-dash-select-bound")) return;
		$wrap.data("sp-dash-select-bound", true);

		const $select = $wrap.children("select");
		const $btn = $wrap.children(".sp-dash-select__btn");
		const $menu = $wrap.children(".sp-dash-select__menu");

		$btn.on("click", function (event) {
			event.preventDefault();
			event.stopPropagation();
			const willOpen = $menu.prop("hidden");
			close_dash_selects(willOpen ? $wrap : null);
			if (!willOpen) return;
			sync_dash_select_menu($wrap);
			$wrap.addClass("is-open");
			$menu.prop("hidden", false);
			$btn.attr("aria-expanded", "true");
			$menu.find(".sp-dash-select__option.is-selected").trigger("focus");
		});

		$menu.on("click", ".sp-dash-select__option", function (event) {
			event.preventDefault();
			event.stopPropagation();
			const value = String($(this).attr("data-value"));
			$select.val(value).trigger("change");
			$btn.text($(this).text());
			$menu.find(".sp-dash-select__option").removeClass("is-selected").attr("aria-selected", "false");
			$(this).addClass("is-selected").attr("aria-selected", "true");
			close_dash_selects();
			$btn.trigger("focus");
		});

		$select.on("change.sp-dash-select", function () {
			sync_dash_select_menu($wrap);
		});

		$btn.on("keydown", function (event) {
			if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
				event.preventDefault();
				if ($menu.prop("hidden")) $btn.trigger("click");
			} else if (event.key === "Escape") {
				close_dash_selects();
			}
		});

		$menu.on("keydown", ".sp-dash-select__option", function (event) {
			const $options = $menu.find(".sp-dash-select__option");
			const index = $options.index(this);
			if (event.key === "ArrowDown") {
				event.preventDefault();
				$options.eq(Math.min(index + 1, $options.length - 1)).trigger("focus");
			} else if (event.key === "ArrowUp") {
				event.preventDefault();
				$options.eq(Math.max(index - 1, 0)).trigger("focus");
			} else if (event.key === "Escape") {
				event.preventDefault();
				close_dash_selects();
				$btn.trigger("focus");
			} else if (event.key === "Tab") {
				close_dash_selects();
			}
		});
	});

	if (!window.__spDashSelectDocBound) {
		window.__spDashSelectDocBound = true;
		$(document).on("click.sp-dash-select", () => close_dash_selects());
		$(document).on("keydown.sp-dash-select", (event) => {
			if (event.key === "Escape") close_dash_selects();
		});
	}
}

function upgrade_native_selects($root) {
	if (!$root?.length) return;
	$root
		.find("select")
		.not(".sp-dash-select select")
		.each(function () {
			const $select = $(this);
			if ($select.closest(".sp-dash-select, .modal, .modal-dialog, .grid-row, .form-in-grid").length) return;
			if ($select.attr("multiple") != null) return;
			if ($select.attr("size") && Number($select.attr("size")) > 1) return;
			if (!$select.find("option").length) return;

			const width = $select.outerWidth();
			const variant = $select.hasClass("sp-dash-panel__select--solid") ? "solid" : "outline";
			const selectedLabel = $select.find("option:selected").text() || $select.find("option").first().text();
			const label = $select.attr("aria-label") || $select.attr("title") || selectedLabel || __("Filter");

			$select.attr({ tabindex: "-1", "aria-hidden": "true" });
			$select.wrap(`<div class="sp-dash-select sp-dash-select--${escape_html(variant)}"></div>`);
			const $wrap = $select.parent();
			$(`
				<button type="button" class="sp-dash-select__btn sp-dash-panel__select sp-dash-panel__select--${escape_html(variant)}" aria-haspopup="listbox" aria-expanded="false" aria-label="${escape_html(label)}">${escape_html(selectedLabel)}</button>
				<div class="sp-dash-select__menu" hidden role="listbox" aria-label="${escape_html(label)}"></div>
			`).insertAfter($select);
			if (width > 40) {
				$wrap.children(".sp-dash-select__btn").css("min-width", `${Math.round(width)}px`);
			}
			sync_dash_select_menu($wrap);
			bind_dash_selects($wrap.parent());
		});
}

const TEAMS_ICON = "/assets/hrms/images/integrations/teams.svg";
const TEAMS_COLOR = "#5059C9";
const TEAMS_CHANNEL_STORAGE = "staff_pro_teams_channel";

let teamsChannelCache = null;

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

function celebration_first_name(name) {
	return String(name || "")
		.trim()
		.split(/\s+/)[0] || name;
}

function celebration_date_label(row) {
	if (row.event_date && typeof frappe.datetime?.str_to_user === "function") {
		return frappe.datetime.str_to_user(row.event_date);
	}
	return [row.day, row.month].filter(Boolean).join(" ");
}

function celebration_teams_title(row) {
	const name = row.employee_name || __("a teammate");
	if (row.event_type === "anniversary") {
		const years = row.years_completed
			? __("{0} Year Work Anniversary", [row.years_completed])
			: __("Work Anniversary");
		return `${years}, ${name}`;
	}
	return __("Happy Birthday, {0}", [name]);
}

function celebration_teams_message(row) {
	const name = row.employee_name || __("a teammate");
	const first = celebration_first_name(name);
	const when = celebration_date_label(row);
	const lines = [];

	if (row.event_type === "anniversary") {
		const years = row.years_completed
			? __("{0} Year Work Anniversary", [row.years_completed])
			: __("Work Anniversary");
		lines.push(`🏅 ${__("Please join us in celebrating {0}'s {1} on {2}!", [name, years, when])}`);
	} else {
		lines.push(`🎂 ${__("Let's wish {0} a happy birthday on {1}!", [name, when])}`);
	}

	if (row.subtitle) {
		lines.push("");
		lines.push(__("{0} is {1}.", [first, row.subtitle]));
	}

	lines.push("");
	if (row.event_type === "anniversary") {
		lines.push(__("Thank you for being part of the Staff Pro team. 🎉"));
	} else {
		lines.push(__("Drop a note and help us celebrate. 🎉"));
	}

	return lines.join("\n");
}

function read_local_teams_channel() {
	try {
		return JSON.parse(localStorage.getItem(TEAMS_CHANNEL_STORAGE) || "null") || {};
	} catch (error) {
		return {};
	}
}

function write_local_teams_channel(channel) {
	localStorage.setItem(
		TEAMS_CHANNEL_STORAGE,
		JSON.stringify({
			channel_name: channel.channel_name || "",
			webhook_url: channel.webhook_url || "",
		})
	);
}

function load_teams_channel(callback) {
	if (teamsChannelCache) {
		callback(teamsChannelCache);
		return;
	}

	const local = read_local_teams_channel();
	if (local.webhook_url) {
		teamsChannelCache = local;
		callback(local);
		return;
	}

	frappe.call({
		method: "hrms.hr.teams_announce.get_teams_channel",
		callback(r) {
			teamsChannelCache = r.message || {};
			if (teamsChannelCache.webhook_url) {
				write_local_teams_channel(teamsChannelCache);
			}
			callback(teamsChannelCache);
		},
		error() {
			callback(local);
		},
	});
}

function style_teams_dialog_button(dialog) {
	dialog.get_primary_btn().css({
		backgroundColor: TEAMS_COLOR,
		borderColor: TEAMS_COLOR,
		color: "#fff",
	});
}

function open_teams_announce_dialog(row) {
	if (!row) return;

	load_teams_channel((channel) => {
		const dialog = new frappe.ui.Dialog({
			title: __("Announce to Teams"),
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "teams_help",
					options: `<p class="sp-teams-announce__help">${escape_html(
						__(
							"Set the Teams channel once, then send. In Teams: channel ••• → Workflows → “Post to a channel when a webhook request is received”, and paste the URL below."
						)
					)}</p>`,
				},
				{
					label: __("Teams channel"),
					fieldname: "channel_name",
					fieldtype: "Data",
					reqd: 1,
					default: channel.channel_name || "",
					placeholder: __("e.g. General"),
				},
				{
					label: __("Incoming webhook URL"),
					fieldname: "webhook_url",
					fieldtype: "Small Text",
					reqd: 1,
					default: channel.webhook_url || "",
				},
				{
					label: __("Message"),
					fieldname: "message",
					fieldtype: "Text",
					reqd: 1,
					default: celebration_teams_message(row),
				},
				{
					label: __("Remember this channel"),
					fieldname: "save_channel",
					fieldtype: "Check",
					default: 1,
				},
			],
			primary_action_label: __("Announce to Teams"),
			primary_action(values) {
				frappe.call({
					method: "hrms.hr.teams_announce.announce_to_teams",
					freeze: true,
					freeze_message: __("Posting to Teams..."),
					args: {
						message: values.message,
						webhook_url: values.webhook_url,
						channel_name: values.channel_name,
						title: celebration_teams_title(row),
						save_channel: values.save_channel ? 1 : 0,
					},
					callback() {
						const saved = {
							channel_name: values.channel_name,
							webhook_url: values.webhook_url,
						};
						teamsChannelCache = saved;
						if (values.save_channel) {
							write_local_teams_channel(saved);
						}
						dialog.hide();
						const destination = values.channel_name
							? __("Posted to {0}.", [values.channel_name])
							: __("Posted to Teams.");
						frappe.show_alert({ message: destination, indicator: "green" });
					},
				});
			},
		});
		dialog.$wrapper.addClass("sp-teams-announce-dialog");
		dialog.show();
		style_teams_dialog_button(dialog);
	});
}

function bind_celebration_rows($list, rows) {
	$list.find(".sp-celebrations__person").on("click", function () {
		const employee = $(this).closest(".sp-celebrations__row").data("employee");
		if (employee) frappe.set_route("Form", "Employee", employee);
	});

	$list.find(".sp-celebrations__announce").each(function (idx) {
		$(this).data("celebration", rows[idx]);
	});

	$list.find(".sp-celebrations__announce").on("click", function (e) {
		e.preventDefault();
		e.stopPropagation();
		open_teams_announce_dialog($(this).data("celebration"));
	});
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
			<div class="sp-celebrations__row sp-celebrations__row--${escape_html(row.event_type)}" data-employee="${escape_html(row.employee)}">
				<button type="button" class="sp-celebrations__person" aria-label="${escape_html(row.employee_name)}">
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
				<button type="button" class="sp-celebrations__announce" title="${escape_html(__("Announce to Teams"))}" aria-label="${escape_html(__("Announce to Teams"))}">
					<img class="sp-celebrations__announce-icon" src="${escape_html(TEAMS_ICON)}" alt="">
					<span>${escape_html(__("Announce to Teams"))}</span>
				</button>
			</div>
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
			bind_celebration_rows($list, rows);
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

function hr_kpi_widget_group($root) {
	return $root
		.find(".dashboard-graph .widget-group")
		.filter(function () {
			return $(this).find(kpi_card_selector()).length;
		})
		.first();
}

const KPI_HOURS_CARDS = new Set(["Hours Worked (This Week)"]);
const HIDDEN_HR_KPI_CARDS = new Set([
	"Total Outgoing Salary(Last month)",
	"Payroll Payouts (Last Month)",
]);
const HIDDEN_HR_CHARTS = new Set([
	"Shift Assignment Breakup",
	"Shift Coverage",
	"Hiring vs Attrition Count",
	"Hiring vs Attrition",
]);
const PERCENT_LEGEND_CHARTS = new Set(["Floor Attendance"]);

function format_kpi_hours(value) {
	const hours = Number(value || 0);
	if (!hours) return "0h";
	const text = hours.toFixed(1);
	return `${text.endsWith(".0") ? text.slice(0, -2) : text}h`;
}

function apply_kpi_value_format($card) {
	const name = kpi_card_name($card);
	if (!KPI_HOURS_CARDS.has(name)) return;

	const $number = $card.find(".widget-content .number, .widget-body .number").first();
	if (!$number.length) return;

	const value = kpi_parse_number($number.text());
	if (value == null) return;

	const formatted = format_kpi_hours(value);
	if ($number.text().trim() !== formatted) {
		$number.text(formatted);
	}
}

function filter_hr_kpi_cards($root) {
	if (dashboard_name() !== "Human Resource") return;

	$root.find(".sp-dash-kpi-group").find(kpi_card_selector()).each(function () {
		const $card = $(this);
		if (HIDDEN_HR_KPI_CARDS.has(kpi_card_name($card))) {
			$card.remove();
		}
	});
}

function chart_widget_label($widget) {
	const $title = $widget.find(".widget-title").first();
	return (
		$title.find("[title]").attr("title") ||
		$title.attr("title") ||
		$title.text() ||
		""
	)
		.replace(/\s+/g, " ")
		.trim();
}

function filter_hr_charts($root) {
	if (dashboard_name() !== "Human Resource") return;

	$root.find(".dashboard-graph .widget.dashboard-widget-box, .dashboard-graph .chart-widget").each(function () {
		const $widget = $(this).closest(".widget");
		if (HIDDEN_HR_CHARTS.has(chart_widget_label($widget))) {
			$widget.remove();
		}
	});
}

function format_legend_percentages(values) {
	const total = values.reduce((sum, value) => sum + value, 0);
	if (!total) return values.map(() => "0%");

	const raw = values.map((value) => (value / total) * 100);
	const rounded = raw.map((value) => Math.round(value));
	let diff = 100 - rounded.reduce((sum, value) => sum + value, 0);
	const order = raw
		.map((value, index) => ({ index, frac: value - Math.floor(value) }))
		.sort((a, b) => (diff > 0 ? b.frac - a.frac : a.frac - b.frac));
	for (let i = 0; diff !== 0 && i < order.length; i++) {
		rounded[order[i].index] += diff > 0 ? 1 : -1;
		diff += diff > 0 ? -1 : 1;
	}
	return rounded.map((value) => `${Math.max(0, value)}%`);
}

function format_pie_legend_percentages($root) {
	$root.find(".dashboard-graph .widget.dashboard-widget-box, .dashboard-graph .chart-widget").each(function () {
		const $widget = $(this).closest(".widget");
		if (!PERCENT_LEGEND_CHARTS.has(chart_widget_label($widget))) return;

		const $values = $widget.find(".legend-dataset-value");
		if (!$values.length) return;

		const texts = $values
			.map(function () {
				return $(this).text().replace(/\s+/g, " ").trim();
			})
			.get();
		if (!texts.length || texts.some((text) => !text)) return;
		if (texts.every((text) => /%$/.test(text))) return;

		const numbers = texts.map((text) => kpi_parse_number(text) || 0);
		const labels = format_legend_percentages(numbers);
		$values.each(function (index) {
			if (labels[index] != null && $(this).text().trim() !== labels[index]) {
				$(this).text(labels[index]);
			}
		});
	});
}

function reorder_hr_dashboard_layout($root) {
	if (dashboard_name() !== "Human Resource") {
		$root.find(".sp-dash-kpi-group").removeClass("sp-dash-kpi-group");
		return;
	}

	const $kpiGroup = hr_kpi_widget_group($root);
	const $home = $root.find(".sp-dash-home").first();
	if (!$kpiGroup.length || !$home.length) return;

	$kpiGroup.addClass("sp-dash-kpi-group");
	if (!$home.prev().is($kpiGroup)) {
		$home.before($kpiGroup);
	}

	filter_hr_kpi_cards($root);
}

function inject_celebrations($root) {
	if (dashboard_name() !== "Human Resource") {
		$root.find(".sp-dash-home, .sp-dash-split, .sp-dash-celebrations, .sp-dash-payroll, .sp-dash-inout").remove();
		return;
	}

	const $existingHome = $root.find(".sp-dash-home");
	if (
		$existingHome.length &&
		$existingHome.find(".sp-inout-dash__department").length &&
		$existingHome.find(".sp-clock-btn").length &&
		$existingHome.find(".sp-payroll__gross").length &&
		$existingHome.find(".sp-payroll__ss").length
	) {
		return;
	}
	$existingHome.remove();
	$root.find(".sp-dash-split, .sp-dash-inout").remove();

	const $pills = $root.find(".sp-dash-pills").first();
	if (!$pills.length) return;

	const $home = $(`
		<div class="sp-dash-home">
			<section class="sp-dash-split">
				<section class="sp-dash-panel sp-dash-celebrations" aria-label="${escape_html(__("Birthdays & Anniversaries"))}">
					<div class="sp-dash-panel__head">
						<h2 class="sp-dash-panel__title">${escape_html(__("Birthdays & Anniversaries"))}</h2>
						<div class="sp-dash-panel__filters">
							<div class="sp-dash-panel__filter">
								${dash_select_html({
									className: "sp-celebrations__type-filter",
									variant: "solid",
									label: __("Type"),
									value: "all",
									options: [
										{ value: "all", label: CELEBRATION_TYPES.all },
										{ value: "birthday", label: CELEBRATION_TYPES.birthday },
										{ value: "anniversary", label: CELEBRATION_TYPES.anniversary },
									],
								})}
							</div>
							<div class="sp-dash-panel__filter">
								${dash_select_html({
									className: "sp-celebrations__period",
									variant: "outline",
									label: __("Period"),
									value: "weekly",
									options: [
										{ value: "weekly", label: CELEBRATION_PERIODS.weekly },
										{ value: "monthly", label: CELEBRATION_PERIODS.monthly },
										{ value: "yearly", label: CELEBRATION_PERIODS.yearly },
									],
								})}
							</div>
						</div>
					</div>
					<div class="sp-celebrations__list"></div>
				</section>
				<section class="sp-dash-panel sp-dash-payroll" aria-label="${escape_html(__("Upcoming Payroll"))}">
					<div class="sp-dash-panel__head">
						<h2 class="sp-dash-panel__title">${escape_html(__("Upcoming Payroll"))}</h2>
						<div class="sp-dash-panel__filters">
							<div class="sp-dash-panel__filter">
								${dash_select_html({
									className: "sp-payroll__period",
									variant: "outline",
									label: __("Period"),
									value: "monthly",
									options: [
										{ value: "monthly", label: __("Monthly") },
										{ value: "weekly", label: __("Weekly") },
										{ value: "yearly", label: __("Yearly") },
									],
								})}
							</div>
						</div>
					</div>
					<div class="sp-payroll__table-wrap">
						<div class="sp-payroll__table-head">
							<span>${escape_html(__("Agent"))}</span>
							<span>${escape_html(__("Status"))}</span>
							<span>${escape_html(__("Pay Date"))}</span>
							<span>${escape_html(__("Hours"))}</span>
							<span class="sp-payroll__gross">${escape_html(__("Gross Pay"))}</span>
							<span class="sp-payroll__ss">${escape_html(__("SS"))}</span>
							<span>${escape_html(__("Net Pay"))}</span>
						</div>
						<div class="sp-payroll__list"></div>
					</div>
				</section>
			</section>
			<section class="sp-dash-panel sp-dash-inout" aria-label="${escape_html(__("Who Is In"))}">
				<div class="sp-dash-panel__head">
					<h2 class="sp-dash-panel__title">${escape_html(__("Who Is In"))}</h2>
					<div class="sp-dash-panel__filters">
						<div class="sp-dash-panel__filter">
							${dash_select_html({
								className: "sp-inout-dash__department",
								variant: "outline",
								label: __("Department"),
								value: "",
								options: [{ value: "", label: __("All Departments") }],
							})}
						</div>
						<button type="button" class="sp-clock-btn">${escape_html(__("CLOCK"))}</button>
						<div class="sp-dash-panel__filter">
							${hrms.ui.inout_toggle_html({ value: "IN" })}
						</div>
						<button type="button" class="sp-inout-dash__open">${escape_html(__("View all"))}</button>
					</div>
				</div>
				<div class="sp-inout-dash__totals" aria-live="polite"></div>
				<div class="sp-inout-dash__summary"></div>
				<div class="sp-inout-dash__table-wrap">
					<div class="sp-inout-dash__table-head">
						<span>${escape_html(__("Name"))}</span>
						<span>${escape_html(__("In / Out"))}</span>
						<span>${escape_html(__("Time"))}</span>
						<span>${escape_html(__("Job / Pto Code"))}</span>
						<span>${escape_html(__("Device ID"))}</span>
					</div>
					<div class="sp-inout-dash__list"></div>
				</div>
			</section>
		</div>
	`);

	$pills.after($home);
	bind_dash_selects($home);

	const $celebrations = $home.find(".sp-dash-celebrations");
	reload_celebrations($celebrations);
	$celebrations.find(".sp-celebrations__period, .sp-celebrations__type-filter").on("change", function () {
		reload_celebrations($celebrations);
	});

	const $payroll = $home.find(".sp-dash-payroll");
	reload_payroll($payroll);
	$payroll.find(".sp-payroll__period").on("change", function () {
		reload_payroll($payroll);
	});

	const $inout = $home.find(".sp-dash-inout");
	$inout.find(".sp-inout-dash__open").on("click", () => go(["in-out-today"]));
	$inout.find(".sp-clock-btn").on("click", () => open_inout_clock_entry($inout));
	$inout.find(".sp-inout-dash__department").on("change", function () {
		render_inout_panel($inout);
	});
	hrms.ui.bind_inout_toggle($inout.find(".sp-inout-toggle"), () => {
		render_inout_rows($inout);
	});
	load_inout($inout);
}

function format_hours(value) {
	const hours = Number(value || 0);
	if (!hours) return "—";
	return `${hours.toFixed(1)}h`;
}

function format_payroll_money(amount, currency) {
	if (amount == null || amount === "") return "—";
	const currency_code = currency || "";
	if (typeof format_currency === "function") {
		return format_currency(amount, currency_code);
	}
	if (frappe.utils && typeof frappe.utils.fmt_money === "function") {
		return frappe.utils.fmt_money(amount, null, currency_code);
	}
	const value = Number(amount);
	if (Number.isFinite(value)) {
		return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
	}
	return String(amount);
}

function format_pay_amount(row) {
	return format_payroll_money(row.net_pay, row.currency);
}

function format_gross_amount(row) {
	if (row.gross_pay == null || row.gross_pay === "") return "—";
	return format_payroll_money(row.gross_pay, row.currency);
}

function format_ss_amount(row) {
	if (row.ss_contribution == null || row.ss_contribution === "") return "—";
	return format_payroll_money(row.ss_contribution, row.currency);
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
				<span class="sp-payroll__gross">${escape_html(format_gross_amount(row))}</span>
				<span class="sp-payroll__ss">${escape_html(format_ss_amount(row))}</span>
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

function inout_status_label(row) {
	if (row.late) return __("LATE");
	return row.status || __("OUT");
}

function inout_status_class(row) {
	if (row.late) return "is-late";
	if (row.status === "IN") return "is-in";
	return "is-out";
}

function render_inout_empty(message) {
	return `
		<div class="sp-inout-dash__empty">
			<p>${escape_html(message)}</p>
		</div>
	`;
}

function inout_none_department() {
	return "__none__";
}

function matches_inout_department(row, department) {
	if (!department) return true;
	if (department === inout_none_department()) return !row.department;
	return row.department === department;
}

function inout_department_value($widget) {
	return $widget.find(".sp-inout-dash__department").val() || "";
}

function inout_totals_from_rows(rows) {
	return {
		total: rows.length,
		in_count: rows.filter((row) => row.status === "IN").length,
		out_count: rows.filter((row) => row.status === "OUT").length,
		late: rows.filter((row) => row.late).length,
	};
}

function scoped_inout_rows($widget) {
	const department = inout_department_value($widget);
	return ($widget.data("inout-rows") || []).filter((row) => matches_inout_department(row, department));
}

function filtered_inout_rows($widget) {
	const status = hrms.ui.inout_toggle_value($widget.find(".sp-inout-toggle"));
	const rows = scoped_inout_rows($widget);
	return rows.filter((row) => row.status === status);
}

function inout_department_options(payload) {
	const options = [{ value: "", label: __("All Departments") }];
	(payload.departments || []).forEach((name) => options.push({ value: name, label: name }));
	if ((payload.details || []).some((row) => !row.department)) {
		options.push({ value: inout_none_department(), label: __("No Department") });
	}
	return options;
}

function render_inout_totals($widget) {
	const totals = inout_totals_from_rows(scoped_inout_rows($widget));
	$widget.find(".sp-inout-dash__totals").html(`
		<span><strong>${escape_html(__("Total"))}:</strong> ${totals.total}</span>
		<span><strong>${escape_html(__("IN"))}:</strong> ${totals.in_count}</span>
		<span><strong>${escape_html(__("OUT"))}:</strong> ${totals.out_count}</span>
		<span><strong>${escape_html(__("Late"))}:</strong> ${totals.late}</span>
	`);
}

function render_inout_summary($widget) {
	const $summary = $widget.find(".sp-inout-dash__summary");
	const department = inout_department_value($widget);
	const rows = ($widget.data("inout-summary") || []).filter((row) => {
		if (!department) return true;
		if (department === inout_none_department()) return row.department === __("No Department");
		return row.department === department;
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
					<th>${escape_html(__("Department"))}</th>
					<th>${escape_html(__("Employees"))}</th>
					<th>${escape_html(__("IN"))}</th>
					<th>${escape_html(__("OUT"))}</th>
				</tr>
			</thead>
			<tbody>
				${rows
					.map(
						(row) => `
					<tr>
						<td>${escape_html(row.department || __("No Department"))}</td>
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
}

function render_inout_panel($widget) {
	render_inout_totals($widget);
	render_inout_summary($widget);
	render_inout_rows($widget);
}

function render_inout_rows($widget) {
	const $list = $widget.find(".sp-inout-dash__list");
	const rows = filtered_inout_rows($widget);
	if (!rows.length) {
		$list.html(render_inout_empty(__("No agents to show for this filter.")));
		return;
	}

	$list.html(
		rows
			.map(
				(row) => `
			<button type="button" class="sp-inout-dash__row" data-employee="${escape_html(row.employee)}">
				<span class="sp-inout-dash__agent">
					<span class="sp-inout-dash__avatar">${celebration_avatar(row)}</span>
					<span class="sp-inout-dash__agent-meta">
						<span class="sp-inout-dash__name">${escape_html(row.employee_name || row.employee || "")}</span>
						${row.department ? `<span class="sp-inout-dash__dept">${escape_html(row.department)}</span>` : ""}
					</span>
				</span>
				<span class="sp-inout-dash__status-pill ${inout_status_class(row)}">${escape_html(inout_status_label(row))}</span>
				<span class="sp-inout-dash__time">${escape_html(row.time || "—")}</span>
				<span class="sp-inout-dash__pto">${escape_html(row.pto_code || "—")}</span>
				<span class="sp-inout-dash__device">${escape_html(row.device_id || "—")}</span>
			</button>
		`
			)
			.join("")
	);

	$list.find(".sp-inout-dash__row").on("click", function () {
		const employee = $(this).data("employee");
		if (employee) frappe.set_route("Form", "Employee", employee);
	});
}

function load_inout($widget) {
	const $list = $widget.find(".sp-inout-dash__list");
	$list.addClass("is-loading");

	frappe.call({
		method: "hrms.hr.page.in_out_today.in_out_today.get_in_out_today",
		callback(r) {
			$list.removeClass("is-loading");
			const payload = r.message || {};
			$widget.data("inout-rows", payload.details || []);
			$widget.data("inout-summary", payload.summary || []);
			set_dash_select_options($widget.find(".sp-inout-dash__department"), inout_department_options(payload));
			render_inout_panel($widget);
		},
		error() {
			$list.removeClass("is-loading");
			$widget.data("inout-rows", []);
			$widget.data("inout-summary", []);
			render_inout_totals($widget);
			$widget.find(".sp-inout-dash__summary").empty().hide();
			$list.html(render_inout_empty(__("Could not load today's timeclock.")));
		},
	});
}

function hide_attendance_charts($root) {
	if (dashboard_name() !== "Attendance") {
		$root.removeClass("sp-dash--hours");
		return;
	}
	$root.addClass("sp-dash--hours");
}

function hours_filter_state($panel) {
	const controls = $panel.data("hours-controls") || {};
	return {
		from_date: $panel.find(".sp-hours__from").val() || frappe.datetime.get_today(),
		to_date: $panel.find(".sp-hours__to").val() || frappe.datetime.get_today(),
		employee: (controls.employee && controls.employee.get_value()) || "",
		department: (controls.department && controls.department.get_value()) || "",
	};
}

function attach_hours_link($host, options, onchange) {
	if (!frappe.ui?.form?.make_control) {
		$host.html(
			`<input type="text" class="sp-hours__${escape_html(options.fieldname)} sp-dash-panel__select sp-dash-panel__select--outline" placeholder="${escape_html(options.placeholder)}" />`,
		);
		$host.find("input").on("change", onchange);
		return null;
	}
	const control = frappe.ui.form.make_control({
		parent: $host.get(0),
		df: {
			fieldtype: "Link",
			options: options.doctype,
			fieldname: options.fieldname,
			placeholder: options.placeholder,
			only_select: 1,
			get_query: options.get_query,
			change: onchange,
			onchange,
		},
		render_input: true,
	});
	control.refresh();
	control.$input?.addClass("sp-hours__control sp-dash-panel__select sp-dash-panel__select--outline");
	control.$input?.attr("placeholder", options.placeholder);
	control.$input?.on("awesomplete-selectcomplete", onchange);
	return control;
}

function local_hours_presets() {
	const today = frappe.datetime.get_today();
	const m = moment(today);
	const fmt = (value) => value.format("YYYY-MM-DD");
	return {
		today: [today, today],
		this_week: [fmt(m.clone().startOf("week")), fmt(m.clone().endOf("week"))],
		last_week: [fmt(m.clone().subtract(1, "week").startOf("week")), fmt(m.clone().subtract(1, "week").endOf("week"))],
		this_month: [fmt(m.clone().startOf("month")), fmt(m.clone().endOf("month"))],
		current_pay_period: [fmt(m.clone().startOf("week")), fmt(m.clone().endOf("week"))],
		previous_pay_period: [fmt(m.clone().subtract(1, "week").startOf("week")), fmt(m.clone().subtract(1, "week").endOf("week"))],
	};
}

function hours_date_label(value) {
	if (!value) return "";
	const parsed = moment(value);
	return parsed.isValid() ? parsed.format("MM-DD, ddd") : frappe.datetime.str_to_user(value);
}

function hours_sort_value(row, field) {
	switch (field) {
		case "employee_name":
			return String(row.employee_name || row.employee || "").toLowerCase();
		case "attendance_date":
			return row.attendance_date || "";
		case "in_time":
			return row.in_time || "";
		case "out_time":
			return row.out_time || "";
		case "working_hours":
			return row_working_hours(row);
		case "daily_pay":
			return Number(row.daily_pay || 0);
		case "week_ss":
			return Number(row.week_ss || 0);
		case "net_daily_pay":
			return Number(row.net_daily_pay || 0);
		case "status":
			return String(row.status || "").toLowerCase();
		case "shift":
			return String(row.shift || row.leave_type || "").toLowerCase();
		default:
			return "";
	}
}

function compare_hours_sort_values(left, right) {
	const empty_left = left == null || left === "";
	const empty_right = right == null || right === "";
	if (empty_left && empty_right) return 0;
	if (empty_left) return 1;
	if (empty_right) return -1;
	if (typeof left === "number" && typeof right === "number") return left - right;
	return String(left).localeCompare(String(right), undefined, {
		numeric: true,
		sensitivity: "base",
	});
}

function sort_hours_rows(rows, sort) {
	const field = sort?.field;
	if (!field) return rows.slice();
	const dir = sort.order === "asc" ? 1 : -1;
	return rows
		.map((row, index) => ({ row, index }))
		.sort((a, b) => {
			const cmp = compare_hours_sort_values(
				hours_sort_value(a.row, field),
				hours_sort_value(b.row, field),
			);
			if (cmp) return cmp * dir;
			return a.index - b.index;
		})
		.map((item) => item.row);
}

function hours_sort_state($panel) {
	return $panel.data("hours-sort") || { ...HOURS_DEFAULT_SORT };
}

function render_hours_table_head() {
	const buttons = HOURS_SORT_COLUMNS.map(([field, label]) => {
		const active = field === HOURS_DEFAULT_SORT.field;
		return `
			<button type="button" class="sp-hours__sort${active ? " is-active" : ""}" data-sort="${escape_html(field)}" aria-sort="${active ? "descending" : "none"}" title="${escape_html(__("Sort by {0}", [__(label)]))}">
				<span class="sp-hours__sort-label">${escape_html(__(label))}</span>
				<span class="sp-hours__sort-icon" aria-hidden="true">${ICONS.sortDesc}</span>
			</button>`;
	}).join("");
	return `${buttons}<span></span>`;
}

function sync_hours_sort_ui($panel) {
	const sort = hours_sort_state($panel);
	$panel.find(".sp-hours__sort").each(function () {
		const $btn = $(this);
		const field = $btn.data("sort");
		const active = field === sort.field;
		const order = active ? sort.order : "desc";
		$btn.toggleClass("is-active", active);
		$btn.attr("aria-sort", active ? (order === "asc" ? "ascending" : "descending") : "none");
		$btn.find(".sp-hours__sort-icon").html(order === "asc" ? ICONS.sortAsc : ICONS.sortDesc);
	});
}

function paint_hours_list($panel) {
	const $list = $panel.find(".sp-hours__list");
	const rows = sort_hours_rows($panel.data("hours-rows") || [], hours_sort_state($panel));
	$list.html(render_hours_rows(rows, $panel.find(".sp-hours__group-by").is(":checked")));
	bind_hours_row_actions($panel, $list);
	sync_hours_sort_ui($panel);
}

function apply_quick_dates($panel, key) {
	const presets = $panel.data("hours-presets") || local_hours_presets();
	if (key === "custom") return;
	const range = presets[key];
	if (!range) return;
	$panel.find(".sp-hours__from").val(range[0]);
	$panel.find(".sp-hours__to").val(range[1]);
}

function normalize_hours_dates($panel) {
	const $from = $panel.find(".sp-hours__from");
	const $to = $panel.find(".sp-hours__to");
	const from = $from.val();
	const to = $to.val();
	if (from && to && from > to) {
		$to.val(from);
	}
}

function open_hours_date_picker(input) {
	if (!input?.showPicker) return;
	try {
		input.showPicker();
	} catch (error) {
		/* picker already open or not allowed */
	}
}

function hours_listview_stub($panel) {
	return {
		doctype: "Attendance",
		refresh() {
			load_hours($panel);
		},
		filter_area: {
			get() {
				const filters = hours_filter_state($panel);
				const rows = [
					["Attendance", "attendance_date", "Between", [filters.from_date, filters.to_date]],
				];
				if (filters.employee) rows.push(["Attendance", "employee", "=", filters.employee]);
				if (filters.department) rows.push(["Attendance", "department", "=", filters.department]);
				return rows;
			},
		},
		page: { wrapper: $panel, page_form: $panel.find(".sp-hours__toolbar") },
	};
}

function format_hours_clock(value) {
	if (hrms.time?.format_clock) return hrms.time.format_clock(value);
	if (!value) return "";
	return frappe.datetime.str_to_user(value);
}

function format_hours_duration(value) {
	if (hrms.time?.format_hours) return hrms.time.format_hours(value);
	return value == null || value === "" ? "" : String(value);
}

function row_working_hours(row) {
	if (hrms.time?.hours_for_row) return hrms.time.hours_for_row(row);
	return Number(row?.working_hours || 0);
}

function format_hours_money(value) {
	return format_currency(Number(value || 0));
}

function render_hours_totals_text(totals) {
	const parts = [
		__("Total Hours: {0}", [format_hours_duration(totals.total)]),
		__("Paid Hours: {0}", [format_hours_duration(totals.paid)]),
		__("Gross: {0}", [format_hours_money(totals.daily_pay)]),
		__("SS: {0}", [format_hours_money(totals.ss_deduction)]),
		__("Net: {0}", [format_hours_money(totals.net_daily_pay)]),
	];
	if (Number(totals.tax_deduction || 0) > 0) {
		parts.push(__("Tax: {0}", [format_hours_money(totals.tax_deduction)]));
	}
	return parts.join("    ");
}

function format_hours_comment(comment) {
	const when = moment(comment.creation);
	const time = when.isValid() ? when.format("hh:mm A") : "";
	const date = when.isValid() ? when.format("MM/DD/YYYY") : "";
	const who = comment.comment_by || __("Admin");
	return __("Comment ({0}, {1}, {2}): {3}", [who, time, date, comment.content || ""]);
}

function render_hours_comments(comments) {
	if (!comments || !comments.length) return "";
	return comments
		.map(
			(comment) =>
				`<div class="sp-hours__comment">${escape_html(format_hours_comment(comment))}</div>`,
		)
		.join("");
}

function render_hours_row(row) {
	const kind = row.kind || "attendance";
	const is_lunch = kind === "lunch";
	const actions = is_lunch
		? ""
		: `<span class="sp-hours__row-actions">
					<button type="button" class="sp-hours__link" data-act="edit">${escape_html(__("edit"))}</button>
					<button type="button" class="sp-hours__link" data-act="del">${escape_html(__("del"))}</button>
				</span>`;
	return `
		<div class="sp-hours__row" data-name="${escape_html(row.name || "")}" data-kind="${escape_html(
			kind,
		)}" data-in-log="${escape_html(row.in_log || "")}" data-out-log="${escape_html(row.out_log || "")}">
			<div class="sp-hours__row-main">
				<span>${escape_html(row.employee_name || row.employee || "")}</span>
				<span>${escape_html(hours_date_label(row.attendance_date))}</span>
				<span>${escape_html(format_hours_clock(row.in_time))}</span>
				<span>${escape_html(format_hours_clock(row.out_time))}</span>
				<span>${escape_html(format_hours_duration(row_working_hours(row)))}</span>
				<span>${escape_html(__(row.status || ""))}</span>
				<span>${escape_html(row.shift || row.leave_type || row.job || "")}</span>
				<span>${escape_html(format_hours_money(row.daily_pay))}</span>
				<span class="sp-hours__ss"></span>
				<span class="sp-hours__net">${escape_html(format_hours_money(row.net_daily_pay))}</span>
				${actions || "<span class=\"sp-hours__row-actions\"></span>"}
			</div>
			${render_hours_comments(row.comments)}
		</div>`;
}

function hours_week_label(start, end) {
	const from = start ? moment(start) : null;
	const to = end ? moment(end) : null;
	if (from?.isValid() && to?.isValid()) {
		return __("Week of {0} – {1}", [from.format("MM-DD"), to.format("MM-DD")]);
	}
	return __("Week");
}

function group_hours_by_week(rows) {
	const weeks = [];
	const index = {};
	rows.forEach((row) => {
		const key = row.week_start || row.attendance_date || "";
		if (!index[key]) {
			index[key] = {
				start: row.week_start || key,
				end: row.week_end || key,
				rows: [],
				hours: 0,
				pay: 0,
				ss: 0,
				tax: 0,
				net: 0,
				seen_employees: {},
			};
			weeks.push(index[key]);
		}
		const week = index[key];
		week.rows.push(row);
		week.hours += row_working_hours(row);
		week.pay += Number(row.daily_pay || 0);
		const employee = row.employee || "";
		if (employee && !week.seen_employees[employee]) {
			week.seen_employees[employee] = true;
			week.ss += Number(row.week_ss || 0);
			week.tax += Number(row.week_tax || 0);
		}
		if (row.week_end) week.end = row.week_end;
	});
	weeks.forEach((week) => {
		week.net = week.pay - week.ss - week.tax;
	});
	return weeks;
}

function render_hours_date_groups(rows) {
	const groups = [];
	const index = {};
	rows.forEach((row) => {
		const key = row.attendance_date || "";
		if (!index[key]) {
			index[key] = { date: key, rows: [], hours: 0 };
			groups.push(index[key]);
		}
		index[key].rows.push(row);
		index[key].hours += row_working_hours(row);
	});
	return groups
		.map((group) => {
			const label = hours_date_label(group.date) || __("No date");
			return `
			<div class="sp-hours__date-group">
				<div class="sp-hours__date-head">
					<span>${escape_html(label)}</span>
					<span>${escape_html(format_hours_duration(group.hours))}</span>
				</div>
				${group.rows.map(render_hours_row).join("")}
			</div>`;
		})
		.join("");
}

function render_hours_week_group(week, group_by_date) {
	const inner = group_by_date
		? render_hours_date_groups(week.rows)
		: week.rows.map(render_hours_row).join("");
	return `
		<div class="sp-hours__week">
			<div class="sp-hours__group-head">
				<span class="sp-hours__group-label">${escape_html(hours_week_label(week.start, week.end))}</span>
				<span>${escape_html(format_hours_duration(week.hours))}</span>
				<span></span>
				<span></span>
				<span>${escape_html(format_hours_money(week.pay))}</span>
				<span class="sp-hours__ss">${escape_html(format_hours_money(week.ss))}</span>
				<span class="sp-hours__net">${escape_html(format_hours_money(week.net))}</span>
				<span></span>
			</div>
			${inner}
		</div>`;
}

function render_hours_rows(rows, group_by_date) {
	if (!rows.length) {
		return `<div class="sp-hours__empty"><p>${escape_html(__("No hours for this date range."))}</p></div>`;
	}
	return group_hours_by_week(rows)
		.map((week) => render_hours_week_group(week, group_by_date))
		.join("");
}

function bind_hours_row_actions($panel, $list) {
	$list.find(".sp-hours__link").on("click", function () {
		const $row = $(this).closest(".sp-hours__row");
		const name = $row.attr("data-name");
		const in_log = $row.attr("data-in-log") || null;
		const out_log = $row.attr("data-out-log") || null;
		const kind = $row.attr("data-kind");
		const act = $(this).data("act");
		if (kind === "lunch") {
			return;
		}
		if (act === "edit") {
			if (hrms.time?.show_edit_entry_dialog) {
				hrms.time.show_edit_entry_dialog(hours_listview_stub($panel), name, {
					in_log,
					out_log,
				});
			}
			return;
		}
		frappe.confirm(__("Remove this hours entry?"), () => {
			frappe.call({
				method: "hrms.hr.doctype.attendance.attendance.cancel_hours_entry",
				args: { name, in_log, out_log },
				callback() {
					load_hours($panel);
				},
			});
		});
	});
}

function update_hours_title($panel) {
	const controls = $panel.data("hours-controls") || {};
	const employee = controls.employee?.get_value?.();
	const label = employee
		? controls.employee.$input?.val() || employee
		: __("All Agents");
	$panel.find(".sp-dash-panel__title").text(label);
}

function load_hours($panel) {
	const filters = hours_filter_state($panel);
	const $list = $panel.find(".sp-hours__list");
	$list.addClass("is-loading");
	update_hours_title($panel);

	frappe.call({
		method: "hrms.hr.doctype.attendance.attendance.get_hours_rows",
		args: filters,
		callback(r) {
			$list.removeClass("is-loading");
			const rows = r.message?.rows || [];
			const totals = r.message?.totals || {};
			$panel.find(".sp-hours__totals").text(render_hours_totals_text(totals));
			$panel.data("hours-rows", rows);
			paint_hours_list($panel);
		},
		error() {
			$list.removeClass("is-loading");
			$panel.data("hours-rows", []);
			$list.html(`<div class="sp-hours__empty"><p>${escape_html(__("Could not load hours."))}</p></div>`);
		},
	});
}

function inject_hours_board($root) {
	if (dashboard_name() !== "Attendance") {
		$root.removeClass("sp-dash--hours");
		$root.find(".sp-dash-hours").remove();
		return;
	}

	hide_attendance_charts($root);

	const $kpiGroup = $root.find(".dashboard-graph .widget-group").filter(function () {
		return $(this).find(".number-widget-box").length;
	}).first();
	const $existing = $root.find(".sp-dash-hours");
	if ($existing.length && $existing.data("sp-hours-select-v7")) {
		if ($kpiGroup.length && !$kpiGroup.next().is(".sp-dash-hours")) {
			$kpiGroup.after($existing);
		}
		return;
	}
	$existing.remove();

	const today = frappe.datetime.get_today();
	const $panel = $(`
		<section class="sp-dash-panel sp-dash-hours" aria-label="${escape_html(__("Hours"))}">
			<div class="sp-dash-panel__head">
				<h2 class="sp-dash-panel__title">${escape_html(__("All Agents"))}</h2>
				<div class="sp-hours__totals text-muted" aria-live="polite"></div>
			</div>
			<div class="sp-hours__toolbar">
				<button type="button" class="sp-hours__calendar" aria-label="${escape_html(__("Custom dates"))}">${ICONS.calendar}</button>
				<div class="sp-hours__quick-wrap">
					<button type="button" class="sp-hours__quick-btn sp-dash-panel__select sp-dash-panel__select--outline" aria-haspopup="listbox" aria-expanded="false">${escape_html(__("Quick Dates"))}</button>
					<div class="sp-hours__quick-menu" hidden>
						<button type="button" data-range="today">${escape_html(__("Today"))}</button>
						<button type="button" data-range="this_week">${escape_html(__("This Week"))}</button>
						<button type="button" data-range="last_week">${escape_html(__("Last Week"))}</button>
						<button type="button" data-range="this_month">${escape_html(__("This Month"))}</button>
						<hr />
						<button type="button" data-range="previous_pay_period">${escape_html(__("Previous Pay Period"))}</button>
						<button type="button" data-range="current_pay_period">${escape_html(__("Current Pay Period"))}</button>
						<button type="button" data-range="custom">${escape_html(__("Custom"))}</button>
					</div>
				</div>
				<div class="sp-hours__custom-dates">
					<label class="sp-dash-panel__filter">
						<span class="sr-only">${escape_html(__("From"))}</span>
						<input type="date" class="sp-hours__from" value="${escape_html(today)}" />
					</label>
					<label class="sp-dash-panel__filter">
						<span class="sr-only">${escape_html(__("To"))}</span>
						<input type="date" class="sp-hours__to" value="${escape_html(today)}" />
					</label>
				</div>
				<div class="sp-hours__field" data-field="employee"></div>
				<div class="sp-hours__field" data-field="department"></div>
				<label class="sp-hours__group">
					<input type="checkbox" class="sp-hours__group-by" />
					<span>${escape_html(__("Group by Date"))}</span>
				</label>
			</div>
			<div class="sp-hours__table-bar">
				<button type="button" class="sp-hours__btn-green sp-hours__add-absence">${escape_html(__("Add Absence"))}</button>
				<button type="button" class="sp-hours__btn-green sp-hours__add-entry">${escape_html(__("Add Entry"))}</button>
				<button type="button" class="sp-hours__btn-green sp-hours__add-adjustment">${escape_html(__("Add Adjustment"))}</button>
			</div>
			<div class="sp-hours__table-wrap">
				<div class="sp-hours__table-head">
					${render_hours_table_head()}
				</div>
				<div class="sp-hours__list"></div>
			</div>
		</section>
	`);

	const $graph = $root.find(".dashboard-graph").first();
	if ($kpiGroup.length) {
		$kpiGroup.after($panel);
	} else if ($graph.length) {
		$graph.after($panel);
	} else {
		$root.find(".sp-dash-pills").first().after($panel);
	}

	$panel.data("hours-presets", local_hours_presets());
	$panel.data("hours-range", "today");
	$panel.data("hours-sort", { ...HOURS_DEFAULT_SORT });
	$panel.data("sp-hours-select-v7", true);

	const reload = () => load_hours($panel);
	const controls = {
		employee: attach_hours_link(
			$panel.find('.sp-hours__field[data-field="employee"]'),
			{
				doctype: "Employee",
				fieldname: "employee",
				placeholder: __("All Agents"),
				get_query() {
					const department = controls.department?.get_value?.();
					const filters = { status: "Active" };
					if (department) filters.department = department;
					return { filters };
				},
			},
			reload,
		),
		department: attach_hours_link(
			$panel.find('.sp-hours__field[data-field="department"]'),
			{ doctype: "Department", fieldname: "department", placeholder: __("All Departments") },
			() => {
				if (controls.employee?.get_value?.()) {
					const employees = $panel.data("hours-employees") || [];
					const department = controls.department?.get_value?.();
					const current = controls.employee.get_value();
					const match = employees.find((row) => row.name === current);
					if (department && match && match.department !== department) {
						controls.employee.set_value("");
					}
				}
				reload();
			},
		),
	};
	$panel.data("hours-controls", controls);
	const close_hours_quick = () => {
		$panel.find(".sp-hours__quick-menu").prop("hidden", true);
		$panel.find(".sp-hours__quick-btn").attr("aria-expanded", "false");
		$panel.find(".sp-hours__quick-wrap").removeClass("is-open");
	};
	const mark_hours_range = (key) => {
		$panel.find(".sp-hours__quick-menu [data-range]").removeClass("is-selected");
		$panel.find(`.sp-hours__quick-menu [data-range="${key}"]`).addClass("is-selected");
	};
	const set_range = (key) => {
		$panel.data("hours-range", key);
		mark_hours_range(key);
		close_hours_quick();
		apply_quick_dates($panel, key);
		if (key !== "custom") reload();
	};
	$panel.find(".sp-hours__quick-btn").on("click", function (event) {
		event.stopPropagation();
		const $menu = $panel.find(".sp-hours__quick-menu");
		const $wrap = $panel.find(".sp-hours__quick-wrap");
		const willOpen = $menu.prop("hidden");
		close_hours_quick();
		if (!willOpen) return;
		mark_hours_range($panel.data("hours-range") || "today");
		$menu.prop("hidden", false);
		$(this).attr("aria-expanded", "true");
		$wrap.addClass("is-open");
	});
	$panel.find(".sp-hours__quick-menu [data-range]").on("click", function (event) {
		event.stopPropagation();
		set_range($(this).data("range"));
	});
	$(document).off("click.sp-hours-quick").on("click.sp-hours-quick", close_hours_quick);
	$panel.find(".sp-hours__calendar").on("click", () => {
		const from = $panel.find(".sp-hours__from").get(0);
		set_range("custom");
		from?.focus();
		open_hours_date_picker(from);
	});
	$panel.find(".sp-hours__from, .sp-hours__to").on("change", () => {
		$panel.data("hours-range", "custom");
		normalize_hours_dates($panel);
		reload();
	});
	$panel.find(".sp-hours__group-by").on("change", () => paint_hours_list($panel));
	$panel.on("click", ".sp-hours__sort", function () {
		const field = $(this).data("sort");
		if (!field) return;
		const current = hours_sort_state($panel);
		const order = current.field === field && current.order === "desc" ? "asc" : "desc";
		$panel.data("hours-sort", { field, order });
		paint_hours_list($panel);
	});
	$panel.find(".sp-hours__add-entry").on("click", () => open_hours_add_entry());
	$panel.find(".sp-hours__add-absence").on("click", () => {
		if (hrms.time?.show_add_absence_dialog) {
			hrms.time.show_add_absence_dialog(hours_listview_stub($panel));
		} else {
			frappe.new_doc("Leave Application");
		}
	});
	$panel.find(".sp-hours__add-adjustment").on("click", () => {
		if (hrms.time?.show_add_adjustment_dialog) {
			hrms.time.show_add_adjustment_dialog(hours_listview_stub($panel));
		}
	});

	frappe.call({
		method: "hrms.hr.doctype.attendance.attendance.get_hours_date_presets",
		callback(r) {
			if (r.message) $panel.data("hours-presets", Object.assign(local_hours_presets(), r.message));
			apply_quick_dates($panel, $panel.data("hours-range") || "today");
			reload();
		},
		error() {
			apply_quick_dates($panel, "today");
			reload();
		},
	});
	frappe.call({
		method: "hrms.hr.doctype.attendance.attendance.get_hours_filter_options",
		callback(r) {
			$panel.data("hours-employees", r.message?.employees || []);
		},
	});
}

function inject_quick_actions($root) {
	$root.find(".sp-dash-hero").remove();
	$root.removeClass("staff-pro-has-hero");

	const cfg = dashboard_config();
	const name = dashboard_name();
	const $existing = $root.find(".sp-dash-pills").first();
	if ($existing.length && $existing.attr("data-dashboard") === name) {
		return;
	}
	$existing.remove();

	if (!$root.length) return;
	let $host = $root.find(".dashboard-view").first();
	if (!$host.length) $host = $root.find(".dashboard").first();
	if (!$host.length) $host = $root.find(".layout-main-section").first();
	if (!$host.length) $host = $root;

	const $pills = $(
		`<nav class="sp-dash-pills sp-dash-pills--v4" data-dashboard="${escape_html(name)}" aria-label="${escape_html(__("Quick actions"))}"></nav>`,
	);
	cfg.pills.forEach((pill) => {
		const $btn = $(`
			<button type="button" class="sp-dash-pill">
				<span class="sp-dash-pill__icon" style="--sp-icon-accent:${pill.hue || "#90BA93"}">${ICONS[pill.icon] || ICONS.spark}</span>
				<span class="sp-dash-pill__label">${escape_html(pill.label)}</span>
			</button>
		`);
		$btn.on("click", () => run_pill(pill));
		$pills.append($btn);
	});

	$host.prepend($pills);
}

function kpi_card_selector() {
	return ".number-widget-box, .number-card-container .widget, .number-widget-area .widget, .widget.number-widget-box";
}

function kpi_card_name($card) {
	return (
		$card.attr("data-widget-name") ||
		$card.attr("data-number-card-name") ||
		$card.data("widget-name") ||
		$card.find(".widget-title").first().text().trim() ||
		""
	);
}

function kpi_open_card($card) {
	const $clickable = $card.find("a, .widget-head, .number").first();
	if ($clickable.length) {
		$clickable.trigger("click");
		return;
	}
	$card.trigger("click");
}

function kpi_parse_number(text) {
	if (text == null) return null;
	const raw = String(text).replace(/,/g, "").trim();
	if (!raw) return null;
	const match = raw.match(/-?\d+(\.\d+)?/);
	if (!match) return null;
	let value = parseFloat(match[0]);
	if (/[kK]\b/.test(raw)) value *= 1000;
	if (/[mM]\b/.test(raw)) value *= 1000000;
	return Number.isFinite(value) ? value : null;
}

function kpi_parse_percent_text(text) {
	const raw = String(text || "");
	const match = raw.match(/(-?\d+(\.\d+)?)\s*%/);
	if (!match) return null;
	const value = parseFloat(match[1]);
	if (/↓|red-stat|decrease|−|–/.test(raw) && value > 0) return -value;
	if (/↑|green-stat|increase|\+/.test(raw)) return Math.abs(value);
	return value;
}

function kpi_synthesize_series($card) {
	const current = kpi_parse_number($card.find(".number").first().text()) || 0;
	const stats = $card.find(".card-stats, .percentage-stat-area").first().text();
	const pct = kpi_parse_percent_text(stats);
	const prev = pct == null || pct <= -100 ? Math.max(current * 0.72, 0) : current / (1 + pct / 100);
	const points = 6;
	const values = [];
	for (let i = 0; i < points; i++) {
		const t = i / (points - 1);
		const wobble = Math.sin(i * 1.7) * Math.abs(current - prev) * 0.08;
		values.push(Math.max(0, prev + (current - prev) * t + wobble));
	}
	values[values.length - 1] = current;
	return values;
}

function kpi_bar_svg(values, accent) {
	const width = 28;
	const height = 22;
	const pad = 2;
	const n = Math.max(values.length, 1);
	const gap = 1.5;
	const bar_w = Math.max(2.5, (width - pad * 2 - gap * (n - 1)) / n);
	const peak = Math.max(...values.map((v) => Math.abs(v)), 0.0001);
	const bars = values
		.map((value, index) => {
			const ratio = Math.max(0.12, Math.abs(value) / peak);
			const h = Math.max(2, (height - pad * 2) * ratio);
			const x = pad + index * (bar_w + gap);
			const y = height - pad - h;
			const fill = index === values.length - 1 ? accent.accent : accent.soft;
			return `<rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${bar_w.toFixed(2)}" height="${h.toFixed(
				2,
			)}" rx="1.2" fill="${fill}"></rect>`;
		})
		.join("");
	return `<svg class="sp-kpi__chart" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" aria-hidden="true">${bars}</svg>`;
}

function kpi_ring_svg(values, accent) {
	const peak = Math.max(...values.map((v) => Math.abs(v)), 0.0001);
	const latest = Math.abs(values[values.length - 1] || 0);
	const ratio = Math.max(0.04, Math.min(0.96, latest / peak));
	const r = 8;
	const c = 2 * Math.PI * r;
	const dash = (ratio * c).toFixed(2);
	const gap = (c - ratio * c).toFixed(2);
	return `
		<svg class="sp-kpi__chart" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
			<circle cx="12" cy="12" r="${r}" fill="none" stroke="${accent.soft}" stroke-width="3"></circle>
			<circle cx="12" cy="12" r="${r}" fill="none" stroke="${accent.accent}" stroke-width="3"
				stroke-linecap="round" stroke-dasharray="${dash} ${gap}" transform="rotate(-90 12 12)"></circle>
		</svg>
	`;
}

function kpi_viz_html(accent, series) {
	const values = Array.isArray(series?.values) ? series.values : [];
	const kind = series?.kind || (accent.ring ? "ring" : "bars");
	if (!values.length) {
		return `<span class="sp-kpi__viz is-loading" aria-hidden="true"></span>`;
	}
	if (kind === "ring" || accent.ring) {
		return `<span class="sp-kpi__viz sp-kpi__viz--ring" aria-hidden="true">${kpi_ring_svg(values, accent)}</span>`;
	}
	return `<span class="sp-kpi__viz" aria-hidden="true">${kpi_bar_svg(values, accent)}</span>`;
}

function request_kpi_sparklines(names) {
	const missing = names.filter((name) => name && kpi_sparkline_cache[name] === undefined);
	if (!missing.length) {
		return Promise.resolve(kpi_sparkline_cache);
	}

	if (kpi_sparkline_request) {
		return kpi_sparkline_request.then(() => request_kpi_sparklines(names));
	}

	missing.forEach((name) => {
		kpi_sparkline_cache[name] = null;
	});

	kpi_sparkline_request = frappe
		.xcall("hrms.hr.desk_dashboard.get_number_card_sparklines", {
			card_names: missing,
			points: 6,
		})
		.then((res) => {
			Object.entries(res || {}).forEach(([name, payload]) => {
				kpi_sparkline_cache[name] = payload || { values: [], kind: "bars" };
			});
			missing.forEach((name) => {
				if (!kpi_sparkline_cache[name]) {
					kpi_sparkline_cache[name] = { values: [], kind: "bars" };
				}
			});
			return kpi_sparkline_cache;
		})
		.catch(() => {
			missing.forEach((name) => {
				kpi_sparkline_cache[name] = { values: [], kind: "bars" };
			});
			return kpi_sparkline_cache;
		})
		.finally(() => {
			kpi_sparkline_request = null;
		});

	return kpi_sparkline_request;
}

function series_for_card($card, name) {
	const cached = name ? kpi_sparkline_cache[name] : null;
	if (cached && Array.isArray(cached.values) && cached.values.length) {
		return cached;
	}
	return { values: kpi_synthesize_series($card), kind: "bars" };
}

function render_kpi_viz($card) {
	const accent = $card.data("sp-kpi-accent") || KPI_ACCENTS[0];
	const name = kpi_card_name($card);
	const $label = $card.find(".widget-label").first();
	if (!$label.length) return;

	const series = series_for_card($card, name);
	const html = kpi_viz_html(accent, series);
	const $existing = $label.children(".sp-kpi__viz");
	if ($existing.length) {
		$existing.replaceWith(html);
	} else {
		$label.prepend(html);
	}
}

function kpi_trend_class(text) {
	const raw = String(text || "").toLowerCase();
	if (/\bgreen-stat\b|↑|\bincrease|\+\s*\d/.test(raw)) return "is-up";
	if (/\bred-stat\b|↓|\bdecrease|−|–/.test(raw)) return "is-down";
	return "";
}

function sync_kpi_footer($card) {
	let $footer = $card.children(".sp-kpi__footer");
	if (!$footer.length) {
		$footer = $(`
			<div class="sp-kpi__footer">
				<button type="button" class="sp-kpi__more">${escape_html(__("View more"))}</button>
				<div class="sp-kpi__trend"></div>
			</div>
		`);
		$footer.find(".sp-kpi__more").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			kpi_open_card($card);
		});
		$card.append($footer);
	}

	const $trend = $footer.find(".sp-kpi__trend");
	const $source = $card
		.find(
			".widget-content .card-stats, .widget-content .percentage-stat-area, .widget-body > .card-stats, .widget-body > .percentage-stat-area",
		)
		.first();
	let text = "";
	if ($source.length) {
		text = $source.text().replace(/\s+/g, " ").trim();
	}
	$trend.text(text || "");
	$trend.removeClass("is-up is-down");
	const class_hint = [$source.attr("class"), $source.find(".green-stat, .red-stat, .grey-stat").attr("class")]
		.filter(Boolean)
		.join(" ");
	const tone = kpi_trend_class(`${class_hint} ${text}`);
	if (tone) $trend.addClass(tone);
	$trend.toggle(Boolean(text));
}

function ensure_kpi_chrome($card, index) {
	const accent = KPI_ACCENTS[index % KPI_ACCENTS.length];
	$card.data("sp-kpi-accent", accent);
	$card
		.addClass("sp-kpi")
		.toggleClass("sp-kpi--dark", index % 3 === 0)
		.css({
			"--sp-kpi-accent": accent.accent,
			"--sp-kpi-accent-soft": accent.soft,
		});

	if (!$card.children(".sp-kpi__arrow").length) {
		const $arrow = $(
			`<button type="button" class="sp-kpi__arrow" aria-label="${escape_html(__("Open"))}">${ICONS.arrowUpRight}</button>`,
		);
		$arrow.on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			kpi_open_card($card);
		});
		$card.prepend($arrow);
	}

	render_kpi_viz($card);
	sync_kpi_footer($card);
	apply_kpi_value_format($card);
}

function theme_number_cards($root) {
	const $cards = $root.find(kpi_card_selector()).filter(function () {
		return !$(this).closest(".chart-widget, .dashboard-widget-box").length;
	});

	const names = [];
	$cards.each(function (index) {
		const $card = $(this);
		const name = kpi_card_name($card);
		if (name) names.push(name);
		if ($card.data("sp-themed")) {
			sync_kpi_footer($card);
			apply_kpi_value_format($card);
			return;
		}
		$card.data("sp-themed", 1);
		ensure_kpi_chrome($card, index);
	});

	const unique = [...new Set(names)];
	if (!unique.length) return;

	request_kpi_sparklines(unique).then(() => {
		$cards.each(function () {
			const $card = $(this);
			const name = kpi_card_name($card);
			const payload = name ? kpi_sparkline_cache[name] : null;
			if (!payload || !payload.values || !payload.values.length) return;
			const fingerprint = `${payload.kind}:${payload.values.join(",")}`;
			if ($card.data("sp-spark") === fingerprint) return;
			$card.data("sp-spark", fingerprint);
			render_kpi_viz($card);
			apply_kpi_value_format($card);
		});
	});

	if (dashboard_name() === "Human Resource") {
		filter_hr_kpi_cards($root);
	}
}

function clean_number_cards($root) {
	$root.find(".sp-kpi__arrow, .sp-kpi__viz, .sp-kpi__footer").remove();
	$root.find(kpi_card_selector()).each(function () {
		$(this)
			.removeData("sp-themed")
			.removeData("sp-kpi-accent")
			.removeClass("sp-kpi sp-kpi--dark")
			.css({ "--sp-kpi-accent": "", "--sp-kpi-accent-soft": "" });
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
				${empty_state_card({
					title: __("Nothing to plot yet"),
					text: cfg.empty_text,
					button: cfg.create_label,
					size: "embed",
				})}
			</div>
		`);
		$body.find(".sp-empty-list__btn").on("click", () => start_action(cfg));
	});
}

function enhance_page_empty() {
	const route = frappe.get_route?.() || [];
	const doctype = route[0] === "List" ? route[1] : "";
	const copy = LIST_EMPTY[doctype] || {
		title: __("Nothing here yet"),
		text: __("Create the first record and this list starts working for you."),
		button: __("Create"),
		doctype,
	};

	const selector = [
		".no-result",
		".list-empty-state",
		".empty-state",
		".empty-apps-state",
		".kanban-empty-state",
		"#hierarchy-empty-root",
	].join(", ");

	$(selector).each(function () {
		const $box = $(this);
		if ($box.closest(".sp-empty-chart, .sp-empty-list").length) return;
		if ($box.find(".sp-empty-list").length) return;
		if ($box.siblings(".sp-empty-list").length) return;
		if ($box.hasClass("sp-empty-list")) return;
		if (!$box.text().trim()) return;
		if ($box.closest(".modal, .grid-empty, .form-grid").length) return;

		const filtered = /filter/i.test($box.text());
		const current = filtered
			? {
					title: __("Nothing matches these filters"),
					text: __("Clear the filters to see every record, or create a new one."),
					button: __("Clear filters"),
					action: "clear-filters",
				}
			: copy;

		const $card = $(
			empty_state_card({
				title: current.title,
				text: current.text,
				button: current.button,
			})
		);
		$card.find(".sp-empty-list__btn").on("click", () => {
			if (current.action === "clear-filters") {
				cur_list?.filter_area?.clear?.();
				return;
			}
			if (copy.doctype) {
				new_doc(copy.doctype);
				return;
			}
			if (copy.route) {
				go(copy.route);
			}
		});
		$box.prepend($card);
		$box.children().not(".sp-empty-list").hide();
	});
}

const BPO_DASHBOARD_MENU = new Set([
	"Human Resource",
	"Data Analytics",
	"SS and Taxes",
	"Attendance",
	"Payroll",
	"Recruitment",
]);

const BPO_DASHBOARD_ORDER = [
	"Human Resource",
	"Attendance",
	"Payroll",
	"SS and Taxes",
	"Recruitment",
	"Data Analytics",
];

const BPO_DASHBOARD_LABELS = {
	"Human Resource": "People",
	"Attendance": "Time",
	"Recruitment": "Talent",
};

const DASHBOARD_MENU_ACTIONS = new Set(["Edit", "New", "Refresh All"]);

const HIDDEN_DASHBOARD_MENU = new Set([
	"Stock",
	"Buying",
	"Selling",
	"Project",
	"Projects",
	"CRM",
	"Accounts",
	"Accounting",
	"Asset",
	"Assets",
	"Manufacturing",
	"Payments",
	"Quality",
	"Support",
	"Website",
	"Home",
	"Invoicing",
	"Payables",
	"Receivables",
	"Financial Reports",
	"Performance",
	"Leaves",
	"Expense Claims",
	"Employee Lifecycle",
	"All",
]);

function dashboard_menu_label(name) {
	const mapped = BPO_DASHBOARD_LABELS[name] || name;
	return typeof __ === "function" ? __(mapped) : mapped;
}

function is_dashboard_view_route() {
	const route = frappe.get_route?.() || [];
	return route[0] === "dashboard-view" || route[0] === "dashboard";
}

function is_allowed_dashboard_menu_label(label) {
	const name = String(label || "").replace(/\s+/g, " ").trim();
	if (!name) return false;
	if (DASHBOARD_MENU_ACTIONS.has(name)) return true;
	if (name === __("Edit") || name === __("New") || name === __("Refresh All")) return true;
	if (BPO_DASHBOARD_MENU.has(name)) return true;
	return Object.values(BPO_DASHBOARD_LABELS).some((display) => name === display || name === __(display));
}

function is_hidden_dashboard_menu_label(label) {
	const name = String(label || "").replace(/\s+/g, " ").trim();
	if (!name || is_allowed_dashboard_menu_label(name)) return false;
	return HIDDEN_DASHBOARD_MENU.has(name);
}

function is_page_menu_parent(page, opts) {
	if (!page?.menu || !opts?.parent) return false;
	const parent = opts.parent;
	const parentEl = parent.jquery ? parent.get(0) : parent;
	const menuEl = page.menu.jquery ? page.menu.get(0) : page.menu;
	return Boolean(parentEl && menuEl && parentEl === menuEl);
}

function staff_pro_dashboard_set_dropdown() {
	this.page.clear_menu();

	this.page.add_menu_item(__("Edit"), () => {
		frappe.set_route("Form", "Dashboard", frappe.dashboard.dashboard_name);
	});
	this.page.add_menu_item(__("New"), () => {
		frappe.new_doc("Dashboard");
	});
	this.page.add_menu_item(__("Refresh All"), () => {
		this.chart_group && this.chart_group.widgets_list.forEach((chart) => chart.refresh());
		this.number_card_group && this.number_card_group.widgets_list.forEach((card) => card.render_card());
	});

	const current = this.dashboard_name;
	BPO_DASHBOARD_ORDER.filter((name) => name !== current).forEach((name) => {
		this.page.add_menu_item(dashboard_menu_label(name), () => frappe.set_route("dashboard-view", name), 1);
	});
}

function patch_page_menu_filter() {
	const Page = frappe.ui && frappe.ui.Page;
	if (!Page || Page.prototype._staff_pro_dash_menu) return;
	Page.prototype._staff_pro_dash_menu = true;

	const original = Page.prototype.add_dropdown_item;
	Page.prototype.add_dropdown_item = function (opts) {
		if (is_dashboard_view_route() && is_page_menu_parent(this, opts)) {
			const label = String(opts?.label || "").trim();
			if (!is_allowed_dashboard_menu_label(label)) {
				return $();
			}
			const display = dashboard_menu_label(label);
			if (display !== label) {
				opts = Object.assign({}, opts, { label: display });
			}
		}
		return original.call(this, opts);
	};

	if (typeof Page.prototype.build_dropdown_options === "function") {
		const original_build = Page.prototype.build_dropdown_options;
		Page.prototype.build_dropdown_options = function ($parent) {
			const options = original_build.call(this, $parent);
			if (!is_dashboard_view_route() || !$parent || !this.menu || !$parent.is(this.menu)) {
				return options;
			}
			return filter_dashboard_menu_options(options);
		};
	}
}

function filter_dashboard_menu_options(options) {
	if (!Array.isArray(options)) return options;
	return options
		.map((row) => {
			if (row && Array.isArray(row.options)) {
				const nested = filter_dashboard_menu_options(row.options);
				return nested.length ? Object.assign({}, row, { options: nested }) : null;
			}
			const label = String(row?.label || "").trim();
			if (!is_allowed_dashboard_menu_label(label)) return null;
			const display = dashboard_menu_label(label);
			return display === label ? row : Object.assign({}, row, { label: display });
		})
		.filter(Boolean);
}

function patch_live_dashboard_menu() {
	const dash = frappe.dashboard;
	if (!dash || typeof dash.set_dropdown !== "function") return;
	if (dash._staff_pro_dropdown) return;

	dash._staff_pro_dropdown = true;
	dash.set_dropdown = staff_pro_dashboard_set_dropdown;
	if (dash.dashboard_name) {
		dash.set_dropdown();
	}
}

function strip_hidden_dashboard_menu_items() {
	if (!is_dashboard_view_route()) return;

	const $store = frappe.dashboard?.page?.menu;
	if ($store?.length) {
		$store.find("li, a, button, .dropdown-item").each(function () {
			const label = ($(this).text() || "").replace(/\s+/g, " ").trim();
			if (is_hidden_dashboard_menu_label(label)) {
				$(this).closest("li").addBack("li").first().remove();
			}
		});
	}

	document.querySelectorAll(".es-menu .es-menu__item").forEach((el) => {
		const label = (
			el.querySelector(".es-menu__label")?.textContent ||
			el.textContent ||
			""
		)
			.replace(/\s+/g, " ")
			.trim();
		if (is_hidden_dashboard_menu_label(label)) {
			el.remove();
		}
	});
}

function install_dashboard_menu_filter() {
	patch_page_menu_filter();
	patch_live_dashboard_menu();
	strip_hidden_dashboard_menu_items();
}

function enhance() {
	inject_dash_css();
	patch_list_view_meta();
	document.body.classList.add("staff-pro-alive");
	install_dashboard_menu_filter();
	const route = frappe.get_route?.() || [];
	const $root = page_root();

	if ($root.length && (route[0] === "dashboard-view" || route[0] === "dashboard")) {
		$root.find(".sp-dash-celebrations:not(.sp-dash-panel)").remove();
		inject_quick_actions($root);
		inject_celebrations($root);
		reorder_hr_dashboard_layout($root);
		filter_hr_charts($root);
		format_pie_legend_percentages($root);
		inject_hours_board($root);
		upgrade_native_selects($root);
		$root.find(".sp-dash-start").remove();
		if (dashboard_name() !== "Attendance") {
			enhance_empty_charts($root);
		}
	}

	theme_number_cards($(document.body));
	enhance_page_empty();
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

hrms.ui.dash_select_html = dash_select_html;
hrms.ui.bind_dash_selects = bind_dash_selects;
hrms.ui.set_dash_select_options = set_dash_select_options;
hrms.ui.refresh_desk_dashboard = enhance;

$(document).on("app_ready", watch);
$(document).on("page-change", () => setTimeout(enhance, 60));

if (typeof frappe !== "undefined" && document.body) {
	watch();
}
