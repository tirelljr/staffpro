frappe.provide("hrms.setup");

const STAFF_PRO_WELCOME_TITLE = "Welcome to Staff Pro BPO";
const STAFF_PRO_COMPANY_NAME = "Staff Pro BPO";
const STAFF_PRO_COMPANY_ABBR = "SPB";
const STAFF_PRO_COUNTRY = "Belize";
const STAFF_PRO_TIMEZONE = "America/Belize";
const STAFF_PRO_CURRENCY = "BZD";
const STAFF_PRO_CURRENCY_OPTIONS = ["BZD", "USD"];
const STAFF_PRO_SETUP_TITLE = "Setting up Staff Pro";
const STAFF_PRO_SETUP_MESSAGE = "Setting up Staff Pro ...";

function apply_staff_pro_welcome_title() {
	const title = () => __(STAFF_PRO_WELCOME_TITLE);
	for (const collection of [frappe.setup.slides_settings, frappe.setup.slides]) {
		const welcome = (collection || []).find((slide) => slide.name === "welcome");
		if (welcome) {
			welcome.title = title;
		}
	}
}

function seed_staff_pro_wizard_region_values() {
	frappe.wizard = frappe.wizard || {};
	frappe.wizard.values = frappe.wizard.values || {};
	frappe.wizard.values.country = STAFF_PRO_COUNTRY;
	frappe.wizard.values.timezone = STAFF_PRO_TIMEZONE;
	if (
		!frappe.wizard.values.currency ||
		!STAFF_PRO_CURRENCY_OPTIONS.includes(frappe.wizard.values.currency)
	) {
		frappe.wizard.values.currency = STAFF_PRO_CURRENCY;
	}
}

function patch_setup_region_fields() {
	if (frappe.setup?.utils?._staff_pro_currency_patched) {
		return;
	}

	const original_setup_region_fields = frappe.setup.utils.setup_region_fields;
	frappe.setup.utils.setup_region_fields = function (slide) {
		original_setup_region_fields.call(this, slide);
		set_staff_pro_locked_region_values(slide);
		setup_staff_pro_currency_field(slide);
	};
	frappe.setup.utils._staff_pro_currency_patched = true;
}

function customize_welcome_slide() {
	const welcome_slide = (frappe.setup?.slides_settings || []).find(
		(slide) => slide.name === "welcome",
	);
	if (!welcome_slide || welcome_slide._staff_pro_customized) {
		return;
	}
	welcome_slide._staff_pro_customized = true;

	for (const field of welcome_slide.fields || []) {
		if (field.fieldname === "country") {
			field.default = STAFF_PRO_COUNTRY;
			field.read_only = 1;
		}
		if (field.fieldname === "timezone") {
			field.default = STAFF_PRO_TIMEZONE;
			field.read_only = 1;
		}
		if (field.fieldname === "currency") {
			field.default = STAFF_PRO_CURRENCY;
			field.options = STAFF_PRO_CURRENCY_OPTIONS.join("\n");
		}
	}

	const original_initialize = welcome_slide.initialize_fields;
	welcome_slide.initialize_fields = function (slide) {
		seed_staff_pro_wizard_region_values();
		original_initialize?.call(this, slide);
	};

	const original_onload = welcome_slide.onload;
	welcome_slide.onload = function (slide) {
		seed_staff_pro_wizard_region_values();
		original_onload?.call(this, slide);
	};

	welcome_slide.validate = function () {
		if (!this?.get_field) {
			return true;
		}

		this.get_field("country")?.set_input(STAFF_PRO_COUNTRY);
		this.get_field("timezone")?.set_input(STAFF_PRO_TIMEZONE);
		setup_staff_pro_currency_field(this);

		const currency = get_staff_pro_currency_value(this);
		this.values.country = STAFF_PRO_COUNTRY;
		this.values.timezone = STAFF_PRO_TIMEZONE;
		this.values.currency = currency;
		frappe.wizard.values.country = STAFF_PRO_COUNTRY;
		frappe.wizard.values.timezone = STAFF_PRO_TIMEZONE;
		frappe.wizard.values.currency = currency;
		return true;
	};
}

function get_staff_pro_currency_value(slide) {
	const currency =
		slide.get_value?.("currency") ||
		slide.get_field?.("currency")?.get_value?.() ||
		frappe.wizard.values.currency;
	return STAFF_PRO_CURRENCY_OPTIONS.includes(currency) ? currency : STAFF_PRO_CURRENCY;
}

