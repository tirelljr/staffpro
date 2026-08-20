// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("HR Settings", {
	refresh: function (frm) {
		frm.set_query("sender", () => {
			return {
				filters: {
					enable_outgoing: 1,
				},
			};
		});
		frm.set_query("hiring_sender", () => {
			return {
				filters: {
					enable_outgoing: 1,
				},
			};
		});
		setup_hr_settings_audit_logs(frm);
		setTimeout(() => setup_hr_settings_audit_logs(frm), 200);
		setTimeout(() => setup_hr_settings_audit_logs(frm), 800);
	},
	timeline_refresh: function (frm) {
		setup_hr_settings_audit_logs(frm);
	},
});

function setup_hr_settings_audit_logs(frm) {
	const $page = frm.page?.wrapper || frm.$wrapper;
	if (!$page?.length) {
		return;
	}

	const $after = $page.find(".after-save");
	if (!$after.length) {
		return;
	}

	const audit_label = __("Audit Logs");
	replace_own_text($after, [__("Comments"), "Comments"], audit_label);
	$after.find(".timeline-item.activity-title h4, .activity-title h4").text(audit_label);
	replace_own_text($after, [__("Activity"), "Activity"], audit_label);

	$after.find("button.action-btn, .action-btn").each(function () {
		const label = ($(this).text() || "").replace(/\s+/g, " ").trim();
		if (label.includes(__("New Email")) || label.includes("New Email")) {
			$(this).closest(".timeline-actions").length ? $(this).closest(".timeline-actions").hide() : $(this).hide();
		}
	});
}

function replace_own_text($root, from_labels, to_label) {
	const labels = new Set(from_labels.filter(Boolean));
	$root.find("h4, h5, span, div, label").each(function () {
		const own = Array.from(this.childNodes)
			.filter((node) => node.nodeType === Node.TEXT_NODE)
			.map((node) => (node.textContent || "").trim())
			.filter(Boolean)
			.join(" ");
		if (!labels.has(own)) {
			return;
		}
		Array.from(this.childNodes).forEach((node) => {
			if (node.nodeType === Node.TEXT_NODE && labels.has((node.textContent || "").trim())) {
				node.textContent = to_label;
			}
		});
	});
}

frappe.tour["HR Settings"] = [
	{
		fieldname: "emp_created_by",
		title: "Employee Naming By",
		description: __(
			"Employee can be named by Employee ID if you assign one, or via Naming Series. Select your preference here.",
		),
	},
	{
		fieldname: "standard_working_hours",
		title: "Standard Working Hours",
		description: __(
			"Enter the Standard Working Hours for a normal work day. These hours will be used in calculations of reports such as Employee Hours Utilization and Project Profitability analysis.",
		),
	},
	{
		fieldname: "leave_and_expense_claim_settings",
		title: "Leave and Expense Claim Settings",
		description: __(
			"Review various other settings related to Employee Leaves and Expense Claim",
		),
	},
];
