(function () {
	const FALLBACK_ROUTE = ["dashboard-view", "Human Resource"];

	function hide_onboarding_css() {
		if (document.getElementById("staff-pro-hide-onboarding")) return;
		const style = document.createElement("style");
		style.id = "staff-pro-hide-onboarding";
		style.textContent = `
			.user-onboarding,
			.onb-panel,
			.body-sidebar .onboarding-sidebar,
			.onboarding-widget-box,
			.widget.onboarding-widget,
			.workspace-page .onboarding-widget {
				display: none !important;
			}
		`;
		(document.head || document.documentElement).appendChild(style);
	}

	hide_onboarding_css();
	document.addEventListener("DOMContentLoaded", hide_onboarding_css);

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

	function should_redirect(route = frappe.get_route?.() || [], options = {}) {
		if (!frappe.boot?.staff_pro_skip_desktop || window._staff_pro_desk_redirecting) return false;

		const homeRoute = staff_pro_home_route();
		if (route[0] === homeRoute[0] && (route[1] || "") === (homeRoute[1] || "")) {
			return false;
		}

		const path = (window.location.pathname || "").replace(/\/$/, "") || "/";
		if (path === staff_pro_home_path()) return false;

		const on_apps = route[0] === "apps" || path === "/apps" || path.endsWith("/apps");
		const on_desktop_page = route[0] === "desktop";
		const on_empty_desk_route = !route[0] && (path === "/desk" || path === "/");
		const on_workforce_bootstrap =
			options.includeWorkforceBootstrap &&
			(route[0]?.toLowerCase() === "workforce" || /\/desk\/workforce\/?$/.test(path));
		return on_apps || on_desktop_page || on_empty_desk_route || on_workforce_bootstrap;
	}

	function redirect_staff_pro_home(options = {}) {
		const route = frappe.get_route?.() || [];
		if (!should_redirect(route, options)) return;

		window._staff_pro_desk_redirecting = true;
		Promise.resolve(frappe.set_route(...staff_pro_home_route())).finally(() => {
			window._staff_pro_desk_redirecting = false;
		});
	}

	$(document).on("app_ready", () => redirect_staff_pro_home({ includeWorkforceBootstrap: true }));
	$(document).on("page-change", () => redirect_staff_pro_home());
})();
