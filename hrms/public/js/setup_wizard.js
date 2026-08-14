frappe.provide("hrms.setup");

const STAFF_PRO_WELCOME_TITLE = "Welcome to Staff Pro BPO";

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

apply_staff_pro_welcome_title();
remove_erpnext_persona_slide();
document.title = "Staff Pro BPO";

frappe.setup.on("before_load", () => {
	apply_staff_pro_welcome_title();
	remove_erpnext_persona_slide();
});
frappe.setup.on("after_load", apply_staff_pro_welcome_title);
