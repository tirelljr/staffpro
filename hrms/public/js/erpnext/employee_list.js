const existing_employee_listview = frappe.listview_settings["Employee"] || {};
const existing_onload = existing_employee_listview.onload;
const existing_refresh = existing_employee_listview.refresh;
const EMPLOYEE_IMAGE_FIELDS = [
	"name",
	"department",
	"date_of_joining",
	"image",
	"employee_name",
	"is_floor_worker",
];

frappe.listview_settings["Employee"] = Object.assign({}, existing_employee_listview, {
	add_fields: [...new Set([...field_name_list(existing_employee_listview.add_fields), ...EMPLOYEE_IMAGE_FIELDS])],
	onload(listview) {
		existing_onload?.(listview);
		hide_employee_list_menu(listview);
		ensure_employee_image_fields(listview);
		setup_employee_bulk_delete(listview);
		apply_employee_roster_filter(listview);
	},
	refresh(listview) {
		existing_refresh?.(listview);
		hide_employee_list_menu(listview);
		ensure_employee_image_fields(listview);
	},
});

patch_employee_image_view();
patch_employee_list_args();
if (typeof frappe.ready === "function") {
	frappe.ready(() => {
		patch_employee_image_view();
		patch_employee_list_args();
	});
}

function is_field_pair(value) {
	return (
		Array.isArray(value) &&
		value.length >= 2 &&
		typeof value[0] === "string" &&
		typeof value[1] === "string" &&
		!value[0].includes(".") &&
		!value[0].includes("`") &&
		value[1][0] === value[1][0]?.toUpperCase() &&
		value[1][0] !== value[1][0]?.toLowerCase()
	);
}

function field_name_list(value) {
	if (Array.isArray(value)) {
		if (is_field_pair(value)) return field_name_list(value[0]);
		return value.flatMap(field_name_list);
	}
	if (typeof value !== "string") return [];
	const text = value.trim();
	if (!text) return [];
	if (text.includes(",") && !text.includes("`")) {
		return text.split(",").flatMap(field_name_list);
	}
	const name = text.replace(/`/g, "").split(".").pop();
	if (!name || name.length < 2 || is_garbage_field(text)) return [];
	return [name];
}

function is_garbage_field(field) {
	const text = String(field || "").replace(/`/g, "");
	if (!text || text.length === 1) return true;
	const parts = text.split(".");
	const parent = (parts[0] || "").replace(/^tab/i, "");
	return parts.length === 2 && parent.length <= 1;
}

function delete_employees_with_unlink(listview, names) {
	if (!names.length) {
		frappe.msgprint(__("Select one or more agents first."));
		return;
	}
	frappe.confirm(
		__(
			"Delete {0} agent(s) and remove all linked attendance, payroll, leave, and related records? This cannot be undone.",
			[names.length],
		),
		() => {
			frappe.call({
				method: "hrms.hr.employee_cleanup.delete_employees_with_unlink",
				args: { employees: names },
				freeze: true,
				freeze_message: __("Removing linked records..."),
				callback(r) {
					if (r.exc) return;
					const count = r.message?.count || 0;
					const failed = r.message?.errors?.length || 0;
					frappe.show_alert({
						message: failed
							? __("Deleted {0} agent(s). {1} failed.", [count, failed])
							: __("Deleted {0} agent(s)", [count]),
						indicator: failed ? "orange" : "green",
					});
					listview.refresh();
				},
			});
		},
	);
}

function setup_employee_bulk_delete(listview) {
	if (!listview?.page || listview._sp_delete_hooked) return;
	listview._sp_delete_hooked = true;

	if (typeof listview.delete_items === "function") {
		listview.delete_items = function () {
			delete_employees_with_unlink(listview, listview.get_checked_items(true));
		};
	}

	listview.page.add_action_item(__("Delete selected (unlink all)"), () => {
		delete_employees_with_unlink(listview, listview.get_checked_items(true));
	});
}

function apply_employee_roster_filter(listview) {
	if (!listview?.filter_area) return;
	let mode = "";
	try {
		mode = sessionStorage.getItem("staff_pro_employee_roster") || "";
	} catch (err) {
		mode = "";
	}
	if (mode !== "floor" && mode !== "all") return;
	listview.filter_area.remove("is_floor_worker");
	if (mode === "floor") {
		listview.filter_area.add([["Employee", "is_floor_worker", "=", 1]]);
	}
}

function hide_employee_list_menu(listview) {
	const page = listview?.page;
	if (!page) return;
	if (typeof page.hide_menu === "function") {
		page.hide_menu();
	}
	page.menu_btn_group?.addClass("hidden hide").hide();
	page.wrapper?.find(".menu-btn-group").addClass("hidden hide").hide();
}

function ensure_employee_image_fields(listview) {
	if (!listview) return;
	const current = Array.isArray(listview.fields) ? listview.fields : [];
	const as_pairs = current.some(is_field_pair);
	const names = new Set(field_name_list(current));
	EMPLOYEE_IMAGE_FIELDS.forEach((fieldname) => names.add(fieldname));

	if (!as_pairs) {
		listview.fields = [...names];
		return;
	}

	const doctype = listview.doctype || "Employee";
	const fields = [];
	const seen = new Set();
	current.forEach((field) => {
		if (!is_field_pair(field) || seen.has(field[0])) return;
		seen.add(field[0]);
		fields.push(field);
	});
	names.forEach((fieldname) => {
		if (seen.has(fieldname)) return;
		seen.add(fieldname);
		fields.push([fieldname, doctype]);
	});
	listview.fields = fields;
}

