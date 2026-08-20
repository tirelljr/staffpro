frappe.provide("hrms.ui");

const TOPBAR_CSS = `
header.staff-pro-topbar {
	display: block !important;
	box-sizing: border-box !important;
	width: 100% !important;
	height: 56px !important;
	min-height: 56px !important;
	max-height: 56px !important;
	margin: 0 !important;
	padding: 0 !important;
	overflow: visible !important;
	background: #ffffff !important;
	border: 0 !important;
	border-bottom: 1px solid #ececec !important;
	box-shadow: none !important;
	flex: 0 0 56px !important;
}
.staff-pro-topbar *,
.staff-pro-topbar *::before,
.staff-pro-topbar *::after {
	box-sizing: border-box !important;
}
.staff-pro-topbar__inner {
	display: flex !important;
	flex-direction: row !important;
	flex-wrap: nowrap !important;
	align-items: center !important;
	justify-content: space-between !important;
	width: 100% !important;
	height: 56px !important;
	padding: 0 16px !important;
	gap: 16px !important;
	overflow: visible !important;
	position: relative !important;
}
.staff-pro-topbar__left {
	display: flex !important;
	flex-direction: column !important;
	justify-content: center !important;
	min-width: 140px !important;
	max-width: 220px !important;
	flex: 0 1 180px !important;
}
.staff-pro-topbar__id {
	font-size: 11px !important;
	font-weight: 500 !important;
	letter-spacing: 0.08em !important;
	text-transform: uppercase !important;
	color: #9ca3af !important;
	line-height: 1.2 !important;
	white-space: nowrap !important;
	overflow: hidden !important;
	text-overflow: ellipsis !important;
}
.staff-pro-topbar__status {
	display: flex !important;
	flex-direction: row !important;
	align-items: center !important;
	gap: 8px !important;
	font-size: 14px !important;
	font-weight: 700 !important;
	color: #111827 !important;
	line-height: 1.2 !important;
}
.staff-pro-topbar__status-dot {
	width: 8px !important;
	height: 8px !important;
	border-radius: 50% !important;
	background: #11a5dd !important;
	flex-shrink: 0 !important;
}
.staff-pro-topbar__center {
	display: flex !important;
	flex-direction: row !important;
	align-items: center !important;
	justify-content: center !important;
	flex: 1 1 auto !important;
	min-width: 0 !important;
	position: relative !important;
	left: auto !important;
	top: auto !important;
	transform: none !important;
	overflow: visible !important;
	pointer-events: auto !important;
	width: auto !important;
	max-width: none !important;
}
.staff-pro-topbar__search-wrap {
	position: relative !important;
	width: 320px !important;
	max-width: 100% !important;
	overflow: visible !important;
	flex-shrink: 0 !important;
}
.staff-pro-topbar__search {
	display: flex !important;
	flex-direction: row !important;
	align-items: center !important;
	gap: 10px !important;
	width: 100% !important;
	height: 36px !important;
	margin: 0 !important;
	padding: 0 10px 0 14px !important;
	border: 0 !important;
	border-radius: 999px !important;
	background: #f3f4f6 !important;
	box-shadow: none !important;
	cursor: text !important;
	color: #9ca3af !important;
	font: inherit !important;
	line-height: 1 !important;
	appearance: none !important;
	-webkit-appearance: none !important;
}
.staff-pro-topbar__search.is-open {
	background: #eceef1 !important;
	box-shadow: 0 0 0 1px #e5e7eb !important;
}
.staff-pro-topbar__search .icon,
.staff-pro-topbar__search svg {
	width: 15px !important;
	height: 15px !important;
	stroke: #9ca3af !important;
	flex-shrink: 0 !important;
}
.staff-pro-topbar__search-input,
.staff-pro-topbar__search-field {
	flex: 1 1 auto !important;
	min-width: 0 !important;
	height: 100% !important;
	margin: 0 !important;
	padding: 0 !important;
	border: 0 !important;
	outline: none !important;
	background: transparent !important;
	box-shadow: none !important;
	font-size: 13px !important;
	font-weight: 400 !important;
	color: #111827 !important;
	line-height: 36px !important;
	appearance: none !important;
	-webkit-appearance: none !important;
}
.staff-pro-topbar__search-input::placeholder,
.staff-pro-topbar__search-field::placeholder {
	color: #9ca3af !important;
	opacity: 1 !important;
}
.staff-pro-topbar__search-placeholder {
	flex: 1 1 auto !important;
	font-size: 13px !important;
	font-weight: 400 !important;
	color: #9ca3af !important;
	white-space: nowrap !important;
	overflow: hidden !important;
	text-overflow: ellipsis !important;
	text-align: left !important;
}
.staff-pro-topbar__search-panel {
	position: fixed !important;
	z-index: 2000 !important;
	width: min(480px, calc(100vw - 24px)) !important;
	max-height: min(420px, calc(100vh - 80px)) !important;
	display: flex !important;
	flex-direction: column !important;
	margin: 0 !important;
	border-radius: 12px !important;
	background: #fff !important;
	border: 1px solid #eef0f2 !important;
	box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12) !important;
	pointer-events: auto !important;
	overflow: hidden !important;
}
.staff-pro-topbar__search-panel.hidden {
	display: none !important;
}
.staff-pro-topbar__search-panel-field {
	display: none !important;
	align-items: center !important;
	gap: 10px !important;
	padding: 10px 12px !important;
	border-bottom: 1px solid #eef0f2 !important;
}
.staff-pro-topbar__search-panel-field .icon,
.staff-pro-topbar__search-panel-field svg {
	width: 15px !important;
	height: 15px !important;
	stroke: #9ca3af !important;
	flex-shrink: 0 !important;
}
.staff-pro-topbar__search-results {
	flex: 1 1 auto !important;
	min-height: 0 !important;
	overflow-y: auto !important;
	padding: 6px !important;
}
.staff-pro-topbar__search-item {
	display: flex !important;
	flex-direction: column !important;
	align-items: flex-start !important;
	gap: 2px !important;
	width: 100% !important;
	padding: 8px 10px !important;
	border: 0 !important;
	border-radius: 8px !important;
	background: transparent !important;
	text-align: left !important;
	cursor: pointer !important;
	color: #111827 !important;
}
.staff-pro-topbar__search-item:hover,
.staff-pro-topbar__search-item.is-active {
	background: #f3f4f6 !important;
}
.staff-pro-topbar__search-item-label {
	font-size: 13px !important;
	font-weight: 500 !important;
	line-height: 1.35 !important;
	color: #111827 !important;
}
.staff-pro-topbar__search-item-label b,
.staff-pro-topbar__search-item-label mark,
.staff-pro-topbar__search-item-label strong {
	font-weight: 700 !important;
	background: transparent !important;
	color: #11a5dd !important;
}
.staff-pro-topbar__search-item-meta {
	font-size: 11px !important;
	color: #9ca3af !important;
	line-height: 1.3 !important;
}
.staff-pro-topbar__search-empty {
	display: flex !important;
	align-items: center !important;
	justify-content: center !important;
	min-height: 88px !important;
	padding: 16px !important;
	font-size: 13px !important;
	color: #6b7280 !important;
	text-align: center !important;
}
.staff-pro-topbar__search-footer {
	display: flex !important;
	flex-wrap: wrap !important;
	align-items: center !important;
	gap: 10px 14px !important;
	padding: 8px 12px !important;
	border-top: 1px solid #eef0f2 !important;
	background: #fafafa !important;
	font-size: 11px !important;
	color: #6b7280 !important;
}
.staff-pro-topbar__search-hint {
	display: inline-flex !important;
	align-items: center !important;
	gap: 4px !important;
	white-space: nowrap !important;
}
.staff-pro-topbar__search-hint kbd,
.staff-pro-topbar__search-hint .staff-pro-topbar__search-key {
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	min-width: 18px !important;
	height: 18px !important;
	padding: 0 4px !important;
	border-radius: 4px !important;
	background: #fff !important;
	border: 1px solid #e5e7eb !important;
	font-size: 10px !important;
	font-weight: 600 !important;
	color: #6b7280 !important;
}
.staff-pro-topbar__shortcut {
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	height: 20px !important;
	padding: 0 6px !important;
	border-radius: 4px !important;
	background: #ffffff !important;
	border: 1px solid #e5e7eb !important;
	box-shadow: none !important;
	font-size: 10px !important;
	font-weight: 600 !important;
	color: #9ca3af !important;
	flex-shrink: 0 !important;
}
.staff-pro-topbar__right {
	display: flex !important;
	flex-direction: row !important;
	align-items: center !important;
	justify-content: flex-end !important;
	gap: 8px !important;
	flex: 0 0 auto !important;
}
.staff-pro-topbar__icon-btn,
.staff-pro-topbar__avatar {
	display: inline-flex !important;
	flex-direction: row !important;
	align-items: center !important;
	justify-content: center !important;
	width: 36px !important;
	height: 36px !important;
	margin: 0 !important;
	padding: 0 !important;
	border: 0 !important;
	border-radius: 50% !important;
	background: #f3f4f6 !important;
	box-shadow: none !important;
	cursor: pointer !important;
	appearance: none !important;
	-webkit-appearance: none !important;
	color: #111827 !important;
	position: relative !important;
}
.staff-pro-topbar__icon-btn .icon,
.staff-pro-topbar__icon-btn svg {
	width: 16px !important;
	height: 16px !important;
	stroke: #111827 !important;
}
.staff-pro-topbar__lang {
	font-size: 11px !important;
	font-weight: 700 !important;
	letter-spacing: 0.02em !important;
}
.staff-pro-topbar__badge {
	position: absolute !important;
	top: -3px !important;
	right: -3px !important;
	min-width: 16px !important;
	height: 16px !important;
	padding: 0 4px !important;
	border-radius: 999px !important;
	background: #111827 !important;
	color: #fff !important;
	font-size: 9px !important;
	font-weight: 700 !important;
	line-height: 16px !important;
	text-align: center !important;
}
.staff-pro-topbar__avatar .avatar,
.staff-pro-topbar__avatar .avatar-frame {
	width: 36px !important;
	height: 36px !important;
	border-radius: 50% !important;
}
.staff-pro-topbar__lang-wrap { position: relative !important; }
.staff-pro-topbar__lang.is-open {
	background: #eceef1 !important;
}
.staff-pro-topbar__menu {
	position: fixed !important;
	z-index: 1050 !important;
	min-width: 140px !important;
	padding: 4px !important;
	border-radius: 12px !important;
	background: #fff !important;
	border: 1px solid #eef0f2 !important;
	box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12) !important;
}
.staff-pro-topbar__menu-item {
	display: block !important;
	width: 100% !important;
	padding: 8px 12px !important;
	border: 0 !important;
	border-radius: 8px !important;
	background: transparent !important;
	text-align: left !important;
	font-size: 13px !important;
	color: #111827 !important;
	cursor: pointer !important;
}
.staff-pro-topbar__menu-item:hover,
.staff-pro-topbar__menu-item.is-active {
	background: #f3f4f6 !important;
}
.staff-pro-topbar__menu-item.is-active {
	font-weight: 600 !important;
}
.staff-pro-topbar__notifications-wrap { position: relative !important; }
.staff-pro-topbar__icon-btn.is-open {
	background: #eceef1 !important;
}
.staff-pro-topbar__notifications-panel {
	position: fixed !important;
	z-index: 1050 !important;
	width: min(360px, calc(100vw - 24px)) !important;
	max-height: min(480px, calc(100vh - 80px)) !important;
	display: flex !important;
	flex-direction: column !important;
	border-radius: 12px !important;
	background: #fff !important;
	border: 1px solid #eef0f2 !important;
	box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12) !important;
	overflow: hidden !important;
}
.staff-pro-topbar__notifications-panel.hidden,
.staff-pro-topbar__menu.hidden {
	display: none !important;
}
.staff-pro-topbar__notifications-backdrop {
	position: fixed !important;
	inset: 0 !important;
	z-index: 1049 !important;
	background: transparent !important;
}
.staff-pro-topbar__notifications-backdrop.hidden {
	display: none !important;
}
.staff-pro-topbar__notifications-header {
	display: flex !important;
	align-items: center !important;
	justify-content: space-between !important;
	gap: 12px !important;
	padding: 12px 14px !important;
	border-bottom: 1px solid #eef0f2 !important;
}
.staff-pro-topbar__notifications-title {
	font-size: 14px !important;
	font-weight: 700 !important;
	color: #111827 !important;
}
.staff-pro-topbar__notifications-actions {
	display: flex !important;
	align-items: center !important;
	gap: 4px !important;
}
.staff-pro-topbar__notifications-action {
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	width: 28px !important;
	height: 28px !important;
	border: 0 !important;
	border-radius: 8px !important;
	background: transparent !important;
	color: #6b7280 !important;
	cursor: pointer !important;
}
.staff-pro-topbar__notifications-action:hover {
	background: #f3f4f6 !important;
	color: #111827 !important;
}
.staff-pro-topbar__notifications-body {
	flex: 1 1 auto !important;
	min-height: 0 !important;
	overflow-y: auto !important;
}
.staff-pro-topbar__notification-item {
	display: flex !important;
	align-items: flex-start !important;
	gap: 10px !important;
	width: 100% !important;
	padding: 12px 14px !important;
	border: 0 !important;
	border-bottom: 1px solid #f3f4f6 !important;
	background: transparent !important;
	text-align: left !important;
	cursor: pointer !important;
}
.staff-pro-topbar__notification-item:hover {
	background: #f9fafb !important;
}
.staff-pro-topbar__notification-item.is-unread {
	background: #f8fbff !important;
}
.staff-pro-topbar__notification-item .avatar {
	width: 32px !important;
	height: 32px !important;
	flex-shrink: 0 !important;
}
.staff-pro-topbar__notification-content {
	flex: 1 1 auto !important;
	min-width: 0 !important;
}
.staff-pro-topbar__notification-message {
	font-size: 13px !important;
	line-height: 1.4 !important;
	color: #111827 !important;
}
.staff-pro-topbar__notification-time {
	margin-top: 4px !important;
	font-size: 11px !important;
	color: #9ca3af !important;
}
.staff-pro-topbar__notifications-empty,
.staff-pro-topbar__notifications-loading {
	display: flex !important;
	align-items: center !important;
	justify-content: center !important;
	min-height: 180px !important;
	padding: 24px 16px !important;
	font-size: 13px !important;
	color: #6b7280 !important;
	text-align: center !important;
}
.staff-pro-topbar__notifications-footer {
	padding: 10px 14px !important;
	border-top: 1px solid #eef0f2 !important;
}
.staff-pro-topbar__notifications-footer-btn {
	display: block !important;
	width: 100% !important;
	padding: 8px 12px !important;
	border: 0 !important;
	border-radius: 8px !important;
	background: transparent !important;
	text-align: center !important;
	font-size: 13px !important;
	font-weight: 600 !important;
	color: #11a5dd !important;
	cursor: pointer !important;
}
.staff-pro-topbar__notifications-footer-btn:hover {
	background: #f3f4f6 !important;
}
.staff-pro-topbar__search-toggle { display: none !important; }
body.staff-pro-has-topbar .modal:has(.cool-awesomebar-modal-footer),
body.staff-pro-has-topbar .modal:has(.navbar-modal-wrapper) {
	display: none !important;
}
body.staff-pro-has-topbar.staff-pro-search-open,
body.staff-pro-has-topbar.staff-pro-search-open.modal-open {
	overflow: auto !important;
	padding-right: 0 !important;
}
body.staff-pro-has-topbar.staff-pro-search-open .modal-backdrop {
	display: none !important;
	opacity: 0 !important;
}
@media (max-width: 767px) {
	.staff-pro-topbar__center { display: none !important; }
	.staff-pro-topbar__search-toggle { display: inline-flex !important; }
	.staff-pro-topbar__search-toggle.is-open { background: #eceef1 !important; }
	.staff-pro-topbar__search-panel-field { display: flex !important; }
	.staff-pro-topbar__lang { display: none !important; }
}
`;

