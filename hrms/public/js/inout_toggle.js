frappe.provide("hrms.ui");

function escape_html(value) {
	return frappe.utils.escape_html(value == null ? "" : String(value));
}

function inout_toggle_html({ className = "", value = "IN" } = {}) {
	const selected = value === "OUT" ? "OUT" : "IN";
	return `
		<div class="sp-inout-toggle ${escape_html(className)}" role="group" aria-label="${escape_html(__("In / Out"))}">
			<button type="button" class="sp-inout-toggle__btn${selected === "IN" ? " is-active" : ""}" data-value="IN">${escape_html(__("IN"))}</button>
			<button type="button" class="sp-inout-toggle__btn${selected === "OUT" ? " is-active" : ""}" data-value="OUT">${escape_html(__("OUT"))}</button>
			<input type="hidden" class="sp-inout-dash__status" value="${escape_html(selected)}" />
		</div>
	`;
}

function bind_inout_toggle($root, on_change) {
	if (!$root?.length) return;
	$root.off("click.inoutToggle");
	$root.on("click.inoutToggle", ".sp-inout-toggle__btn", function () {
		const value = $(this).data("value");
		if (!value || $(this).hasClass("is-active")) return;
		$root.find(".sp-inout-toggle__btn").removeClass("is-active");
		$(this).addClass("is-active");
		$root.find(".sp-inout-dash__status").val(value);
		on_change?.(value, $root);
	});
}

function inout_toggle_value($root) {
	return $root.find(".sp-inout-dash__status").val() || "IN";
}

function set_inout_toggle_value($root, value) {
	const selected = value === "OUT" ? "OUT" : "IN";
	$root.find(".sp-inout-toggle__btn").removeClass("is-active");
	$root.find(`.sp-inout-toggle__btn[data-value="${selected}"]`).addClass("is-active");
	$root.find(".sp-inout-dash__status").val(selected);
}

function leave_reason(row) {
	const leaveType = String(row?.leave_type || "").trim();
	if (leaveType) return leaveType;
	if (String(row?.attendance_status || "").trim() === "On Leave") return __("On Leave");
	return "";
}

function late_status_label(row) {
	const leave = leave_reason(row);
	if (leave) {
		return `${__("OUT")} - ${leave}`;
	}
	const status = row?.status === "IN" ? __("IN") : __("OUT");
	if (row?.late) {
		const lateBy = String(row.late_label || "").trim();
		return lateBy ? `${status} - ${lateBy} ${__("late")}` : `${status} - ${__("late")}`;
	}
	return status;
}

function inout_summary_table_html(rows, escape) {
	const esc = escape || escape_html;
	return `
		<table class="sp-inout-dash__summary-table">
			<thead>
				<tr>
					<th>${esc(__("Department"))}</th>
					<th>${esc(__("Employees"))}</th>
					<th>${esc(__("IN"))}</th>
					<th>${esc(__("OUT"))}</th>
					<th>${esc(__("Late"))}</th>
				</tr>
			</thead>
			<tbody>
				${rows
					.map(
						(row) => `
					<tr>
						<td>${esc(row.department || __("No Department"))}</td>
						<td>${Number(row.employees || 0)}</td>
						<td>${Number(row.in_count || 0)}</td>
						<td>${Number(row.out_count || 0)}</td>
						<td>${Number(row.late || 0)}</td>
					</tr>`,
					)
					.join("")}
			</tbody>
		</table>
	`;
}

hrms.ui.inout_toggle_html = inout_toggle_html;
hrms.ui.bind_inout_toggle = bind_inout_toggle;
hrms.ui.inout_toggle_value = inout_toggle_value;
hrms.ui.set_inout_toggle_value = set_inout_toggle_value;
hrms.ui.leave_reason = leave_reason;
hrms.ui.late_status_label = late_status_label;
hrms.ui.inout_summary_table_html = inout_summary_table_html;
