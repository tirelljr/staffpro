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
			#page-dashboard-view:not(:has(.sp-dash-pills)) .dashboard-graph,
			#page-dashboard:not(:has(.sp-dash-pills)) .dashboard-graph,
			.page-container[data-page-route="dashboard-view"]:not(:has(.sp-dash-pills)) .dashboard-graph,
			#page-dashboard-view:not(:has(.sp-dash-pills)) .dashboard-view > .widget-group,
			#page-dashboard-view:not(:has(.sp-dash-pills)) .number-widget-area,
			#page-dashboard-view:not(:has(.sp-dash-pills)) .number-card-container,
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
			.dock,
			.workspace-dock,
			.body-sidebar-container {
				align-self: stretch !important;
				height: 100% !important;
				min-height: 100vh !important;
				min-height: 100dvh !important;
				max-height: none !important;
			}
			.body-sidebar-container.expanded .body-sidebar,
			.body-sidebar {
				height: 100% !important;
				min-height: 100% !important;
				max-height: none !important;
			}
			.body-sidebar-container:not(.expanded),
			.body-sidebar-container:not(.expanded) .body-sidebar {
				height: 0 !important;
				min-height: 0 !important;
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