function format_employee_tenure(date_of_joining) {
	if (!date_of_joining) return "";

	const today = frappe.datetime.get_today();
	const days = frappe.datetime.get_diff(today, date_of_joining);
	if (days < 0) return "";
	if (days === 0) return __("Joined today");
	if (days === 1) return __("1 day");
	if (days < 30) return __("{0} days", [days]);

	const start = frappe.datetime.str_to_obj(date_of_joining);
	const now = frappe.datetime.str_to_obj(today);
	let months = (now.getFullYear() - start.getFullYear()) * 12 + (now.getMonth() - start.getMonth());
	if (now.getDate() < start.getDate()) months -= 1;
	if (months < 1) months = 1;

	const years = Math.floor(months / 12);
	const rest = months % 12;
	const year_label = years === 1 ? __("1 year") : __("{0} years", [years]);
	const month_label = rest === 1 ? __("1 month") : __("{0} months", [rest]);

	if (years && rest) return `${year_label} ${month_label}`;
	if (years) return year_label;
	return month_label;
}

function employee_image_details_html(item) {
	const department = String(item.department || "").trim();
	const tenure = format_employee_tenure(item.date_of_joining);
	const lines = [];

	if (department) {
		const label = frappe.utils.escape_html(department);
		lines.push(
			`<div class="staff-pro-employee-card__meta ellipsis" title="${label}">${label}</div>`
		);
	}
	if (tenure) {
		const label = frappe.utils.escape_html(tenure);
		lines.push(
			`<div class="staff-pro-employee-card__meta staff-pro-employee-card__meta--tenure ellipsis" title="${label}">${label}</div>`
		);
	}
	if (cint(item.is_floor_worker)) {
		lines.push(
			`<div class="staff-pro-employee-card__meta"><span class="sp-floor-worker-badge" style="display:inline-block;padding:0 6px;border-radius:999px;background:#e7f6ec;color:#146c43;font-size:11px;font-weight:600;line-height:18px;">floorworkers</span></div>`
		);
	}
	if (!lines.length) return "";

	return `<div class="item-info staff-pro-employee-card__info">${lines.join("")}</div>`;
}

function patch_employee_image_view() {
	const ImageView = frappe.views?.ImageView;
	if (!ImageView || ImageView._staff_pro_employee_patch) return;
	ImageView._staff_pro_employee_patch = true;

	const original_set_fields = ImageView.prototype.set_fields;
	ImageView.prototype.set_fields = function () {
		original_set_fields.call(this);
		if (this.doctype !== "Employee") return;
		ensure_employee_image_fields(this);
	};

	const original_details = ImageView.prototype.item_details_html;
	ImageView.prototype.item_details_html = function (item) {
		if (this.doctype !== "Employee") {
			return original_details.call(this, item);
		}
		return employee_image_details_html(item);
	};

	const original_render = ImageView.prototype.render_image_view;
	ImageView.prototype.render_image_view = function () {
		original_render.call(this);
		if (this.doctype !== "Employee" || !this.$result) return;
		this.$result.off("click.staff-pro-employee").on(
			"click.staff-pro-employee",
			".image-view-item",
			(event) => {
				if (event.target.closest(".list-row-checkbox, .like-action, .zoom-view, .list-row-like")) {
					return;
				}
				const link = event.currentTarget.querySelector("a[data-name]");
				const raw = link?.getAttribute("data-name") || "";
				let name = raw;
				try {
					name = decodeURIComponent(raw);
				} catch (err) {
					name = raw;
				}
				if (!name || name === "undefined") return;
				event.preventDefault();
				frappe.route_options = null;
				frappe.set_route("Form", "Employee", name);
			},
		);
	};

	ImageView.prototype.get_attached_images = function () {
		const names = (this.items || [])
			.map((item) => item && item.name)
			.filter((name) => typeof name === "string" && name);
		if (!names.length) {
			this.images_map = this.images_map || {};
			return Promise.resolve();
		}
		return frappe
			.call({
				method: "hrms.overrides.attached_images.get_attached_images",
				args: { doctype: this.doctype, names },
			})
			.then((r) => {
				this.images_map = Object.assign(this.images_map || {}, r.message);
			});
	};
}

function patch_employee_list_args() {
	const ListView = frappe.views?.ListView;
	if (!ListView?.prototype || ListView._staff_pro_employee_args_patch) return;
	ListView._staff_pro_employee_args_patch = true;

	if (typeof ListView.prototype.set_fields === "function") {
		const original_set = ListView.prototype.set_fields;
		ListView.prototype.set_fields = function () {
			original_set.apply(this, arguments);
			if (this.doctype === "Employee") ensure_employee_image_fields(this);
		};
	}

	if (typeof ListView.prototype.get_args === "function") {
		const original_args = ListView.prototype.get_args;
		ListView.prototype.get_args = function () {
			const args = original_args.apply(this, arguments);
			if (this.doctype === "Employee" && args) {
				args.fields = field_name_list(args.fields);
				EMPLOYEE_IMAGE_FIELDS.forEach((fieldname) => {
					if (!args.fields.includes(fieldname)) args.fields.push(fieldname);
				});
			}
			return args;
		};
	}
}
