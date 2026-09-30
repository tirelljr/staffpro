// Copyright (c) 2026, Staff Pro BPO and Contributors
// License: GNU General Public License v3. See license.txt

(function () {
	function access_groups() {
		const groups = frappe.boot && frappe.boot.staff_pro_access_groups;
		return groups && groups.length ? groups : [];
	}

	function ensure_styles() {
		if (document.getElementById("staff-pro-role-access-style")) return;
		const style = document.createElement("style");
		style.id = "staff-pro-role-access-style";
		style.textContent = `
			.staff-pro-access {
				margin: 8px 0 4px;
				max-width: 640px;
			}
			.modal .staff-pro-access {
				max-height: 62vh;
				overflow-y: auto;
				padding-right: 6px;
			}
			.staff-pro-access__section + .staff-pro-access__section {
				margin-top: 18px;
				padding-top: 16px;
				border-top: 1px solid var(--border-color, #e5e7eb);
			}
			.staff-pro-access__heading {
				font-size: 14px;
				font-weight: 600;
				color: var(--text-color, #171717);
				line-height: 1.3;
			}
			.staff-pro-access__intro {
				margin-top: 2px;
				margin-bottom: 10px;
				font-size: 13px;
				line-height: 1.4;
				color: var(--text-muted, #6b7280);
			}
			.staff-pro-access__row {
				display: flex;
				align-items: flex-start;
				gap: 12px;
				padding: 10px 0;
			}
			.staff-pro-access__row + .staff-pro-access__row {
				border-top: 1px solid var(--border-color, #f0f0f0);
			}
			.staff-pro-access__title {
				font-size: 14px;
				font-weight: 600;
				color: var(--text-color, #171717);
				line-height: 1.3;
			}
			.staff-pro-access__desc {
				margin-top: 2px;
				font-size: 13px;
				line-height: 1.4;
				color: var(--text-muted, #6b7280);
			}
			.staff-pro-switch {
				position: relative;
				flex: 0 0 auto;
				width: 40px;
				height: 24px;
				margin-top: 1px;
				padding: 0;
				border: 0;
				border-radius: 999px;
				background: #e5e7eb;
				cursor: pointer;
				transition: background 0.15s ease;
			}
			.staff-pro-switch.is-on {
				background: #2f6fed;
			}
			.staff-pro-switch__knob {
				position: absolute;
				top: 3px;
				left: 3px;
				width: 18px;
				height: 18px;
				border-radius: 50%;
				background: #fff;
				box-shadow: 0 1px 2px rgba(0, 0, 0, 0.18);
				transition: transform 0.15s ease;
			}
			.staff-pro-switch.is-on .staff-pro-switch__knob {
				transform: translateX(16px);
			}
			.staff-pro-switch:focus-visible {
				outline: 2px solid #2f6fed;
				outline-offset: 2px;
			}
		`;
		(document.head || document.documentElement).appendChild(style);
	}

	function switch_on(doc, fieldname) {
		const value = doc ? doc[fieldname] : null;
		if (value === undefined || value === null || value === "") return true;
		return value === 1 || value === true || value === "1";
	}

	function read_switches($root) {
		const access = {};
		$root.find(".staff-pro-switch").each(function () {
			const fieldname = this.getAttribute("data-fieldname");
			if (fieldname) access[fieldname] = this.classList.contains("is-on") ? 1 : 0;
		});
		return access;
	}

	function render($parent, doc, on_change) {
		ensure_styles();
		const $host = $('<div class="staff-pro-access">');
		access_groups().forEach((group) => {
			const $section = $('<div class="staff-pro-access__section">').appendTo($host);
			$section.append(`<div class="staff-pro-access__heading">${frappe.utils.escape_html(group.title)}</div>`);
			$section.append(`<div class="staff-pro-access__intro">${frappe.utils.escape_html(group.intro)}</div>`);
			group.flags.forEach((flag) => {
				const on = switch_on(doc, flag.fieldname);
				const $row = $(`
					<div class="staff-pro-access__row">
						<button type="button" class="staff-pro-switch ${on ? "is-on" : ""}" role="switch"
							aria-checked="${on ? "true" : "false"}" data-fieldname="${frappe.utils.escape_html(flag.fieldname)}">
							<span class="staff-pro-switch__knob"></span>
						</button>
						<div>
							<div class="staff-pro-access__title">${frappe.utils.escape_html(flag.label)}</div>
							<div class="staff-pro-access__desc">${frappe.utils.escape_html(flag.description)}</div>
						</div>
					</div>
				`);
				$row.find(".staff-pro-switch").on("click", function () {
					const next = !this.classList.contains("is-on");
					this.classList.toggle("is-on", next);
					this.setAttribute("aria-checked", next ? "true" : "false");
					if (on_change) on_change(flag.fieldname, next ? 1 : 0, read_switches($host));
				});
				$section.append($row);
			});
		});
		$parent.empty().append($host);
		return $host;
	}

	function render_section($parent, section, on_change) {
		ensure_styles();
		const $host = $('<div class="staff-pro-access">');
		const $section = $('<div class="staff-pro-access__section">').appendTo($host);
		if (section.title) {
			$section.append(
				`<div class="staff-pro-access__heading">${frappe.utils.escape_html(section.title)}</div>`,
			);
		}
		if (section.intro) {
			$section.append(
				`<div class="staff-pro-access__intro">${frappe.utils.escape_html(section.intro)}</div>`,
			);
		}
		(section.rows || []).forEach((row) => {
			const on = !!row.on;
			const $row = $(`
				<div class="staff-pro-access__row">
					<button type="button" class="staff-pro-switch ${on ? "is-on" : ""}" role="switch"
						aria-checked="${on ? "true" : "false"}" data-fieldname="${frappe.utils.escape_html(row.id)}">
						<span class="staff-pro-switch__knob"></span>
					</button>
					<div>
						<div class="staff-pro-access__title">${frappe.utils.escape_html(row.label)}</div>
						<div class="staff-pro-access__desc">${frappe.utils.escape_html(row.description || "")}</div>
					</div>
				</div>
			`);
			$row.find(".staff-pro-switch").on("click", function () {
				const next = !this.classList.contains("is-on");
				this.classList.toggle("is-on", next);
				this.setAttribute("aria-checked", next ? "true" : "false");
				if (on_change) on_change(row.id, next ? 1 : 0, read_switches($host));
			});
			$section.append($row);
		});
		$parent.empty().append($host);
		return $host;
	}

	function can(flag) {
		const access = frappe.boot?.staff_pro_access;
		if (!access || !(flag in access)) return true;
		return !!access[flag];
	}

	function hide_role_chrome(frm) {
		["home_page", "restrict_to_domain", "two_factor_auth"].forEach((fieldname) => {
			if (frm.fields_dict?.[fieldname]) frm.set_df_property(fieldname, "hidden", 1);
		});
		const hidden = new Set(["Documents", "Reports", "Pages", "Workspaces"]);
		const $nav = $(frm.page?.wrapper || frm.$wrapper).find("#form-tabs");
		$nav.find("li, .nav-item").each(function () {
			const label = ($(this).text() || "").replace(/\s+/g, " ").trim();
			if (hidden.has(label)) $(this).hide();
		});
	}

	function mount_role_form(frm) {
		hide_role_chrome(frm);
		const $anchor = frm.fields_dict?.role_name?.$wrapper;
		if (!$anchor?.length) return;
		let $host = $anchor.next(".staff-pro-access-host");
		if (!$host.length) {
			$host = $('<div class="staff-pro-access-host">').insertAfter($anchor);
		}
		if (frm.is_new()) {
			access_groups().forEach((group) => {
				group.flags.forEach((flag) => {
					if (frm.doc[flag.fieldname] == null) frm.doc[flag.fieldname] = 1;
				});
			});
		}
		render($host, frm.doc, (fieldname, value) => {
			frm.doc[fieldname] = value;
			if (frm.fields_dict[fieldname]) {
				frm.set_value(fieldname, value);
			} else {
				frm.dirty();
			}
		});
	}

	function watch_role_form(frm) {
		const nav = $(frm.page?.wrapper || frm.$wrapper).find("#form-tabs").get(0);
		if (!nav || nav._staffProRoleAccess) return;
		nav._staffProRoleAccess = true;
		new MutationObserver(() => hide_role_chrome(frm)).observe(nav, { childList: true, subtree: true });
	}

	function attach_quick_entry($modal) {
		const $body = $modal.find(".modal-body").first();
		if (!$body.length || $body.find(".staff-pro-access").length) return;
		if (!$body.find('[data-fieldname="role_name"]').length) return;
		const $anchor = $body.find('[data-fieldname="role_name"]').first();
		const $host = $('<div class="staff-pro-access-host">');
		$anchor.after($host);
		const doc = {};
		render($host, doc, (_field, _value, access) => {
			window._staff_pro_role_access = access;
		});
		window._staff_pro_role_access = read_switches($host);
		$modal.on("hidden.bs.modal", () => {
			window._staff_pro_role_access = null;
		});
		const dialog = $modal.closest(".modal-dialog");
		dialog.css("max-width", "720px");
	}

	function watch_new_role_modal() {
		$(document).on("shown.bs.modal", ".modal", function () {
			const $modal = $(this);
			const title = ($modal.find(".modal-title, .title-section").first().text() || "").replace(/\s+/g, " ").trim();
			if (title !== __("New Role") && title !== "New Role") return;
			attach_quick_entry($modal);
		});
	}

	function patch_role_save() {
		if (!frappe.call || frappe.call._staffProRoleAccess) return;
		const original = frappe.call.bind(frappe);
		function wrapped(opts, ...rest) {
			const access = window._staff_pro_role_access;
			const method = opts && opts.method;
			if (access && opts?.args && (method === "frappe.client.insert" || method === "frappe.client.save" || method === "frappe.desk.form.save.savedocs")) {
				merge_role_doc(opts.args, access);
			}
			return original(opts, ...rest);
		}
		wrapped._staffProRoleAccess = true;
		frappe.call = wrapped;
	}

	function merge_role_doc(args, access) {
		if (!args || args.doc == null) return;
		let doc = args.doc;
		let encoded = false;
		if (typeof doc === "string") {
			try {
				doc = JSON.parse(doc);
				encoded = true;
			} catch (e) {
				return;
			}
		}
		if (!doc || doc.doctype !== "Role") return;
		Object.assign(doc, access);
		args.doc = encoded ? JSON.stringify(doc) : doc;
	}

	function route_blocked(route) {
		const blocks = frappe.boot?.staff_pro_access_blocks;
		if (!blocks) return false;
		const kind = route[0];
		const name = route[1];
		const match = (list) =>
			(list || []).some((item) => String(item).toLowerCase() === String(name || "").toLowerCase());
		if ((kind === "List" || kind === "Form" || kind === "Tree" || kind === "new-doc") && match(blocks.doctypes)) {
			return true;
		}
		if ((kind === "query-report" || kind === "Report") && match(blocks.reports)) return true;
		if (kind === "dashboard-view" && match(blocks.dashboards)) return true;
		if ((kind === "Workspaces" || kind === "workspace") && match(blocks.workspaces)) return true;
		if (kind === "page" && match(blocks.pages)) return true;
		const joined = (route || []).join("/").toLowerCase();
		const here = `${location.pathname}${location.search}`.toLowerCase();
		if ((blocks.pages || []).some((item) => joined.includes(String(item).toLowerCase()))) return true;
		if (
			(blocks.urls || []).some((item) => {
				const part = String(item).toLowerCase();
				return joined.includes(part) || here.includes(part);
			})
		) {
			return true;
		}
		return false;
	}

	function guard_route() {
		if (!frappe.get_route || window._staff_pro_access_redirecting) return;
		const route = frappe.get_route() || [];
		if (!route_blocked(route)) return;
		window._staff_pro_access_redirecting = true;
		frappe.show_alert({
			message: __("You don't have access to that"),
			indicator: "orange",
		});
		const home = frappe.boot?.staff_pro_desk_home;
		const target = Array.isArray(home) && home.length ? home : ["dashboard-view", "Human Resource"];
		Promise.resolve(frappe.set_route(...target)).finally(() => {
			window._staff_pro_access_redirecting = false;
		});
	}

	const USER_ACTION_LABELS = new Set(["Impersonate", "Create User Email", "Reset Password"]);

	function strip_user_buttons(root) {
		if (!root) return;
		$(root)
			.find("button, a")
			.each(function () {
				const raw = $(this).attr("data-label") || "";
				let label = raw;
				try {
					label = decodeURIComponent(raw.replace(/\+/g, " "));
				} catch (e) {
					label = raw;
				}
				const text = ($(this).text() || "").replace(/\s+/g, " ").trim();
				if (USER_ACTION_LABELS.has(label) || USER_ACTION_LABELS.has(text)) {
					$(this).remove();
				}
			});
	}

	let started = false;

	function start() {
		if (started) return;
		started = true;
		ensure_styles();
		patch_role_save();
		watch_new_role_modal();
		guard_route();
	}

	frappe.provide("hrms.role_access");
	hrms.role_access.can = can;
	hrms.role_access.ensure_styles = ensure_styles;
	hrms.role_access.render_section = render_section;
	hrms.role_access.mount_role_form = mount_role_form;
	hrms.role_access.watch_role_form = watch_role_form;
	hrms.role_access.hide_role_chrome = hide_role_chrome;
	hrms.role_access.strip_user_buttons = strip_user_buttons;

	$(document).on("app_ready", start);
	if (window.frappe?.boot) start();
	$(document).on("page-change", () => {
		guard_route();
		if ((frappe.get_route?.() || [])[1] === "User" || (frappe.get_route?.() || [])[0] === "user") {
			strip_user_buttons(document.getElementById("page-User") || document.body);
		}
	});
})();
