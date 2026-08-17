frappe.provide("hrms.setup");

const STAFF_PRO_WELCOME_TITLE = "Welcome to Staff Pro BPO";
const STAFF_PRO_COMPANY_NAME = "Staff Pro BPO";
const STAFF_PRO_COMPANY_ABBR = "SPB";

function apply_staff_pro_welcome_title() {
	const title = () => __(STAFF_PRO_WELCOME_TITLE);
	for (const collection of [frappe.setup.slides_settings, frappe.setup.slides]) {
		const welcome = (collection || []).find((slide) => slide.name === "welcome");
		if (welcome) {
			welcome.title = title;
		}
	}
}

function remove_erpnext_persona_slide() {
	if (frappe.setup?.remove_slide) {
		frappe.setup.remove_slide("persona");
	}
	if (Array.isArray(erpnext?.setup?.slides_settings)) {
		erpnext.setup.slides_settings = erpnext.setup.slides_settings.filter(
			(slide) => slide.name !== "persona",
		);
	}
}

function customize_organization_slide() {
	const org_slide = erpnext?.setup?.slides_settings?.find(
		(slide) => slide.name === "organization",
	);
	if (!org_slide) {
		return;
	}

	org_slide.fields = org_slide.fields.filter((field) => field.fieldname !== "setup_demo");

	for (const field of org_slide.fields) {
		if (field.fieldname === "company_name") {
			field.default = STAFF_PRO_COMPANY_NAME;
			field.read_only = 1;
		}
		if (field.fieldname === "company_abbr") {
			field.default = STAFF_PRO_COMPANY_ABBR;
			field.read_only = 1;
		}
	}

	const original_before_show = org_slide.before_show;
	org_slide.onload = function (slide) {
		set_staff_pro_company_values(slide);
		slide.get_input("company_name")?.off("input");
		slide.get_input("company_abbr")?.off("change");

		slide.get_input("fy_start_date")?.off("change.staffpro").on("change.staffpro", function () {
			const start_date = slide.form.fields_dict.fy_start_date.get_value();
			const year_end_date = frappe.datetime.add_days(
				frappe.datetime.add_months(start_date, 12),
				-1,
			);
			slide.form.fields_dict.fy_end_date.set_value(year_end_date);
		});

		slide.get_input("view_coa")?.off("click.staffpro").on("click.staffpro", function () {
			const chart_template = slide.form.fields_dict.chart_of_accounts.get_value();
			if (!chart_template) {
				return;
			}
			org_slide.charts_modal(slide, chart_template);
		});
	};

	org_slide.before_show = function () {
		original_before_show?.call(this);
		set_staff_pro_company_values(this);
	};

	const original_validate = org_slide.validate;
	org_slide.validate = function () {
		set_staff_pro_company_values(this);
		this.values.company_name = STAFF_PRO_COMPANY_NAME;
		this.values.company_abbr = STAFF_PRO_COMPANY_ABBR;
		this.values.setup_demo = 0;
		return original_validate?.call(this) ?? true;
	};
}

function set_staff_pro_company_values(slide) {
	if (!slide?.get_field) {
		return;
	}

	for (const [fieldname, value] of [
		["company_name", STAFF_PRO_COMPANY_NAME],
		["company_abbr", STAFF_PRO_COMPANY_ABBR],
	]) {
		const field = slide.get_field(fieldname);
		if (!field) {
			continue;
		}

		field.set_value(value);

		if (field.df) {
			field.df.read_only = 1;
		}
		if (typeof field.refresh === "function") {
			field.refresh();
		}
		field.$input?.prop("readonly", true);
	}

	if (frappe.wizard?.values) {
		frappe.wizard.values.company_name = STAFF_PRO_COMPANY_NAME;
		frappe.wizard.values.company_abbr = STAFF_PRO_COMPANY_ABBR;
		frappe.wizard.values.setup_demo = 0;
	}
}

function apply_staff_pro_setup_customizations() {
	apply_staff_pro_welcome_title();
	remove_erpnext_persona_slide();
	customize_organization_slide();
}

apply_staff_pro_setup_customizations();
document.title = "Staff Pro BPO";

frappe.setup.on("before_load", apply_staff_pro_setup_customizations);
frappe.setup.on("after_load", apply_staff_pro_welcome_title);
