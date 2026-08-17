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
	overflow: hidden !important;
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
	background: #00a6e8 !important;
	flex-shrink: 0 !important;
}
.staff-pro-topbar__center {
	display: flex !important;
	flex-direction: row !important;
	align-items: center !important;
	justify-content: center !important;
	flex: 1 1 auto !important;
	min-width: 0 !important;
}
.staff-pro-topbar__search {
	display: flex !important;
	flex-direction: row !important;
	align-items: center !important;
	gap: 10px !important;
	width: 320px !important;
	max-width: 100% !important;
	height: 36px !important;
	margin: 0 !important;
	padding: 0 10px 0 14px !important;
	border: 0 !important;
	border-radius: 999px !important;
	background: #f3f4f6 !important;
	box-shadow: none !important;
	cursor: pointer !important;
	color: #9ca3af !important;
	font: inherit !important;
	line-height: 1 !important;
	appearance: none !important;
	-webkit-appearance: none !important;
}
.staff-pro-topbar__search .icon,
.staff-pro-topbar__search svg {
	width: 15px !important;
	height: 15px !important;
	stroke: #9ca3af !important;
	flex-shrink: 0 !important;
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
.staff-pro-topbar__menu {
	position: absolute !important;
	top: calc(100% + 8px) !important;
	right: 0 !important;
	z-index: 40 !important;
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
.staff-pro-topbar__search-toggle { display: none !important; }
@media (max-width: 767px) {
	.staff-pro-topbar__center { display: none !important; }
	.staff-pro-topbar__search-toggle { display: inline-flex !important; }
	.staff-pro-topbar__lang { display: none !important; }
}
`;

hrms.ui.TopBar = class {
	constructor() {
		this.$wrapper = null;
		this.language_open = false;
		this.bound = false;
		this.inject_css();
		this.make();
	}

	inject_css() {
		if (document.getElementById("staff-pro-topbar-css")) return;
		const style = document.createElement("style");
		style.id = "staff-pro-topbar-css";
		style.textContent = TOPBAR_CSS;
		document.head.appendChild(style);
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
		this.bind();
		this.refresh_context();
		this.refresh_notifications();
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
						<div class="staff-pro-topbar__search" data-action="search" role="button" tabindex="0">
							${frappe.utils.icon("search", "sm")}
							<span class="staff-pro-topbar__search-placeholder">
								${__("Search employees, payroll, knowledge, help")}
							</span>
							<kbd class="staff-pro-topbar__shortcut">${frappe.utils.escape_html(shortcut)}</kbd>
						</div>
					</div>
					<div class="staff-pro-topbar__right">
						<div class="staff-pro-topbar__icon-btn staff-pro-topbar__search-toggle" data-action="search" role="button" tabindex="0" title="${__("Search")}">
							${frappe.utils.icon("search", "sm")}
						</div>
						<div class="staff-pro-topbar__icon-btn" data-action="notifications" role="button" tabindex="0" title="${__("Notifications")}">
							${frappe.utils.icon("bell", "sm")}
							<span class="staff-pro-topbar__badge hidden">0</span>
						</div>
						<div class="staff-pro-topbar__icon-btn" data-action="settings" role="button" tabindex="0" title="${__("Settings")}">
							${frappe.utils.icon("setting", "sm")}
						</div>
						<div class="staff-pro-topbar__lang-wrap">
							<div class="staff-pro-topbar__icon-btn staff-pro-topbar__lang" data-action="language" role="button" tabindex="0" title="${__("Language")}">
								${frappe.utils.escape_html(lang)}
							</div>
							<div class="staff-pro-topbar__menu hidden"></div>
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
		if (!this.$wrapper || this.bound) return;
		this.bound = true;

		this.$wrapper.on("click", "[data-action='search']", () => this.open_search());
		this.$wrapper.on("click", "[data-action='notifications']", () => this.open_notifications());
		this.$wrapper.on("click", "[data-action='settings']", () => this.open_settings());
		this.$wrapper.on("click", "[data-action='profile']", () => this.open_profile());
		this.$wrapper.on("click", "[data-action='language']", (e) => {
			e.stopPropagation();
			this.toggle_language_menu();
		});
		this.$wrapper.on("keydown", "[data-action]", (e) => {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				$(e.currentTarget).trigger("click");
			}
		});

		$(document).on("click.staff-pro-topbar", (e) => {
			if (!$(e.target).closest(".staff-pro-topbar__lang-wrap").length) {
				this.close_language_menu();
			}
		});

		$(document).on("page-change.staff-pro-topbar form-load.staff-pro-topbar", () => {
			this.refresh_context();
		});

		if (frappe.router?.on) {
			frappe.router.on("change", () => this.refresh_context());
		}

		if (frappe.realtime?.on) {
			frappe.realtime.on("notification", () => this.refresh_notifications());
		}
	}

	refresh_context() {
		if (!this.$wrapper) return;
		const { id, status } = this.get_context();
		this.$wrapper.find(".staff-pro-topbar__id").text(id);
		this.$wrapper.find(".staff-pro-topbar__status-label").text(status);
		this.$wrapper
			.find(".staff-pro-topbar__avatar")
			.attr("title", this.is_intake_flow() ? __("Logout") : __("Profile"));
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

	open_search() {
		if (frappe.search?.open_awesomebar_from_global_search_shortcut) {
			frappe.search.open_awesomebar_from_global_search_shortcut({ preventDefault() {} });
			return;
		}
		if (frappe.searchdialog?.search?.toggle_global_search_dialog) {
			frappe.searchdialog.search.toggle_global_search_dialog();
			return;
		}
		if (frappe.searchdialog?.search?.search_dialog?.show) {
			frappe.searchdialog.search.search_dialog.show();
		}
	}

	open_notifications() {
		const $btn = $(".sidebar-notification");
		if ($btn.length) {
			$btn.trigger("click");
			return;
		}
		frappe.app?.sidebar?.wrapper?.find(".dropdown-notifications")?.toggleClass("hidden");
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
		const lang = (frappe.boot?.lang || "en").split("-")[0];
		return lang.slice(0, 2).toUpperCase();
	}

	languages() {
		return [
			{ code: "en", label: "English" },
			{ code: "es", label: "Español" },
			{ code: "fr", label: "Français" },
			{ code: "ar", label: "العربية" },
			{ code: "hi", label: "हिन्दी" },
		];
	}

	toggle_language_menu() {
		const $menu = this.$wrapper.find(".staff-pro-topbar__menu");
		if (!this.language_open) {
			const current = (frappe.boot?.lang || "en").split("-")[0];
			$menu.html(
				this.languages()
					.map(
						(lang) => `
							<div class="staff-pro-topbar__menu-item ${
								lang.code === current ? "is-active" : ""
							}" data-lang="${lang.code}" role="button" tabindex="0">
								${frappe.utils.escape_html(lang.label)}
							</div>
						`
					)
					.join("")
			);
			$menu.removeClass("hidden");
			this.language_open = true;
			$menu.off("click.lang").on("click.lang", "[data-lang]", (e) => {
				this.set_language($(e.currentTarget).data("lang"));
			});
		} else {
			this.close_language_menu();
		}
	}

	close_language_menu() {
		this.language_open = false;
		this.$wrapper?.find(".staff-pro-topbar__menu").addClass("hidden");
	}

	set_language(code) {
		this.close_language_menu();
		if (!code || code === (frappe.boot?.lang || "en").split("-")[0]) return;

		frappe.call({
			method: "frappe.client.set_value",
			args: {
				doctype: "User",
				name: frappe.session.user,
				fieldname: "language",
				value: code,
			},
			callback() {
				window.location.reload();
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