function setup_staff_pro_currency_field(slide) {
	const currency_field = slide.get_field("currency");
	if (!currency_field) {
		return;
	}

	if (currency_field.df) {
		currency_field.df.options = STAFF_PRO_CURRENCY_OPTIONS.join("\n");
		currency_field.df.read_only = 0;
	}

	slide.get_input("currency").empty().add_options(STAFF_PRO_CURRENCY_OPTIONS);

	const currency = get_staff_pro_currency_value(slide);
	currency_field.set_input(currency);
	currency_field.$input?.trigger("change");

	if (typeof currency_field.refresh === "function") {
		currency_field.refresh();
		// Frappe refresh can rebuild options from df; keep the Staff Pro list.
		slide.get_input("currency").empty().add_options(STAFF_PRO_CURRENCY_OPTIONS);
		currency_field.set_input(currency);
	}
	currency_field.$input?.prop("readonly", false).prop("disabled", false);

	frappe.wizard.values.currency = currency;

	slide.get_input("currency")?.off("change.staffpro").on("change.staffpro", function () {
		const selected = slide.get_input("currency").val();
		if (STAFF_PRO_CURRENCY_OPTIONS.includes(selected)) {
			frappe.wizard.values.currency = selected;
		}
	});
}

function set_staff_pro_locked_region_values(slide) {
	if (!slide?.get_field) {
		return;
	}

	frappe.wizard.values.country = STAFF_PRO_COUNTRY;
	frappe.wizard.values.timezone = STAFF_PRO_TIMEZONE;

	const country_field = slide.get_field("country");
	if (country_field) {
		country_field.set_input(STAFF_PRO_COUNTRY);
		$(country_field.input).change();
	}

	slide.get_field("timezone")?.set_input(STAFF_PRO_TIMEZONE);

	for (const fieldname of ["country", "timezone"]) {
		const field = slide.get_field(fieldname);
		if (!field) {
			continue;
		}

		if (field.df) {
			field.df.read_only = 1;
		}
		if (typeof field.refresh === "function") {
			field.refresh();
		}
		field.$input?.prop("readonly", true);
	}

	slide.get_input("country")?.off("change");
	slide.get_input("timezone")?.off("change");
}

function set_staff_pro_region_values(slide) {
	set_staff_pro_locked_region_values(slide);
	setup_staff_pro_currency_field(slide);
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

function is_frappe_setup_copy(value) {
	const text = String(value || "").trim();
	return (
		text === "Setting up your system" ||
		text === __("Setting up your system") ||
		text === "Starting Frappe ..." ||
		text === __("Starting Frappe ...")
	);
}

function patch_setup_working_state() {
	const Wizard = frappe.setup?.SetupWizard;
	if (!Wizard?.prototype || Wizard.prototype._staff_pro_working_state) {
		return;
	}
	Wizard.prototype._staff_pro_working_state = true;

	const original_show = Wizard.prototype.show_working_state;
	Wizard.prototype.show_working_state = function () {
		original_show.call(this);
		this.set_setup_complete_message?.(__("Setting up Staff Pro"), __("Setting up Staff Pro ..."));
		this.update_setup_message?.(__("Setting up Staff Pro ..."));
	};

	const original_get_message = Wizard.prototype.get_message;
	if (original_get_message) {
		Wizard.prototype.get_message = function (title, message = "") {
			if (is_frappe_setup_copy(title)) {
				title = __(STAFF_PRO_SETUP_TITLE);
			}
			if (is_frappe_setup_copy(message)) {
				message = __(STAFF_PRO_SETUP_MESSAGE);
			}
			return original_get_message.call(this, title, message);
		};
	}

	const original_update = Wizard.prototype.update_setup_message;
	if (original_update) {
		Wizard.prototype.update_setup_message = function (message) {
			if (is_frappe_setup_copy(message) || !message) {
				message = __(STAFF_PRO_SETUP_MESSAGE);
			}
			return original_update.call(this, message);
		};
	}
}

function apply_staff_pro_setup_customizations() {
	patch_setup_region_fields();
	patch_setup_working_state();
	seed_staff_pro_wizard_region_values();
	apply_staff_pro_welcome_title();
	remove_erpnext_persona_slide();
	customize_welcome_slide();
	customize_organization_slide();
}

function apply_staff_pro_welcome_slide_fields() {
	const welcome_slide = frappe.wizard?.slides?.find((slide) => slide.name === "welcome");
	if (!welcome_slide?.get_field) {
		return;
	}
	set_staff_pro_locked_region_values(welcome_slide);
	setup_staff_pro_currency_field(welcome_slide);
}

apply_staff_pro_setup_customizations();
document.title = "Staff Pro BPO";

frappe.setup.on("before_load", apply_staff_pro_setup_customizations);
frappe.setup.on("after_load", () => {
	apply_staff_pro_welcome_title();
	apply_staff_pro_welcome_slide_fields();
});
