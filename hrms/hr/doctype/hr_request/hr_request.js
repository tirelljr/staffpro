// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("HR Request", {
	refresh(frm) {
		render_letter(frm);
		fill_job_letter_salary(frm);
		lock_job_letter_for_agent(frm);
		render_inline_review(frm);
		if (frm.doc.request_type === "Job Letter") {
			if (!frm.doc.__islocal && ["Open", "In Progress", "Waiting on Employee"].includes(frm.doc.status)) {
				frm.add_custom_button(__("Edit Letter"), () => open_letter_editor(frm));
			}
			if (frm.doc.letter_html) {
				frm.add_custom_button(__("Print"), () => print_letter(frm.doc.name));
			}
		}
		if (frm.doc.request_type === "Office Print" && frm.doc.letter_html) {
			frm.add_custom_button(__("Print"), () => print_letter(frm.doc.name)).addClass("btn-primary");
			if (["Open", "In Progress", "Waiting on Employee"].includes(frm.doc.status)) {
				add_review_buttons(frm);
			}
		}
	},

	request_type(frm) {
		if (frm.doc.request_type === "Job Letter" && !frm.doc.subject) {
			frm.set_value("subject", __("Job Letter Request"));
		}
		fill_job_letter_salary(frm);
		lock_job_letter_for_agent(frm);
	},

	employee(frm) {
		fill_job_letter_salary(frm);
	},
});

function is_letter_staff() {
	return (
		frappe.session.user === "Administrator" ||
		frappe.user.has_role("System Manager") ||
		frappe.user.has_role("HR Manager") ||
		frappe.user.has_role("HR User")
	);
}

function lock_job_letter_for_agent(frm) {
	if (frm.doc.request_type !== "Job Letter" || is_letter_staff()) return;
	frm.set_df_property("annual_salary", "read_only", 1);
	frm.set_df_property("biweekly_salary", "read_only", 1);
	frm.attachments?.parent?.hide?.();
	const $page = frm.page?.wrapper || frm.$wrapper;
	$page?.find(".form-sidebar .form-attachments, .form-attachments").hide();
}

function fill_job_letter_salary(frm) {
	if (frm.doc.request_type !== "Job Letter" || !frm.doc.employee) return;
	if (flt(frm.doc.annual_salary) && flt(frm.doc.biweekly_salary)) return;
	frappe.call({
		method: "hrms.hr.job_letter.salary_for_employee",
		args: { employee: frm.doc.employee },
		callback(response) {
			const pay = response.message || {};
			if (!flt(frm.doc.annual_salary)) frm.set_value("annual_salary", pay.annual_salary);
			if (!flt(frm.doc.biweekly_salary)) frm.set_value("biweekly_salary", pay.biweekly_salary);
		},
	});
}

function render_letter(frm) {
	const field = frm.get_field("letter_preview");
	if (!field || !field.$wrapper) return;
	if (!["Job Letter", "Office Print"].includes(frm.doc.request_type)) {
		field.$wrapper.empty();
		return;
	}
	if (frm.doc.__islocal || !frm.doc.name) {
		mount_letter_preview(field.$wrapper, frm.doc.letter_html || "");
		return;
	}
	const requested = frm.doc.name;
	field.$wrapper.html(`<div class="text-muted" style="padding:12px;">${__("Loading the letter...")}</div>`);
	frappe.call({
		method: "hrms.hr.job_letter.get_letter_preview",
		args: { name: requested },
		callback(response) {
			if (!frm.doc || frm.doc.name !== requested) return;
			mount_letter_preview(field.$wrapper, (response.message || {}).html || "");
		},
		error() {
			if (!frm.doc || frm.doc.name !== requested) return;
			mount_letter_preview(field.$wrapper, frm.doc.letter_html || "");
		},
	});
}

function mount_letter_preview($wrapper, html) {
	const frame = document.createElement("iframe");
	frame.title = __("Job letter");
	frame.setAttribute("scrolling", "yes");
	frame.style.cssText =
		"width:100%;height:1056px;border:0;background:#fff;display:block;border-radius:12px;";
	const page = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:#fff;}</style></head><body>${
		html || `<p style="font-family:sans-serif;color:#6b7280;padding:24px;">${__("The letter appears here after it is generated.")}</p>`
	}</body></html>`;
	$wrapper.html(
		`<div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;"></div>`,
	);
	$wrapper.children("div").append(frame);
	frame.srcdoc = page;
}

const OPEN_LETTER_STATUSES = ["Open", "In Progress", "Waiting on Employee"];

