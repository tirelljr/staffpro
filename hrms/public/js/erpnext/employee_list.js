const existing_employee_listview = frappe.listview_settings["Employee"] || {};
const existing_onload = existing_employee_listview.onload;
const existing_refresh = existing_employee_listview.refresh;
const EMPLOYEE_IMAGE_FIELDS = ["department", "date_of_joining", "image", "employee_name"];

frappe.listview_settings["Employee"] = Object.assign({}, existing_employee_listview, {
	add_fields: [...new Set([...(existing_employee_listview.add_fields || []), ...EMPLOYEE_IMAGE_FIELDS])],
	onload(listview) {
		existing_onload?.(listview);
		hide_employee_list_menu(listview);
		ensure_employee_image_fields(listview);
	},
	refresh(listview) {
		existing_refresh?.(listview);
		hide_employee_list_menu(listview);
	},
});

patch_employee_image_view();

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
	if (!listview?.fields) return;
	EMPLOYEE_IMAGE_FIELDS.forEach((fieldname) => {
		if (fieldname && !listview.fields.includes(fieldname)) {
			listview.fields.push(fieldname);
		}
	});
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
}
