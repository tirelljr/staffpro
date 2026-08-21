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

function hide_new_email_buttons($after) {
	$after.find("button.action-btn, .action-btn").each(function () {
		const label = ($(this).text() || "").replace(/\s+/g, " ").trim();
		if (!label.includes(__("New Email")) && !label.includes("New Email")) {
			return;
		}
		const $action = $(this).closest(".timeline-item.timeline-action, .timeline-actions");
		if ($action.length) {
			$action.addClass("staff-pro-hide-new-email").hide();
		} else {
			$(this).addClass("staff-pro-hide-new-email").hide();
		}
	});
}

function apply_staff_pro_form_footer(frm) {
	const $page = frm?.page?.wrapper || frm?.$wrapper;
	if (!$page?.length) {
		return;
	}

	const $after = $page.find(".form-footer .after-save, .after-save");
	if (!$after.length) {
		return;
	}

	replace_own_text($after, [__("Comments"), "Comments"], __("Collab"));
	$after.find(".comment-input-header").each(function () {
		replace_own_text($(this), [__("Comments"), "Comments"], __("Collab"));
	});

	const audit_label = __("Audit Logs");
	$after.find(".timeline-item.activity-title h4, .activity-title h4").text(audit_label);
	replace_own_text($after, [__("Activity"), "Activity"], audit_label);

	hide_new_email_buttons($after);
}

function schedule_staff_pro_form_footer(frm) {
	if (!frm) {
		return;
	}
	apply_staff_pro_form_footer(frm);
	setTimeout(() => apply_staff_pro_form_footer(frm), 200);
	setTimeout(() => apply_staff_pro_form_footer(frm), 800);
}

function patch_form_timeline_email() {
	const Timeline = frappe.ui?.form?.FormTimeline;
	if (!Timeline?.prototype || Timeline.prototype._staff_pro_hide_new_email) {
		return;
	}
	Timeline.prototype._staff_pro_hide_new_email = true;

	for (const method of ["setup_email_button", "setup_new_email_button", "make_email_button"]) {
		if (typeof Timeline.prototype[method] === "function") {
			Timeline.prototype[method] = function () {};
		}
	}
}

function patch_form_footer() {
	const Form = frappe.ui?.form?.Form;
	if (!Form?.prototype || Form.prototype._staff_pro_form_footer) {
		return;
	}
	Form.prototype._staff_pro_form_footer = true;

	const original_refresh = Form.prototype.refresh;
	Form.prototype.refresh = function (...args) {
		const result = original_refresh.apply(this, args);
		schedule_staff_pro_form_footer(this);
		return result;
	};

	const original_trigger = Form.prototype.trigger;
	Form.prototype.trigger = function (event, ...args) {
		const result = original_trigger.apply(this, arguments);
		if (event === "timeline_refresh") {
			apply_staff_pro_form_footer(this);
		}
		return result;
	};

	patch_form_timeline_email();
}

$(document).on("app_ready", patch_form_footer);
$(document).on("page-change", () => {
	patch_form_footer();
	if (typeof cur_frm !== "undefined" && cur_frm) {
		schedule_staff_pro_form_footer(cur_frm);
	}
});