function render_inline_review(frm) {
	const field = frm.get_field("priority");
	if (!field || !field.$wrapper) return;
	field.$wrapper.find(".jl-inline-review").remove();
	if (frm.doc.request_type !== "Job Letter" || frm.doc.__islocal || !is_letter_staff()) return;
	if (!OPEN_LETTER_STATUSES.includes(frm.doc.status)) return;
	const $actions = $(`
		<div class="jl-inline-review" style="display:flex; gap:8px; margin-top:12px;">
			<button type="button" class="btn btn-primary btn-sm jl-approve">${__("Approve")}</button>
			<button type="button" class="btn btn-danger btn-sm jl-reject">${__("Reject")}</button>
		</div>
	`);
	field.$wrapper.append($actions);
	$actions.find(".jl-approve").on("click", () => approve_letter(frm));
	$actions.find(".jl-reject").on("click", () => reject_letter(frm));
}

function approve_letter(frm) {
	const message =
		frm.doc.request_type === "Job Letter"
			? __("Approve this job letter and create the PDF?")
			: __("Approve this request?");
	frappe.confirm(message, () => {
		review_letter(frm, "Approve", "");
	});
}

function reject_letter(frm) {
	frappe.prompt(
		[{ fieldname: "comment", fieldtype: "Small Text", label: __("Reason") }],
		(values) => review_letter(frm, "Reject", values.comment || ""),
		__("Reject Request"),
		__("Reject"),
	);
}

function review_letter(frm, action, comment) {
	frappe.call({
		method: "hrms.hr.job_letter.review_job_letter",
		args: { name: frm.doc.name, action, comment },
		freeze: true,
		freeze_message: action === "Approve" ? __("Creating the job letter PDF...") : __("Rejecting..."),
		callback(response) {
			const letter = response.message || {};
			if (action === "Approve" && frm.doc.request_type === "Job Letter" && !letter.letter_document) {
				frappe.msgprint(__("The request was approved, but the PDF was not created."));
			}
			frm.reload_doc();
		},
	});
}

function print_letter(name) {
	const url = frappe.urllib.get_full_url(
		`/api/method/hrms.hr.job_letter.download_letter_pdf?name=${encodeURIComponent(name)}`,
	);
	window.open(url);
}

function add_review_buttons(frm) {
	frm.add_custom_button(__("Approve"), () => approve_letter(frm), __("Review"));
	frm.add_custom_button(__("Reject"), () => reject_letter(frm), __("Review"));
}

function open_letter_editor(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Edit Job Letter"),
		size: "extra-large",
		fields: [
			{
				fieldname: "addressed_to",
				fieldtype: "Data",
				label: __("Addressed To"),
				default: frm.doc.addressed_to,
			},
			{
				fieldname: "recipient_address",
				fieldtype: "Small Text",
				label: __("Recipient Address"),
				default: frm.doc.recipient_address,
			},
			{
				fieldname: "honorific",
				fieldtype: "Select",
				label: __("Title"),
				options: "\nMr.\nMs.\nMrs.",
				default: frm.doc.honorific,
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "annual_salary",
				fieldtype: "Currency",
				label: __("Yearly Salary"),
				default: frm.doc.annual_salary,
			},
			{
				fieldname: "biweekly_salary",
				fieldtype: "Currency",
				label: __("Biweekly Salary"),
				default: frm.doc.biweekly_salary,
			},
			{
				fieldname: "letter_paragraphs",
				fieldtype: "Text",
				label: __("Letter Text"),
				default: frm.doc.letter_paragraphs,
			},
			{
				fieldname: "rebuild_text",
				fieldtype: "Button",
				label: __("Rebuild Text"),
				click() {
					save_letter(frm, dialog, dialog.get_values(), 1);
				},
			},
		],
		primary_action_label: __("Save"),
		primary_action() {
			save_letter(frm, dialog, dialog.get_values(), 0);
		},
	});
	dialog.show();
}

function save_letter(frm, dialog, values, rebuild) {
	frappe.call({
		method: "hrms.hr.job_letter.update_job_letter",
		args: {
			name: frm.doc.name,
			addressed_to: values.addressed_to,
			recipient_address: values.recipient_address,
			honorific: values.honorific,
			annual_salary: values.annual_salary,
			biweekly_salary: values.biweekly_salary,
			letter_paragraphs: values.letter_paragraphs,
			rebuild,
		},
		callback(response) {
			if (cint(rebuild)) {
				const letter = response.message || {};
				dialog.set_value("letter_paragraphs", letter.letter_paragraphs || "");
				dialog.set_value("honorific", letter.honorific || values.honorific || "");
				dialog.set_value("annual_salary", letter.annual_salary);
				dialog.set_value("biweekly_salary", letter.biweekly_salary);
				frm.reload_doc();
				return;
			}
			dialog.hide();
			frm.reload_doc();
		},
	});
}
