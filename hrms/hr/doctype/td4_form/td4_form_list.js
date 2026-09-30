frappe.listview_settings["TD4 Form"] = {
	onload(listview) {
		listview.page.clear_primary_action();
		render_td4_roster(listview);
	},
	refresh(listview) {
		listview.page.clear_primary_action();
		render_td4_roster(listview);
	},
};

function esc(value) {
	const text = cstr(value);
	if (frappe.utils && frappe.utils.escape_html) return frappe.utils.escape_html(text);
	return text
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;");
}

function cstr(value) {
	return value == null ? "" : String(value);
}

function render_td4_roster(listview) {
	const $section = listview.page.main.find(".layout-main-section");
	if (!$section.length) return;
	$section.find(".frappe-list").hide();
	let $roster = $section.find(".td4-roster");
	if (!$roster.length) {
		$roster = $(`<div class="td4-roster" style="padding: 12px 15px 24px;"></div>`);
		$section.find(".frappe-list").before($roster);
	}
	if (!$roster.data("loaded")) {
		$roster.html(`<div class="text-muted">${__("Loading agents...")}</div>`);
	}
	frappe.call({
		method: "hrms.hr.doctype.td4_form.td4_form.get_td4_roster",
		callback(response) {
			const rows = response.message || [];
			$roster.data("loaded", 1);
			if (!rows.length) {
				$roster.html(`<div class="text-muted text-center" style="padding: 48px 0;">${__("No active agents yet.")}</div>`);
				return;
			}
			const body = rows
				.map((row) => {
					const filled = row.filled
						? `<span class="indicator-pill green">${__("Filled")}</span>`
						: `<span class="indicator-pill orange">${__("Not filled")}</span>`;
					const who = row.filled ? esc(row.filled_by_name || row.filled_by || "") : "—";
					const when = row.filled ? esc(row.filled_on || row.date_signed || "") : "—";
					const open = row.form
						? `<a href="/desk/td4-form/${encodeURIComponent(row.form)}">${__("Open")}</a>`
						: "—";
					return `<tr>
						<td><a href="/desk/employee/${encodeURIComponent(row.employee)}">${esc(row.employee_name)}</a></td>
						<td>${esc(row.employee)}</td>
						<td>${filled}</td>
						<td>${who}</td>
						<td>${when}</td>
						<td>${open}</td>
					</tr>`;
				})
				.join("");
			$roster.html(`
				<table class="table table-bordered">
					<thead>
						<tr>
							<th>${__("Agent")}</th>
							<th>${__("ID")}</th>
							<th>${__("TD4")}</th>
							<th>${__("Filled by")}</th>
							<th>${__("Filled on")}</th>
							<th></th>
						</tr>
					</thead>
					<tbody>${body}</tbody>
				</table>
			`);
		},
	});
}
