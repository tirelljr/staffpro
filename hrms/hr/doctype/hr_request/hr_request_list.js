const OPEN_LETTER_STATUSES = ["Open", "In Progress", "Waiting on Employee"];

function can_review_job_letters() {
	return (
		frappe.session.user === "Administrator" ||
		frappe.user.has_role("System Manager") ||
		frappe.user.has_role("HR Manager") ||
		frappe.user.has_role("HR User")
	);
}

function review_job_letter_from_list(listview, name, action, comment) {
	frappe.call({
		method: "hrms.hr.job_letter.review_job_letter",
		args: { name, action, comment: comment || "" },
		freeze: true,
		freeze_message: action === "Approve" ? __("Creating the job letter PDF...") : __("Rejecting..."),
		callback(response) {
			const letter = response.message || {};
			if (action === "Approve" && !letter.letter_document) {
				frappe.msgprint(__("The request was approved, but the PDF was not created."));
			}
			listview.refresh();
		},
	});
}

frappe.listview_settings["HR Request"] = {
	add_fields: ["status", "priority", "request_type", "assigned_to"],
	filters: [["status", "not in", ["Resolved", "Rejected", "Cancelled"]]],
	has_indicator_for_draft: 1,
	formatters: {
		priority(value, df, doc) {
			const label = __(value || "");
			if (
				!can_review_job_letters() ||
				doc.request_type !== "Job Letter" ||
				!OPEN_LETTER_STATUSES.includes(doc.status)
			) {
				return label;
			}
			const name = frappe.utils.escape_html(doc.name);
			return `<span class="jl-priority">${label}</span><span class="jl-actions"><button type="button" class="btn btn-primary btn-xs jl-approve" data-name="${name}">${__(
				"Approve",
			)}</button><button type="button" class="btn btn-danger btn-xs jl-reject" data-name="${name}">${__(
				"Reject",
			)}</button></span>`;
		},
	},
	get_indicator: function (doc) {
		const colors = {
			Open: "orange",
			"In Progress": "blue",
			"Waiting on Employee": "yellow",
			Resolved: "green",
			Rejected: "red",
			Cancelled: "gray",
		};
		return [__(doc.status), colors[doc.status] || "gray", "status,=," + doc.status];
	},
	onload: function (listview) {
		if (!document.getElementById("hr-request-review-css")) {
			const style = document.createElement("style");
			style.id = "hr-request-review-css";
			style.textContent = `
				.list-row-col[data-fieldname="priority"],
				.list-row-head .list-row-col[data-fieldname="priority"] {
					overflow: visible !important;
					text-overflow: unset !important;
					flex: 1.6 0 220px !important;
					white-space: nowrap;
				}
				.list-row-col[data-fieldname="priority"] .ellipsis {
					overflow: visible !important;
					text-overflow: unset !important;
				}
				.jl-actions { display: inline-flex; gap: 4px; margin-left: 8px; vertical-align: middle; }
				.jl-actions .btn { padding: 1px 8px; line-height: 1.5; }
			`;
			document.head.appendChild(style);
		}
		if (!listview._job_letter_actions) {
			listview._job_letter_actions = true;
			const wrapper = listview.page.wrapper.get(0);
			wrapper.addEventListener(
				"click",
				(event) => {
					const button = event.target.closest(".jl-approve, .jl-reject");
					if (!button) return;
					event.preventDefault();
					event.stopPropagation();
					const name = button.getAttribute("data-name");
					if (!name) return;
					if (button.classList.contains("jl-approve")) {
						frappe.confirm(__("Approve this job letter and create the PDF?"), () => {
							review_job_letter_from_list(listview, name, "Approve", "");
						});
						return;
					}
					frappe.prompt(
						[{ fieldname: "comment", fieldtype: "Small Text", label: __("Reason") }],
						(values) => review_job_letter_from_list(listview, name, "Reject", values.comment || ""),
						__("Reject Request"),
						__("Reject"),
					);
				},
				true,
			);
			wrapper.addEventListener(
				"mousedown",
				(event) => {
					if (event.target.closest(".jl-approve, .jl-reject")) event.stopPropagation();
				},
				true,
			);
		}

		const apply = (filters) => {
			listview.filter_area.clear();
			filters.forEach((filter) => listview.filter_area.add(filter));
			listview.refresh();
		};

		listview.page.add_inner_button(__("Open"), () => {
			apply([["HR Request", "status", "=", "Open"]]);
		});
		listview.page.add_inner_button(__("Unassigned"), () => {
			apply([
				["HR Request", "assigned_to", "=", ""],
				["HR Request", "status", "not in", ["Resolved", "Rejected", "Cancelled"]],
			]);
		});
		listview.page.add_inner_button(__("Job Letters"), () => {
			apply([
				["HR Request", "request_type", "=", "Job Letter"],
				["HR Request", "status", "not in", ["Resolved", "Rejected", "Cancelled"]],
			]);
		});
		listview.page.add_inner_button(__("Office Prints"), () => {
			apply([
				["HR Request", "request_type", "=", "Office Print"],
				["HR Request", "status", "not in", ["Resolved", "Rejected", "Cancelled"]],
			]);
		});
		listview.page.add_inner_button(__("My Tickets"), () => {
			apply([["HR Request", "assigned_to", "=", frappe.session.user]]);
		});
	},
};
