(function () {
	const FALLBACK_ROUTE = ["dashboard-view", "Human Resource"];
	const WORKSPACE_DASHBOARD_ALIASES = {
		workforce: ["dashboard-view", "Human Resource"],
		people: ["dashboard-view", "Human Resource"],
		hr: ["dashboard-view", "Human Resource"],
		"human resource": ["dashboard-view", "Human Resource"],
		time: ["dashboard-view", "Attendance"],
		attendance: ["dashboard-view", "Attendance"],
		pay: ["dashboard-view", "Payroll"],
		payroll: ["dashboard-view", "Payroll"],
		talent: ["dashboard-view", "Recruitment"],
		recruitment: ["dashboard-view", "Recruitment"],
		floor: ["floor-map"],
		"ss and taxes": ["dashboard-view", "SS and Taxes"],
	};

	function hide_default_frappe_view_css() {
		if (document.getElementById("staff-pro-hide-frappe-view")) return;
		const style = document.createElement("style");
		style.id = "staff-pro-hide-frappe-view";
		style.textContent = `
			.user-onboarding,
			.onb-panel,
			.body-sidebar .onboarding-sidebar,
			.onboarding-widget-box,
			.widget.onboarding-widget,
			.workspace-page .onboarding-widget {
				display: none !important;
			}
			#page-dashboard-view .page-head,
			#page-dashboard .page-head,
			.page-container[data-page-route="dashboard-view"] .page-head,
			#page-Workspaces .page-head {
				display: none !important;
			}
			#page-dashboard-view .widget-subtitle,
			#page-dashboard .widget-subtitle,
			.page-container[data-page-route="dashboard-view"] .widget-subtitle,
			.dashboard-view .widget-subtitle,
			.dashboard-graph .widget-subtitle {
				display: none !important;
			}
			#page-dashboard-view .filter-chart,
			#page-dashboard-view .chart-actions,
			#page-dashboard .filter-chart,
			#page-dashboard .chart-actions,
			.page-container[data-page-route="dashboard-view"] .filter-chart,
			.page-container[data-page-route="dashboard-view"] .chart-actions {
				display: none !important;
			}
			#page-dashboard-view,
			#page-dashboard,
			.page-container[data-page-route="dashboard-view"] {
				background: #f4f4f4 !important;
			}
			#page-desktop,
			#page-apps,
			.page-container[data-page-route="desktop"],
			.page-container[data-page-route="apps"] {
				visibility: hidden !important;
			}
			html, body {
				min-height: 100% !important;
				min-height: 100vh !important;
				min-height: 100dvh !important;
			}
			.body-sidebar-container .overlay,
			.body-sidebar-container.expanded .overlay {
				display: none !important;
				pointer-events: none !important;
				background: transparent !important;
			}
			@media (min-width: 768px) {
				.dock:not(.hidden),
				.workspace-dock:not(.hidden) {
					position: sticky !important;
					left: auto !important;
					right: auto !important;
					transform: none !important;
					display: flex !important;
					visibility: visible !important;
					opacity: 1 !important;
					flex: 0 0 72px !important;
					width: 72px !important;
					height: 100% !important;
					min-height: calc(100vh - 64px) !important;
					min-height: calc(100dvh - 64px) !important;
					background: #ffffff !important;
				}
				body.dock-active .dock:not(.hidden),
				body.dock-pinned .dock:not(.hidden) {
					display: flex !important;
					visibility: visible !important;
					opacity: 1 !important;
				}
				.dock-item,
				.dock button.dock-item,
				.workspace-dock button.workspace-dock-item {
					height: auto !important;
					min-height: 64px !important;
					overflow: visible !important;
					color: #111111 !important;
				}
				.dock-item .dock-item-label,
				.dock .dock-label,
				.workspace-dock .workspace-dock-label {
					display: block !important;
					opacity: 1 !important;
					visibility: visible !important;
					color: #111111 !important;
				}
				.dock-item,
				.dock-item svg,
				.dock-item use,
				.dock-item .icon,
				.dock-item img {
					opacity: 1 !important;
					visibility: visible !important;
					--icon-motion-opacity: 1 !important;
					--icon-stroke: #111111;
					color: #111111 !important;
				}
				.dock .dock-item-label {
					display: block !important;
				}
				.body-sidebar-container:not(.expanded) .body-sidebar .sidebar-item-label,
				.body-sidebar-container.sidebar-hidden .body-sidebar .sidebar-item-label,
				.body-sidebar-container:not(.expanded) .body-sidebar .avatar-name-email,
				.body-sidebar-container.sidebar-hidden .body-sidebar .avatar-name-email {
					flex: 1 1 auto !important;
					min-width: 0 !important;
					width: auto !important;
					overflow: visible !important;
					opacity: 1 !important;
					visibility: visible !important;
					color: #111111 !important;
				}
				.body-sidebar-container,
				.body-sidebar-container:not(.expanded),
				.body-sidebar-container.sidebar-hidden {
					display: flex !important;
					flex: 0 0 260px !important;
					width: 260px !important;
					height: auto !important;
					min-height: calc(100vh - 64px) !important;
					min-height: calc(100dvh - 64px) !important;
					overflow: visible !important;
					visibility: visible !important;
					opacity: 1 !important;
				}
				.body-sidebar,
				.body-sidebar-container:not(.expanded) .body-sidebar,
				.body-sidebar-container.sidebar-hidden .body-sidebar {
					left: 0 !important;
					right: auto !important;
					width: 260px !important;
					height: 100% !important;
					min-height: 100% !important;
					opacity: 1 !important;
					visibility: visible !important;
					background: #ffffff !important;
					pointer-events: auto !important;
				}
				.body-sidebar-container .body-sidebar > *,
				.body-sidebar-container:not(.expanded) .body-sidebar > *,
				.body-sidebar-container.sidebar-hidden .body-sidebar > *,
				.body-sidebar .sidebar-item-label,
				.body-sidebar .avatar-name-email,
				.body-sidebar .title-container,
				.body-sidebar .header-title {
					opacity: 1 !important;
					visibility: visible !important;
					transform: none !important;
					width: auto !important;
					color: #111111 !important;
				}
				.body-sidebar .body-sidebar-top,
				.body-sidebar .sidebar-items {
					opacity: 1 !important;
					visibility: visible !important;
					flex: 1 1 auto !important;
					min-height: 0 !important;
					overflow: auto !important;
				}
			}
		`;
		(document.head || document.documentElement).appendChild(style);
	}

	function mark_staff_pro_alive() {
		if (document.body) {
			document.body.classList.add("staff-pro-alive");
		}
	}

	hide_default_frappe_view_css();
	mark_staff_pro_alive();
	document.addEventListener("DOMContentLoaded", () => {
		hide_default_frappe_view_css();
		mark_staff_pro_alive();
	});

	function staff_pro_home_route() {
		const home = frappe.boot?.staff_pro_desk_home;
		if (Array.isArray(home) && home.length) return home;
		if (typeof home === "string" && home.includes("/")) return home.split("/");
		return FALLBACK_ROUTE;
	}

	function staff_pro_home_path() {
		const route = staff_pro_home_route();
		return `/desk/${route.map((part) => encodeURIComponent(part)).join("/")}`;
	}

	function normalize_route_key(name) {
		return String(name || "")
			.toLowerCase()
			.replace(/-/g, " ")
			.trim();
	}

	function workspace_dashboard_route(route = []) {
		const raw = route[0] === "Workspaces" ? route[1] : route[0];
		return WORKSPACE_DASHBOARD_ALIASES[normalize_route_key(raw)] || null;
	}

	function same_route(left = [], right = []) {
		return left[0] === right[0] && (left[1] || "") === (right[1] || "");
	}

	function redirect_target(route = frappe.get_route?.() || []) {
		if (!frappe.boot?.staff_pro_skip_desktop || window._staff_pro_desk_redirecting) return null;

		const homeRoute = staff_pro_home_route();
		if (same_route(route, homeRoute)) return null;

		const path = (window.location.pathname || "").replace(/\/$/, "") || "/";
		if (path === staff_pro_home_path()) return null;

		const on_apps = route[0] === "apps" || path === "/apps" || path.endsWith("/apps") || path === "/app/apps";
		const on_desktop_page = route[0] === "desktop" || path.endsWith("/desktop");
		const on_empty_desk_route = !route[0] && (path === "/desk" || path === "/app" || path === "/");
		const on_bare_dashboard =
			(route[0] === "dashboard-view" || route[0] === "dashboard") && !route[1];
		if (on_apps || on_desktop_page || on_empty_desk_route || on_bare_dashboard) {
			return homeRoute;
		}

		return workspace_dashboard_route(route);
	}

	function redirect_staff_pro_home() {
		const target = redirect_target();
		if (!target) return;

		window._staff_pro_desk_redirecting = true;
		Promise.resolve(frappe.set_route(...target)).finally(() => {
			window._staff_pro_desk_redirecting = false;
		});
	}

	$(document).on("app_ready", redirect_staff_pro_home);
	$(document).on("page-change", redirect_staff_pro_home);
})();