hrms.ui.TopBar = class {
	constructor() {
		this.$wrapper = null;
		this.language_open = false;
		this.notifications_open = false;
		this.search_open = false;
		this.search_items = [];
		this.search_index = -1;
		this.search_seq = 0;
		this.notifications_loaded = false;
		this.notifications_loading = false;
		this.notification_items = [];
		this.bound = false;
		this.on_reposition_menu = () => {
			this.position_language_menu();
			this.position_notifications_panel();
			this.position_search_panel();
		};
		this.inject_css();
		this.make();
	}

	inject_css() {
		let style = document.getElementById("staff-pro-topbar-css");
		if (!style) {
			style = document.createElement("style");
			style.id = "staff-pro-topbar-css";
			document.head.appendChild(style);
		}
		style.textContent = TOPBAR_CSS;
	}

	make() {
		if (document.querySelector(".staff-pro-topbar")) {
			this.$wrapper = $(".staff-pro-topbar");
			this.after_mount();
			return;
		}

		const $main = $(".main-section").first();
		if (!$main.length) {
			setTimeout(() => this.make(), 100);
			return;
		}

		this.$wrapper = $(this.template());
		$main.prepend(this.$wrapper);
		$("body").addClass("staff-pro-has-topbar");
		this.after_mount();
	}

	after_mount() {
		if (!this.$wrapper) return;
		this.ensure_language_picker();
		this.ensure_notifications_picker();
		this.ensure_search_picker();
		this.patch_native_awesomebar();
		this.bind();
		this.refresh_context();
		this.refresh_notifications();
	}

	search_shortcut_label() {
		if (frappe.ui.keys?.get_shortcut_label) {
			return frappe.ui.keys.get_shortcut_label("ctrl+k");
		}
		return frappe.utils.is_mac() ? "⌘K" : "Ctrl+K";
	}

	global_search_shortcut_label() {
		if (frappe.ui.keys?.get_shortcut_label) {
			return frappe.ui.keys.get_shortcut_label("ctrl+g");
		}
		return frappe.utils.is_mac() ? "⌘G" : "Ctrl+G";
	}

	search_footer_html() {
		const close_key = frappe.utils.escape_html(this.search_shortcut_label());
		const global_key = frappe.utils.escape_html(this.global_search_shortcut_label());
		return `
			<span class="staff-pro-topbar__search-hint">
				<span class="staff-pro-topbar__search-key">↑</span>
				<span class="staff-pro-topbar__search-key">↓</span>
				${__("to navigate")}
			</span>
			<span class="staff-pro-topbar__search-hint">
				<span class="staff-pro-topbar__search-key">↵</span>
				${__("to select")}
			</span>
			<span class="staff-pro-topbar__search-hint">
				<span class="staff-pro-topbar__search-key">${close_key}</span>
				${__("to close")}
			</span>
			<span class="staff-pro-topbar__search-hint">
				<span class="staff-pro-topbar__search-key">${global_key}</span>
				${__("to open Global Search")}
			</span>
		`;
	}

	search_panel() {
		const $body_panel = $("body > .staff-pro-topbar__search-panel");
		if ($body_panel.length) return $body_panel.first();
		return $(".staff-pro-topbar__search-panel").first();
	}

	search_fields() {
		return this.$wrapper
			.find(".staff-pro-topbar__search-field")
			.add(this.search_panel().find(".staff-pro-topbar__search-field"));
	}

	mount_search_panel() {
		const $nested = this.$wrapper.find(".staff-pro-topbar__search-panel");
		let $panel = $("body > .staff-pro-topbar__search-panel").first();
		if (!$panel.length && $nested.length) {
			$panel = $nested.first();
		}
		if (!$panel.length) {
			$panel = $(`
				<div class="staff-pro-topbar__search-panel hidden" role="listbox" aria-label="${__("Search")}">
					<div class="staff-pro-topbar__search-panel-field">
						${frappe.utils.icon("search", "sm")}
						<input class="staff-pro-topbar__search-field" type="text" autocomplete="off" spellcheck="false" placeholder="${__("Search employees, payroll, knowledge, help")}" aria-label="${__("Search")}" />
					</div>
					<div class="staff-pro-topbar__search-results"></div>
					<div class="staff-pro-topbar__search-footer"></div>
				</div>
			`);
		}
		$nested.not($panel).remove();
		if (!$panel.parent().is("body")) {
			$("body").append($panel);
		}
		$panel.find(".staff-pro-topbar__search-footer").html(this.search_footer_html());
		this.bind_search_panel_events($panel);
		return $panel;
	}

	bind_search_panel_events($panel) {
		$panel.off(".staff-pro-search");
		$panel.on("click.staff-pro-search", (e) => {
			e.stopPropagation();
		});
		$panel.on("input.staff-pro-search", ".staff-pro-topbar__search-field", (e) => {
			this.sync_search_fields(e.currentTarget.value);
			this.schedule_search(e.currentTarget.value);
		});
		$panel.on("keydown.staff-pro-search", ".staff-pro-topbar__search-field", (e) => {
			this.on_search_keydown(e);
		});
		$panel.on("click.staff-pro-search", ".staff-pro-topbar__search-item", (e) => {
			e.preventDefault();
			e.stopPropagation();
			this.select_search_item(cint($(e.currentTarget).attr("data-index")));
		});
		$panel.on("mouseenter.staff-pro-search", ".staff-pro-topbar__search-item", (e) => {
			this.set_search_index(cint($(e.currentTarget).attr("data-index")));
		});
	}

	ensure_search_picker() {
		const shortcut = frappe.utils.escape_html(this.search_shortcut_label());
		let $wrap = this.$wrapper.find(".staff-pro-topbar__search-wrap");
		const $old = this.$wrapper.find(".staff-pro-topbar__search").first();

		if (!$wrap.length) {
			const picker = $(`
				<div class="staff-pro-topbar__search-wrap">
					<div class="staff-pro-topbar__search" data-action="search" role="combobox" aria-expanded="false" aria-haspopup="listbox">
						${frappe.utils.icon("search", "sm")}
						<input class="staff-pro-topbar__search-input staff-pro-topbar__search-field" type="text" autocomplete="off" spellcheck="false" placeholder="${__("Search employees, payroll, knowledge, help")}" aria-label="${__("Search")}" />
						<kbd class="staff-pro-topbar__shortcut">${shortcut}</kbd>
					</div>
				</div>
			`);
			if ($old.length) {
				$old.replaceWith(picker);
			} else {
				this.$wrapper.find(".staff-pro-topbar__center").append(picker);
			}
			$wrap = this.$wrapper.find(".staff-pro-topbar__search-wrap");
		}

		if (!$wrap.find(".staff-pro-topbar__search-input").length) {
			$wrap.find(".staff-pro-topbar__search-placeholder").replaceWith(
				`<input class="staff-pro-topbar__search-input staff-pro-topbar__search-field" type="text" autocomplete="off" spellcheck="false" placeholder="${__("Search employees, payroll, knowledge, help")}" aria-label="${__("Search")}" />`
			);
		}

		$wrap.find(".staff-pro-topbar__search").attr({
			role: "combobox",
			"aria-expanded": "false",
			"aria-haspopup": "listbox",
		});
		this.mount_search_panel();
	}

	ensure_notifications_picker() {
		let $wrap = this.$wrapper.find(".staff-pro-topbar__notifications-wrap");
		const $existingBtn = this.$wrapper.find("[data-action='notifications']").first();

		if (!$("body .staff-pro-topbar__notifications-backdrop").length) {
			$("body").append(
				`<div class="staff-pro-topbar__notifications-backdrop hidden" data-action="notifications-backdrop" aria-hidden="true"></div>`
			);
		}

		if (!$wrap.length) {
			const $right = this.$wrapper.find(".staff-pro-topbar__right");
			const badge = $existingBtn.find(".staff-pro-topbar__badge").first().prop("outerHTML") ||
				`<span class="staff-pro-topbar__badge hidden">0</span>`;
			const picker = $(`
				<div class="staff-pro-topbar__notifications-wrap">
					<div class="staff-pro-topbar__icon-btn" data-action="notifications" role="button" tabindex="0" title="${__("Notifications")}" aria-haspopup="dialog" aria-expanded="false" aria-label="${__("Notifications")}">
						${frappe.utils.icon("bell", "sm")}
						${badge}
					</div>
					<div class="staff-pro-topbar__notifications-panel hidden" role="dialog" aria-label="${__("Notifications")}"></div>
				</div>
			`);
			if ($existingBtn.length) {
				$existingBtn.replaceWith(picker);
			} else {
				$right.prepend(picker);
			}
			$wrap = this.$wrapper.find(".staff-pro-topbar__notifications-wrap");
		}

		if (!$wrap.find(".staff-pro-topbar__notifications-panel").length) {
			$wrap.append(`<div class="staff-pro-topbar__notifications-panel hidden" role="dialog" aria-label="${__("Notifications")}"></div>`);
		}

		const $btn = $wrap.find("[data-action='notifications']");
		if ($btn.length && !$btn.attr("aria-haspopup")) {
			$btn.attr({
				"aria-haspopup": "dialog",
				"aria-expanded": "false",
				"aria-label": __("Notifications"),
			});
		}
	}

	ensure_language_picker() {
		const $wrap = this.$wrapper.find(".staff-pro-topbar__lang-wrap");
		if (!$wrap.length) {
			const lang = this.language_label();
			const $right = this.$wrapper.find(".staff-pro-topbar__right");
			const $avatar = $right.find(".staff-pro-topbar__avatar").first();
			const picker = $(`
				<div class="staff-pro-topbar__lang-wrap">
					<div class="staff-pro-topbar__icon-btn staff-pro-topbar__lang" data-action="language" role="button" tabindex="0" title="${__("Language")}" aria-haspopup="listbox" aria-expanded="false" aria-label="${__("Change language")}">
						${frappe.utils.escape_html(lang)}
					</div>
					<div class="staff-pro-topbar__menu hidden" role="listbox" aria-label="${__("Language")}"></div>
				</div>
			`);
			if ($avatar.length) {
				$avatar.before(picker);
			} else {
				$right.append(picker);
			}
			return;
		}

		if (!$wrap.find(".staff-pro-topbar__menu").length) {
			$wrap.append(`<div class="staff-pro-topbar__menu hidden" role="listbox" aria-label="${__("Language")}"></div>`);
		}

		const $btn = $wrap.find("[data-action='language']");
		if ($btn.length && !$btn.attr("aria-haspopup")) {
			$btn.attr({
				"aria-haspopup": "listbox",
				"aria-expanded": "false",
				"aria-label": __("Change language"),
			});
		}
	}

	template() {
		const shortcut = frappe.ui.keys?.get_shortcut_label
			? frappe.ui.keys.get_shortcut_label("ctrl+k")
			: frappe.utils.is_mac()
				? "⌘K"
				: "Ctrl+K";
		const lang = this.language_label();
		const avatar = frappe.avatar(frappe.session.user, "avatar-medium");

		return `
			<header class="staff-pro-topbar">
				<div class="staff-pro-topbar__inner">
					<div class="staff-pro-topbar__left">
						<div class="staff-pro-topbar__id"></div>
						<div class="staff-pro-topbar__status">
							<span class="staff-pro-topbar__status-dot"></span>
							<span class="staff-pro-topbar__status-label"></span>
						</div>
					</div>
					<div class="staff-pro-topbar__center">
						<div class="staff-pro-topbar__search-wrap">
							<div class="staff-pro-topbar__search" data-action="search" role="combobox" aria-expanded="false" aria-haspopup="listbox">
								${frappe.utils.icon("search", "sm")}
								<input class="staff-pro-topbar__search-input staff-pro-topbar__search-field" type="text" autocomplete="off" spellcheck="false" placeholder="${__("Search employees, payroll, knowledge, help")}" aria-label="${__("Search")}" />
								<kbd class="staff-pro-topbar__shortcut">${frappe.utils.escape_html(shortcut)}</kbd>
							</div>
						</div>
					</div>
					<div class="staff-pro-topbar__right">
						<div class="staff-pro-topbar__icon-btn staff-pro-topbar__search-toggle" data-action="search" role="button" tabindex="0" title="${__("Search")}">
							${frappe.utils.icon("search", "sm")}
						</div>
						<div class="staff-pro-topbar__notifications-wrap">
							<div class="staff-pro-topbar__icon-btn" data-action="notifications" role="button" tabindex="0" title="${__("Notifications")}" aria-haspopup="dialog" aria-expanded="false" aria-label="${__("Notifications")}">
								${frappe.utils.icon("bell", "sm")}
								<span class="staff-pro-topbar__badge hidden">0</span>
							</div>
							<div class="staff-pro-topbar__notifications-panel hidden" role="dialog" aria-label="${__("Notifications")}"></div>
						</div>
						<div class="staff-pro-topbar__icon-btn" data-action="settings" role="button" tabindex="0" title="${__("Settings")}">
							${frappe.utils.icon("setting", "sm")}
						</div>
						<div class="staff-pro-topbar__lang-wrap">
							<div class="staff-pro-topbar__icon-btn staff-pro-topbar__lang" data-action="language" role="button" tabindex="0" title="${__("Language")}" aria-haspopup="listbox" aria-expanded="false" aria-label="${__("Change language")}">
								${frappe.utils.escape_html(lang)}
							</div>
							<div class="staff-pro-topbar__menu hidden" role="listbox" aria-label="${__("Language")}"></div>
						</div>
						<div class="staff-pro-topbar__avatar" data-action="profile" role="button" tabindex="0" title="${__("Profile")}">
							${avatar}
						</div>
					</div>
				</div>
			</header>
		`;
	}

	bind() {
		if (!this.$wrapper) return;

		if (!this.bound) {
			this.bound = true;

			this.$wrapper.on("click", "[data-action='search']", (e) => {
				e.stopPropagation();
				this.open_search_panel();
			});
			this.$wrapper.on("input", ".staff-pro-topbar__search-field", (e) => {
				this.sync_search_fields(e.currentTarget.value);
				this.schedule_search(e.currentTarget.value);
			});
			this.$wrapper.on("focus", ".staff-pro-topbar__search-field", () => {
				this.open_search_panel();
			});
			this.$wrapper.on("keydown", ".staff-pro-topbar__search-field", (e) => {
				this.on_search_keydown(e);
			});
			this.$wrapper.on("click", "[data-action='notifications']", (e) => {
				e.stopPropagation();
				this.toggle_notifications_panel();
			});
			this.$wrapper.on("click", "[data-action='settings']", () => this.open_settings());
			this.$wrapper.on("click", "[data-action='profile']", () => this.open_profile());
			this.$wrapper.on("click", "[data-action='language']", (e) => {
				e.stopPropagation();
				this.toggle_language_menu();
			});
			this.$wrapper.on("keydown", "[data-action]", (e) => {
				if ($(e.target).is(".staff-pro-topbar__search-field")) return;
				if (e.key === "Enter" || e.key === " ") {
					e.preventDefault();
					$(e.currentTarget).trigger("click");
				}
			});

			$(document).on("page-change.staff-pro-topbar form-load.staff-pro-topbar", () => {
				this.refresh_context();
				this.close_notifications_panel();
				this.close_language_menu();
				this.close_search_panel();
			});

			if (frappe.router?.on) {
				frappe.router.on("change", () => this.refresh_context());
			}

			if (frappe.realtime?.on) {
				frappe.realtime.on("notification", () => {
					this.refresh_notifications();
					if (this.notifications_open) {
						this.load_notifications(true);
					}
				});
			}
		}

		$(document).off("click.staff-pro-topbar mousedown.staff-pro-topbar keydown.staff-pro-topbar");
		$(document).on("click.staff-pro-topbar", (e) => {
			if (!$(e.target).closest(".staff-pro-topbar__lang-wrap, .staff-pro-topbar__menu").length) {
				this.close_language_menu();
			}
			if (
				!$(e.target).closest(".staff-pro-topbar__notifications-wrap").length &&
				!$(e.target).closest(".staff-pro-topbar__notifications-panel").length &&
				!$(e.target).closest(".staff-pro-topbar__notifications-backdrop").length
			) {
				this.close_notifications_panel();
			}
			if (
				!$(e.target).closest(".staff-pro-topbar__search-wrap").length &&
				!$(e.target).closest(".staff-pro-topbar__search-panel").length &&
				!$(e.target).closest(".staff-pro-topbar__search-toggle").length
			) {
				this.close_search_panel();
			}
		});

		$(document).on("mousedown.staff-pro-topbar", (e) => {
			if (
				!$(e.target).closest(".staff-pro-topbar__notifications-wrap").length &&
				!$(e.target).closest(".staff-pro-topbar__notifications-panel").length &&
				!$(e.target).closest(".staff-pro-topbar__notifications-backdrop").length
			) {
				this.close_notifications_panel();
			}
		});

		$(document).on("keydown.staff-pro-topbar", (e) => {
			if (e.key === "Escape") {
				this.close_language_menu();
				this.close_notifications_panel();
				this.close_search_panel();
			}
		});
	}

	refresh_context() {
		if (!this.$wrapper) return;
		const { id, status } = this.get_context();
		this.$wrapper.find(".staff-pro-topbar__id").text(id);
		this.$wrapper.find(".staff-pro-topbar__status-label").text(status);
		this.$wrapper
			.find(".staff-pro-topbar__avatar")
			.attr("title", this.is_intake_flow() ? __("Logout") : __("Profile"));
		this.$wrapper
			.find("[data-action='language']")
			.not(".is-open")
			.text(this.language_label());
	}

	get_context() {
		const route = frappe.get_route?.() || [];
		const frm = window.cur_frm;

		if (frm?.docname && !frm.is_new?.()) {
			return {
				id: String(frm.docname).toUpperCase(),
				status: __(
					frm.doc.workflow_state || frm.doc.status || (frm.doc.docstatus === 1 ? "Submitted" : "Open")
				),
			};
		}

		if (route[0] === "dashboard-view" || route[0] === "dashboard") {
			return {
				id: String(route[1] || __("Dashboard")).toUpperCase(),
				status: __("Live"),
			};
		}

		if (route[0] === "Workspaces") {
			return {
				id: String(route[route.length - 1] || __("Workspace")).toUpperCase(),
				status: frappe.boot?.sitename || __("Active"),
			};
		}

		if (route[0] === "List") {
			return {
				id: String(route[1] || __("List")).toUpperCase(),
				status: __(route[2] || "List"),
			};
		}

		if (route[0] === "query-report") {
			return {
				id: String(route[1] || __("Report")).toUpperCase(),
				status: __("Report"),
			};
		}

		const label = (route || []).filter(Boolean).join(" · ") || "Staff Pro BPO";
		return {
			id: String(label).toUpperCase(),
			status: __("Active"),
		};
	}

	refresh_notifications() {
		if (!this.$wrapper) return;
		const count = cint(
			frappe.boot?.notification_unread_count ||
				$(".sidebar-notification .sidebar-item-suffix").text() ||
				0
		);
		const $badge = this.$wrapper.find(".staff-pro-topbar__badge");
		if (count > 0) {
			$badge.text(count > 99 ? "99+" : count).removeClass("hidden");
		} else {
			$badge.addClass("hidden");
		}
	}

	patch_native_awesomebar() {
		if (this._awesomebar_patched) return;
		this._awesomebar_patched = true;

		const self = this;
		if (frappe.search && typeof frappe.search.open_awesomebar_from_global_search_shortcut === "function") {
			frappe.search.open_awesomebar_from_global_search_shortcut = function (e) {
				e?.preventDefault?.();
				e?.stopPropagation?.();
				self.open_search_panel();
				return false;
			};
		}

		$(document).on("show.bs.modal.staff-pro-search", (e) => {
			const $modal = $(e.target);
			if (
				$modal.find(".cool-awesomebar-modal-footer").length ||
				$modal.find(".navbar-modal-wrapper").length ||
				$modal.find("#navbar-search").length
			) {
				e.preventDefault();
				e.stopImmediatePropagation();
				setTimeout(() => $modal.modal("hide"), 0);
				self.open_search_panel();
			}
		});

		$(document).on("click.staff-pro-search", "#navbar-modal-search, #small-search-button, #full-search-button", (e) => {
			e.preventDefault();
			e.stopImmediatePropagation();
			self.open_search_panel();
		});
	}

	search_anchor() {
		const $toggle = this.$wrapper.find(".staff-pro-topbar__search-toggle");
		if ($toggle.length && $toggle.is(":visible")) {
			return $toggle.get(0);
		}
		return this.$wrapper.find(".staff-pro-topbar__search").get(0);
	}

	visible_search_field() {
		const $mobile = this.search_panel().find(".staff-pro-topbar__search-panel-field .staff-pro-topbar__search-field");
		if ($mobile.length && $mobile.is(":visible")) {
			return $mobile.get(0);
		}
		return this.$wrapper.find(".staff-pro-topbar__search-input").get(0);
	}

	sync_search_fields(value) {
		this.search_fields().each((_, el) => {
			if (el.value !== value) el.value = value;
		});
	}

	schedule_search(value) {
		clearTimeout(this._search_timer);
		this._search_timer = setTimeout(() => this.run_search(value), 50);
	}

	collect_search_utils(txt, methods) {
		const utils = frappe.search?.utils;
		if (!utils) return [];
		const out = [];
		methods.forEach((name) => {
			const fn = utils[name];
			if (typeof fn !== "function") return;
			try {
				const result = fn.call(utils, txt);
				if (Array.isArray(result) && result.length) {
					out.push(...result);
				}
			} catch (e) {
				// Ignore optional search sources that are unavailable on this desk version.
			}
		});
		return out;
	}

	deduplicate_search_options(options) {
		const out = [];
		const routes = [];
		(options || []).forEach((option) => {
			if (option?.route) {
				if (
					Array.isArray(option.route) &&
					option.route[0] === "List" &&
					option.route[2] !== "Report" &&
					option.route[2] !== "Inbox"
				) {
					option.route.splice(2);
				}
				const str_route =
					typeof option.route === "string" ? option.route : option.route.join("/");
				if (option.description || routes.indexOf(str_route) === -1) {
					out.push(option);
					routes.push(str_route);
				} else {
					const old = routes.indexOf(str_route);
					if (out[old].index < option.index && !option.recent) {
						out[old] = option;
					}
				}
			} else {
				out.push(option);
				routes.push("");
			}
		});
		return out;
	}

	add_search_defaults(txt, options) {
		if (txt.charAt(0) !== "#") {
			options.unshift({
				label: __("Search for {0}", [frappe.utils.xss_sanitise(txt).bold()]),
				value: __("Search for {0}", [frappe.utils.xss_sanitise(txt)]),
				match: txt,
				index: 100,
				default: "Search",
				onclick: () => {
					if (frappe.searchdialog?.search?.init_search) {
						frappe.searchdialog.search.init_search(txt, "global_search");
					} else if (frappe.searchdialog?.search?.open_global_search_dialog) {
						frappe.searchdialog.search.open_global_search_dialog(txt);
					}
				},
			});
		}

		const route = frappe.get_route?.() || [];
		if (route[0] === "List" && txt.indexOf(" in") === -1) {
			const doctype = frappe.container?.page?.list_view?.doctype;
			if (doctype) {
				const meta = frappe.get_meta(doctype);
				const search_field = meta?.title_field || "name";
				options.push({
					label: __("Find {0} in {1}", [
						frappe.utils.xss_sanitise(txt).bold(),
						__(route[1]).bold(),
					]),
					value: __("Find {0} in {1}", [frappe.utils.xss_sanitise(txt), __(route[1])]),
					route_options: { [search_field]: ["like", "%" + txt + "%"] },
					onclick: () => cur_list?.show?.(),
					index: 90,
					default: "Current",
					match: txt,
				});
			}
		}

		const first = txt.substr(0, 1);
		if (first == parseInt(first, 10) || first === "(" || first === "=") {
			try {
				const expr = first === "=" ? txt.substr(1) : txt;
				const val = frappe.utils.eval_expression ? frappe.utils.eval_expression(expr) : null;
				if (val !== undefined && val !== null && !Number.isNaN(val)) {
					const result = typeof format_number === "function" ? format_number(val) : String(val);
					options.push({
						label: __("{0} = {1}", [frappe.utils.xss_sanitise(txt), `<b>${frappe.utils.escape_html(result)}</b>`]),
						value: __("{0} = {1}", [frappe.utils.xss_sanitise(txt), result]),
						match: result,
						index: 80,
						default: "Calculator",
						onclick: () => frappe.msgprint(__("{0} = {1}", [frappe.utils.xss_sanitise(txt), result]), __("Result")),
					});
				}
			} catch (e) {
				// Not a calculator expression.
			}
		}

		if (txt.toLowerCase().includes("random")) {
			options.push({
				label: __("Generate Random Password"),
				value: frappe.utils.get_random(16),
				onclick: () => frappe.msgprint(frappe.utils.get_random(16), __("Result")),
			});
		}

		return options;
	}

	build_search_options(txt) {
		frappe.search?.utils?.setup_recent?.();
		let options = [];

		if (txt && txt.length > 1) {
			if (txt.charAt(0) === "#" && frappe.tags?.utils?.get_tags) {
				options = frappe.tags.utils.get_tags(txt) || [];
			} else {
				options = this.collect_search_utils(txt, [
					"get_creatables",
					"get_search_in_list",
					"get_doctypes",
					"get_doctype_layouts",
					"get_reports",
					"get_pages",
					"get_workspaces",
					"get_desktop_icons",
					"get_dashboards",
					"get_recent_pages",
					"get_executables",
					"get_marketplace_apps",
				]);
				options = this.add_search_defaults(txt, options);
			}
		} else {
			options = this.collect_search_utils(txt || "", ["get_recent_pages"]);
			options = options.concat(this.collect_search_utils("", ["get_frequent_links"]));
		}

		options = this.deduplicate_search_options(options);
		options.sort((a, b) => (b.index || 0) - (a.index || 0));
		return options.slice(0, 20);
	}

	run_search(value) {
		if (!this.search_open) return;
		const txt = String(value || "")
			.trim()
			.replace(/\s\s+/g, " ");
		this.search_seq += 1;
		const seq = this.search_seq;
		const options = this.build_search_options(txt);
		this.render_search_results(options);

		if (txt.length > 1 && frappe.boot?.has_awesomebar_search) {
			frappe.call({
				method: "frappe.desk.search.awesomebar_search",
				args: { txt },
				callback: (r) => {
					if (seq !== this.search_seq || !r.message?.length) return;
					const merged = this.deduplicate_search_options(this.search_items.concat(r.message));
					merged.sort((a, b) => (b.index || 0) - (a.index || 0));
					this.render_search_results(merged.slice(0, 20));
				},
			});
		}
	}

	search_item_label(item) {
		return item.label || item.value || "";
	}

	search_item_meta(item) {
		if (item.description && item.description !== item.value) {
			return item.description;
		}
		return item.type || item.default || "";
	}

	render_search_results(options) {
		this.search_items = options || [];
		const $results = this.search_panel().find(".staff-pro-topbar__search-results");
		if (!this.search_items.length) {
			this.search_index = -1;
			$results.html(`<div class="staff-pro-topbar__search-empty">${__("No results found")}</div>`);
			return;
		}

		const html = this.search_items
			.map((item, index) => {
				const meta = this.search_item_meta(item);
				return `
					<button type="button" class="staff-pro-topbar__search-item" data-index="${index}" role="option">
						<span class="staff-pro-topbar__search-item-label">${this.search_item_label(item)}</span>
						${meta ? `<span class="staff-pro-topbar__search-item-meta">${frappe.utils.escape_html(String(meta))}</span>` : ""}
					</button>
				`;
			})
			.join("");

		$results.html(html);
		this.set_search_index(0);
	}

	set_search_index(index) {
		if (!this.search_items.length) {
			this.search_index = -1;
			return;
		}
		const max = this.search_items.length - 1;
		this.search_index = Math.max(0, Math.min(max, index));
		const $items = this.search_panel().find(".staff-pro-topbar__search-item");
		$items.removeClass("is-active");
		const $active = $items.eq(this.search_index).addClass("is-active");
		$active.get(0)?.scrollIntoView({ block: "nearest" });
	}

	on_search_keydown(e) {
		if (e.key === "ArrowDown") {
			e.preventDefault();
			this.set_search_index(this.search_index + 1);
			return;
		}
		if (e.key === "ArrowUp") {
			e.preventDefault();
			this.set_search_index(this.search_index - 1);
			return;
		}
		if (e.key === "Enter") {
			e.preventDefault();
			if (this.search_index >= 0) {
				this.select_search_item(this.search_index);
			}
			return;
		}
		if (e.key === "Escape") {
			e.preventDefault();
			this.close_search_panel();
			return;
		}
		if ((e.ctrlKey || e.metaKey) && String(e.key).toLowerCase() === "k") {
			e.preventDefault();
			this.close_search_panel();
			return;
		}
		if ((e.ctrlKey || e.metaKey) && String(e.key).toLowerCase() === "g") {
			e.preventDefault();
			this.open_global_search();
		}
	}

	open_global_search() {
		const txt = this.$wrapper.find(".staff-pro-topbar__search-input").val() || "";
		this.close_search_panel();
		if (frappe.searchdialog?.search?.open_global_search_dialog) {
			frappe.searchdialog.search.open_global_search_dialog(txt);
			return;
		}
		if (frappe.searchdialog?.search?.init_search) {
			frappe.searchdialog.search.init_search(txt, "global_search");
			return;
		}
		if (frappe.search?.open_global_search_from_navbar_shortcut) {
			frappe.search.open_global_search_from_navbar_shortcut({ preventDefault() {} });
		}
	}

	select_search_item(index) {
		const item = this.search_items[index];
		if (!item) return;
		this.close_search_panel();

		if (item.route_options) {
			frappe.route_options = item.route_options;
		}

		if (item.onclick) {
			item.onclick(item.match);
			return;
		}

		const route = item.route;
		const first = Array.isArray(route) ? route[0] : route;
		if (typeof first === "string" && (first.startsWith("https://") || first.startsWith("http://"))) {
			window.open(first, "_blank");
			return;
		}
		if (typeof first === "string" && first.startsWith("/") && !first.startsWith("//")) {
			if (first.startsWith("/app/") || first.startsWith("/desk/")) {
				frappe.set_route(first);
			} else {
				window.location.href = first;
			}
			return;
		}
		if (route) {
			frappe.set_route(route);
		}
	}

	position_search_panel() {
		if (!this.search_open || !this.$wrapper) return;
		const $panel = this.search_panel();
		const anchor = this.search_anchor();
		if (!anchor) return;

		const rect = anchor.getBoundingClientRect();
		const width = Math.min(Math.max(rect.width, 480), window.innerWidth - 24);
		let left = rect.left;
		if (left + width > window.innerWidth - 12) {
			left = Math.max(12, window.innerWidth - width - 12);
		}
		$panel.css({
			top: `${rect.bottom + 8}px`,
			left: `${left}px`,
			width: `${width}px`,
			right: "auto",
		});
	}

	open_search_panel() {
		if (!this.$wrapper) return;
		if (this.search_open) {
			this.visible_search_field()?.focus();
			return;
		}

		this.close_language_menu();
		this.close_notifications_panel();
		this.search_open = true;
		$("body").addClass("staff-pro-search-open");
		this.$wrapper.find(".staff-pro-topbar__search").addClass("is-open").attr("aria-expanded", "true");
		this.$wrapper.find(".staff-pro-topbar__search-toggle").addClass("is-open");
		this.mount_search_panel().removeClass("hidden");
		this.position_search_panel();
		$(window).on("resize.staff-pro-topbar scroll.staff-pro-topbar", this.on_reposition_menu);

		const field = this.visible_search_field();
		const value = field?.value || "";
		this.run_search(value);
		setTimeout(() => field?.focus(), 0);
	}

	close_search_panel(keep_query = false) {
		if (!this.search_open) return;
		this.search_open = false;
		this.search_seq += 1;
		clearTimeout(this._search_timer);
		if (!this.language_open && !this.notifications_open) {
			$(window).off("resize.staff-pro-topbar scroll.staff-pro-topbar", this.on_reposition_menu);
		}
		$("body").removeClass("staff-pro-search-open");
		this.search_panel().addClass("hidden");
		this.$wrapper?.find(".staff-pro-topbar__search").removeClass("is-open").attr("aria-expanded", "false");
		this.$wrapper?.find(".staff-pro-topbar__search-toggle").removeClass("is-open");
		this.visible_search_field()?.blur();
		if (!keep_query) {
			this.sync_search_fields("");
		}
	}

	open_search() {
		this.open_search_panel();
	}

	position_notifications_panel() {
		if (!this.notifications_open || !this.$wrapper) return;
		const $btn = this.$wrapper.find("[data-action='notifications']");
		const $panel = this.$wrapper.find(".staff-pro-topbar__notifications-panel");
		const btn = $btn.get(0);
		if (!btn) return;

		const rect = btn.getBoundingClientRect();
		$panel.css({
			top: `${rect.bottom + 8}px`,
			right: `${window.innerWidth - rect.right}px`,
			left: "auto",
		});
	}

	render_notifications_shell() {
		return `
			<div class="staff-pro-topbar__notifications-header">
				<div class="staff-pro-topbar__notifications-title">${__("Notifications")}</div>
				<div class="staff-pro-topbar__notifications-actions">
					<button type="button" class="staff-pro-topbar__notifications-action" data-action="mark-all-read" title="${__("Mark all as read")}">
						${frappe.utils.icon("check-check", "sm")}
					</button>
					<button type="button" class="staff-pro-topbar__notifications-action" data-action="notification-settings" title="${__("Notification Settings")}">
						${frappe.utils.icon("setting", "sm")}
					</button>
				</div>
			</div>
			<div class="staff-pro-topbar__notifications-body">
				<div class="staff-pro-topbar__notifications-loading">${__("Loading...")}</div>
			</div>
			<div class="staff-pro-topbar__notifications-footer">
				<button type="button" class="staff-pro-topbar__notifications-footer-btn" data-action="view-all-notifications">
					${__("See all Activity")}
				</button>
			</div>
		`;
	}

	get_notification_message(notification) {
		let message = notification.title || notification.subject || notification.description || "";
		if (typeof strip_html === "function") {
			message = strip_html(message);
		} else if (frappe.utils?.strip_html) {
			message = frappe.utils.strip_html(message);
		}
		return message || __("New notification");
	}

	get_notification_route(notification) {
		if (notification.link) {
			return notification.link;
		}
		if (notification.document_type && notification.document_name) {
			return frappe.utils.get_form_link(notification.document_type, notification.document_name);
		}
		return null;
	}

	render_notifications_list(notifications) {
		this.notification_items = notifications;
		const $body = this.$wrapper.find(".staff-pro-topbar__notifications-body");
		if (!notifications.length) {
			$body.html(`<div class="staff-pro-topbar__notifications-empty">${__("You have no notifications")}</div>`);
			return;
		}

		const items = notifications
			.map((notification) => {
				const unread_class = notification.read ? "" : "is-unread";
				const message = frappe.utils.escape_html(this.get_notification_message(notification));
				const time = frappe.datetime.comment_when(notification.creation);
				const avatar = frappe.avatar(notification.from_user || "Administrator", "avatar-medium");
				return `
					<button type="button" class="staff-pro-topbar__notification-item ${unread_class}" data-notification="${frappe.utils.escape_html(notification.name)}">
						${avatar}
						<span class="staff-pro-topbar__notification-content">
							<span class="staff-pro-topbar__notification-message">${message}</span>
							<span class="staff-pro-topbar__notification-time">${frappe.utils.escape_html(time)}</span>
						</span>
					</button>
				`;
			})
			.join("");

		$body.html(items);
	}

	load_notifications(force = false) {
		if (this.notifications_loading) return;
		if (this.notifications_loaded && !force) return;

		this.notifications_loading = true;
		const $body = this.$wrapper.find(".staff-pro-topbar__notifications-body");
		$body.html(`<div class="staff-pro-topbar__notifications-loading">${__("Loading...")}</div>`);

		frappe.call({
			method: "frappe.desk.doctype.notification_log.notification_log.get_notification_logs",
			args: { limit: 20 },
			type: "GET",
			callback: (response) => {
				this.notifications_loading = false;
				this.notifications_loaded = true;
				const notifications = response.message?.notification_logs || [];
				if (response.message?.user_info) {
					frappe.update_user_info(response.message.user_info);
				}
				this.render_notifications_list(notifications);
			},
			error: () => {
				this.notifications_loading = false;
				$body.html(`<div class="staff-pro-topbar__notifications-empty">${__("Could not load notifications")}</div>`);
			},
		});
	}

	open_notification_route(route) {
		if (!route) {
			frappe.set_route("List", "Notification Log");
			return;
		}

		if (route.startsWith("/app/")) {
			frappe.set_route(route.replace(/^\/app\//, "").split("/").filter(Boolean));
			return;
		}

		if (route.startsWith("#")) {
			window.location.hash = route;
			return;
		}

		frappe.set_route(route.split("/").filter(Boolean));
	}

	handle_notification_click(name) {
		const notification = this.notification_items.find((item) => item.name === name);
		this.close_notifications_panel();
		if (name) {
			frappe.call({
				method: "frappe.desk.doctype.notification_log.notification_log.mark_as_read",
				args: { docname: name },
			});
		}
		this.open_notification_route(notification ? this.get_notification_route(notification) : null);
		this.refresh_notifications();
	}

	mark_all_notifications_read() {
		frappe.call({
			method: "frappe.desk.doctype.notification_log.notification_log.mark_all_as_read",
			callback: () => {
				this.$wrapper.find(".staff-pro-topbar__notification-item").removeClass("is-unread");
				if (frappe.boot) {
					frappe.boot.notification_unread_count = 0;
				}
				this.refresh_notifications();
			},
		});
	}

	bind_notifications_panel_events() {
		const $panel = this.$wrapper.find(".staff-pro-topbar__notifications-panel");
		const $backdrop = $(".staff-pro-topbar__notifications-backdrop");
		$backdrop.off("click.notifications").on("click.notifications", (e) => {
			e.stopPropagation();
			this.close_notifications_panel();
		});
		$panel.off("click.notifications").on("click.notifications", (e) => {
			e.stopPropagation();
		});
		$panel.on("click.notifications", "[data-action='mark-all-read']", (e) => {
			e.stopPropagation();
			this.mark_all_notifications_read();
		});
		$panel.on("click.notifications", "[data-action='notification-settings']", (e) => {
			e.stopPropagation();
			this.close_notifications_panel();
			frappe.set_route("Form", "Notification Settings", frappe.session.user);
		});
		$panel.on("click.notifications", "[data-action='view-all-notifications']", (e) => {
			e.stopPropagation();
			this.close_notifications_panel();
			frappe.set_route("List", "Notification Log");
		});
		$panel.on("click.notifications", "[data-notification]", (e) => {
			e.stopPropagation();
			this.handle_notification_click($(e.currentTarget).data("notification"));
		});
	}

	toggle_notifications_panel() {
		if (this.notifications_open) {
			this.close_notifications_panel();
			return;
		}

		this.close_language_menu();
		this.close_search_panel();
		const $panel = this.$wrapper.find(".staff-pro-topbar__notifications-panel");
		const $btn = this.$wrapper.find("[data-action='notifications']");
		$panel.html(this.render_notifications_shell());
		$panel.removeClass("hidden");
		$(".staff-pro-topbar__notifications-backdrop").removeClass("hidden");
		$btn.addClass("is-open").attr("aria-expanded", "true");
		this.notifications_open = true;
		this.bind_notifications_panel_events();
		this.position_notifications_panel();
		$(window).on("resize.staff-pro-topbar scroll.staff-pro-topbar", this.on_reposition_menu);
		this.load_notifications();
		frappe.call({
			method: "frappe.desk.doctype.notification_log.notification_log.trigger_indicator_hide",
		});
	}

	close_notifications_panel() {
		this.notifications_open = false;
		if (!this.language_open && !this.search_open) {
			$(window).off("resize.staff-pro-topbar scroll.staff-pro-topbar", this.on_reposition_menu);
		}
		this.$wrapper?.find(".staff-pro-topbar__notifications-panel").addClass("hidden");
		$(".staff-pro-topbar__notifications-backdrop").addClass("hidden");
		this.$wrapper?.find("[data-action='notifications']").removeClass("is-open").attr("aria-expanded", "false");
	}

	open_settings() {
		frappe.set_route("Form", "User", frappe.session.user);
	}

	open_profile() {
		if (this.is_intake_flow()) {
			this.logout();
			return;
		}
		frappe.set_route("Form", "User", frappe.session.user);
	}

	is_intake_flow() {
		const route = frappe.get_route?.() || [];
		return route[0] === "setup-wizard";
	}

	logout() {
		if (frappe.app?.logout) {
			frappe.app.logout();
			return;
		}
		window.location.href = "/api/method/logout";
	}

	language_label() {
		return this.current_language_code().slice(0, 2).toUpperCase();
	}

	normalize_language_code(code) {
		return String(code || "en")
			.trim()
			.toLowerCase()
			.replace(/_/g, "-")
			.split("-")[0];
	}

	current_language_code() {
		const lang =
			frappe.boot?.lang ||
			frappe.boot?.user?.language ||
			frappe.defaults?.get_user_default?.("language") ||
			"en";
		return this.normalize_language_code(lang);
	}

	default_languages() {
		return [
			{ code: "en", label: "English" },
			{ code: "es", label: "Español" },
			{ code: "fr", label: "Français" },
			{ code: "ar", label: "العربية" },
			{ code: "hi", label: "हिन्दी" },
		];
	}

	languages() {
		return this.language_options || this.default_languages();
	}

	load_language_options(callback) {
		if (this.language_options) {
			callback?.();
			return;
		}

		frappe.call({
			method: "frappe.translate.get_all_languages",
			args: { with_language_name: true },
			callback: (response) => {
				const options = (response.message || [])
					.map((language) => ({
						code: language.language_code || language.name,
						label: language.language_name || language.language_code || language.name,
					}))
					.filter((language) => language.code);

				this.language_options = options.length ? options : this.default_languages();
				callback?.();
			},
			error: () => {
				this.language_options = this.default_languages();
				callback?.();
			},
		});
	}

	render_language_menu() {
		const $menu = this.$wrapper.find(".staff-pro-topbar__menu");
		const current = this.current_language_code();
		$menu.html(
			this.languages()
				.map(
					(lang) => `
						<div class="staff-pro-topbar__menu-item ${
							this.normalize_language_code(lang.code) === current ? "is-active" : ""
						}" data-lang="${frappe.utils.escape_html(lang.code)}" role="option" tabindex="0" aria-selected="${
							this.normalize_language_code(lang.code) === current ? "true" : "false"
						}">
							${frappe.utils.escape_html(lang.label)}
						</div>
					`
				)
				.join("")
		);
		this.bind_language_menu_events($menu);
	}

	bind_language_menu_events($menu) {
		$menu.off("mousedown.lang click.lang keydown.lang");
		$menu.on("mousedown.lang click.lang", (e) => {
			e.stopPropagation();
		});
		$menu.on("click.lang", "[data-lang]", (e) => {
			e.preventDefault();
			e.stopPropagation();
			this.set_language($(e.currentTarget).attr("data-lang"));
		});
		$menu.on("keydown.lang", "[data-lang]", (e) => {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				e.stopPropagation();
				this.set_language($(e.currentTarget).attr("data-lang"));
			}
		});
	}

	position_language_menu() {
		if (!this.language_open || !this.$wrapper) return;
		const $btn = this.$wrapper.find("[data-action='language']");
		const $menu = this.$wrapper.find(".staff-pro-topbar__menu");
		const btn = $btn.get(0);
		if (!btn) return;

		const rect = btn.getBoundingClientRect();
		$menu.css({
			top: `${rect.bottom + 8}px`,
			right: `${window.innerWidth - rect.right}px`,
			left: "auto",
		});
	}

	toggle_language_menu() {
		const $menu = this.$wrapper.find(".staff-pro-topbar__menu");
		const $btn = this.$wrapper.find("[data-action='language']");
		if (!this.language_open) {
			this.close_notifications_panel();
			this.close_search_panel();
			$menu.html(`<div class="staff-pro-topbar__menu-item is-active">${__("Loading...")}</div>`);
			$menu.removeClass("hidden");
			$btn.addClass("is-open").attr("aria-expanded", "true");
			this.language_open = true;
			this.position_language_menu();
			$(window).on("resize.staff-pro-topbar scroll.staff-pro-topbar", this.on_reposition_menu);
			this.load_language_options(() => {
				if (!this.language_open) return;
				this.render_language_menu();
				this.position_language_menu();
			});
		} else {
			this.close_language_menu();
		}
	}

	close_language_menu() {
		this.language_open = false;
		if (!this.notifications_open && !this.search_open) {
			$(window).off("resize.staff-pro-topbar scroll.staff-pro-topbar", this.on_reposition_menu);
		}
		this.$wrapper?.find(".staff-pro-topbar__menu").addClass("hidden");
		this.$wrapper?.find("[data-action='language']").removeClass("is-open").attr("aria-expanded", "false");
	}

	set_language(code) {
		const normalized = this.normalize_language_code(code);
		if (!normalized) return;

		this.close_language_menu();

		frappe.call({
			method: "hrms.boot.set_user_language",
			args: {
				language: normalized,
			},
			callback: () => {
				frappe.show_alert({
					message: __("Language updated"),
					indicator: "green",
				});
				window.location.reload();
			},
			error: () => {
				frappe.call({
					method: "frappe.client.set_value",
					args: {
						doctype: "User",
						name: frappe.session.user,
						fieldname: "language",
						value: normalized,
					},
					callback: () => {
						frappe.show_alert({
							message: __("Language updated"),
							indicator: "green",
						});
						window.location.reload();
					},
					error: () => {
						frappe.show_alert({
							message: __("Could not update language"),
							indicator: "red",
						});
					},
				});
			},
		});
	}
};

function start_staff_pro_topbar() {
	if (window.staff_pro_topbar || frappe.session.user === "Guest") return;
	window.staff_pro_topbar = new hrms.ui.TopBar();
}

$(document).on("app_ready", start_staff_pro_topbar);

if (typeof frappe !== "undefined" && frappe.session?.user && $(".main-section").length) {
	start_staff_pro_topbar();
}
