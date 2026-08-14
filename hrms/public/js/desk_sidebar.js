const SIDEBAR_CSS = `
.workspace-dock,
.body-sidebar,
.body-sidebar-container {
	font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif !important;
	-webkit-font-smoothing: antialiased !important;
}

/* Dock */
.workspace-dock {
	flex: 0 0 72px !important;
	width: 72px !important;
	background: #f6f6f7 !important;
	border-right: 1px solid #ececec !important;
	padding: 10px 0 12px !important;
}
.workspace-dock .workspace-dock-logo {
	height: auto !important;
	padding: 4px 0 8px !important;
}
.workspace-dock .workspace-dock-logo a {
	width: 32px !important;
	height: 32px !important;
	border-radius: 8px !important;
}
.workspace-dock .workspace-dock-items,
.workspace-dock .workspace-dock-shortcuts {
	width: 100% !important;
	padding: 0 4px !important;
	gap: 4px !important;
	align-items: center !important;
}
.workspace-dock > .workspace-dock-item,
.workspace-dock .workspace-dock-items > .workspace-dock-item,
.workspace-dock .workspace-dock-shortcuts > .workspace-dock-item {
	display: flex !important;
	flex-direction: column !important;
	align-items: center !important;
	width: 100% !important;
	height: auto !important;
	min-height: 0 !important;
	padding: 0 !important;
	background: transparent !important;
	box-shadow: none !important;
	overflow: visible !important;
}
.workspace-dock button.workspace-dock-item {
	display: flex !important;
	flex-direction: column !important;
	align-items: center !important;
	justify-content: flex-start !important;
	width: 56px !important;
	height: auto !important;
	min-height: 58px !important;
	padding: 6px 2px 6px !important;
	gap: 4px !important;
	border: 0 !important;
	border-radius: 8px !important;
	background: transparent !important;
	box-shadow: none !important;
	overflow: visible !important;
	color: #4b5563 !important;
	font-size: 9px !important;
	line-height: 1.15 !important;
	text-indent: 0 !important;
	text-transform: none !important;
}
.workspace-dock button.workspace-dock-item::after {
	content: attr(aria-label) !important;
	display: block !important;
	width: 100% !important;
	max-width: 64px !important;
	margin-top: 2px !important;
	font-size: 9px !important;
	font-weight: 500 !important;
	line-height: 1.15 !important;
	letter-spacing: 0 !important;
	color: #6b7280 !important;
	text-align: center !important;
	white-space: normal !important;
	word-break: break-word !important;
	text-transform: none !important;
}
.workspace-dock button.workspace-dock-item:has(.workspace-dock-label)::after {
	content: none !important;
	display: none !important;
}
.workspace-dock .workspace-dock-item svg,
.workspace-dock .workspace-dock-item .icon,
.workspace-dock .workspace-dock-item img {
	width: 18px !important;
	height: 18px !important;
	min-width: 18px !important;
	min-height: 18px !important;
	stroke: #4b5563 !important;
	stroke-width: 1.5 !important;
}
.workspace-dock button.workspace-dock-item:hover {
	background: #ececee !important;
}
.workspace-dock button.workspace-dock-item.active {
	background: #e8e8ea !important;
}
.workspace-dock button.workspace-dock-item.active::before {
	display: none !important;
}
.workspace-dock .workspace-dock-label,
.workspace-dock button.workspace-dock-item .workspace-dock-label {
	display: block !important;
	width: 100% !important;
	max-width: 56px !important;
	margin-top: 2px !important;
	font-size: 9px !important;
	font-weight: 500 !important;
	line-height: 1.15 !important;
	letter-spacing: 0 !important;
	color: #6b7280 !important;
	text-align: center !important;
	white-space: normal !important;
	overflow: hidden !important;
	word-break: break-word !important;
}
.workspace-dock .workspace-dock-shortcuts .workspace-dock-item {
	min-height: 36px !important;
	padding: 8px 2px !important;
}
.workspace-dock .workspace-dock-divider {
	width: 28px !important;
	background: #e5e7eb !important;
}

/* Body sidebar */
.body-sidebar {
	background: #ffffff !important;
	border-right: 1px solid #ececec !important;
	padding: 8px 8px 10px !important;
}
.body-sidebar .sidebar-header {
	padding: 8px 8px 10px !important;
	margin: 0 0 4px !important;
}
.body-sidebar .sidebar-header .header-title,
.body-sidebar .sidebar-header .workspace-title,
.body-sidebar .sidebar-header span {
	font-size: 14px !important;
	font-weight: 700 !important;
	letter-spacing: -0.01em !important;
	color: #111827 !important;
	line-height: 1.3 !important;
}
.body-sidebar .staff-pro-sidebar-search {
	display: flex !important;
	align-items: center !important;
	gap: 8px !important;
	height: 34px !important;
	margin: 8px 4px 10px !important;
	padding: 0 10px !important;
	border: 1px solid #ececec !important;
	border-radius: 8px !important;
	background: #f7f7f8 !important;
	color: #9ca3af !important;
	cursor: pointer !important;
}
.body-sidebar .staff-pro-sidebar-search svg,
.body-sidebar .staff-pro-sidebar-search .icon {
	width: 14px !important;
	height: 14px !important;
	stroke: #9ca3af !important;
}
.body-sidebar .staff-pro-sidebar-search span {
	font-size: 13px !important;
	font-weight: 400 !important;
	color: #9ca3af !important;
}
.body-sidebar .sidebar-items {
	padding: 0 2px !important;
}
.body-sidebar .standard-sidebar-item {
	margin: 0 0 2px !important;
	padding: 0 !important;
	border-radius: 8px !important;
	overflow: hidden !important;
	background: transparent !important;
	box-shadow: none !important;
}
.body-sidebar .standard-sidebar-item .item-anchor {
	display: flex !important;
	flex-direction: row !important;
	align-items: center !important;
	height: 36px !important;
	min-height: 36px !important;
	padding: 0 10px !important;
	gap: 10px !important;
	color: #111827 !important;
	text-decoration: none !important;
}
.body-sidebar .standard-sidebar-item .sidebar-item-icon {
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	width: 18px !important;
	height: 18px !important;
	padding: 0 !important;
	margin: 0 !important;
}
.body-sidebar .standard-sidebar-item .sidebar-item-icon svg,
.body-sidebar .standard-sidebar-item .sidebar-item-icon .icon {
	width: 16px !important;
	height: 16px !important;
	stroke: #111827 !important;
	stroke-width: 1.5 !important;
}
.body-sidebar .standard-sidebar-item .sidebar-item-label {
	font-size: 13px !important;
	font-weight: 500 !important;
	line-height: 1.3 !important;
	letter-spacing: 0 !important;
	color: #111827 !important;
	margin-left: 0 !important;
}
.body-sidebar .standard-sidebar-item:hover,
.body-sidebar .standard-sidebar-item.hover {
	background: #f3f4f6 !important;
}
.body-sidebar .standard-sidebar-item.active-sidebar,
.body-sidebar .standard-sidebar-item.selected,
.body-sidebar .active-sidebar {
	background: #f0f0f1 !important;
	box-shadow: none !important;
}
.body-sidebar .sidebar-item-control .drop-icon {
	width: 18px !important;
	height: 18px !important;
	color: #c4c4c4 !important;
}
.body-sidebar .sidebar-item-control .drop-icon svg,
.body-sidebar .sidebar-item-control .drop-icon .icon {
	width: 14px !important;
	height: 14px !important;
	stroke: #c4c4c4 !important;
}
.body-sidebar .section-break,
.body-sidebar .section-break .sidebar-item-label {
	font-size: 13px !important;
	font-weight: 500 !important;
	letter-spacing: 0 !important;
	text-transform: none !important;
	color: #111827 !important;
	margin-left: 0 !important;
}
.body-sidebar .nested-container {
	margin: 0 0 4px 14px !important;
	padding-left: 8px !important;
	border-left: 1px solid #ececec !important;
}
.body-sidebar .nested-container .standard-sidebar-item .item-anchor {
	height: 32px !important;
	min-height: 32px !important;
}
.body-sidebar .nested-container .sidebar-item-label {
	font-size: 13px !important;
	font-weight: 500 !important;
	color: #111827 !important;
}
`;

function inject_sidebar_css() {
	let style = document.getElementById("staff-pro-sidebar-css");
	if (!style) {
		style = document.createElement("style");
		style.id = "staff-pro-sidebar-css";
		document.head.appendChild(style);
	}
	style.textContent = SIDEBAR_CSS;
}

function shortcut_label($item) {
	if ($item.hasClass("navbar-modal-search-mobile") || $item.find("#icon-search, .icon-search").length) {
		return __("Search");
	}
	if ($item.hasClass("sidebar-notification") || $item.find("#icon-bell, .icon-bell").length) {
		return __("Alerts");
	}
	return "";
}

function dock_item_label($item) {
	return (
		($item.attr("aria-label") || "").trim() ||
		($item.attr("data-original-title") || "").trim() ||
		($item.data("original-title") || "").toString().trim() ||
		($item.attr("title") || "").trim() ||
		shortcut_label($item)
	);
}

function label_workspace_dock() {
	$(".workspace-dock button.workspace-dock-item").each(function () {
		const $item = $(this);
		const label = dock_item_label($item);
		if (!label) return;

		let $label = $item.children(".workspace-dock-label");
		if ($label.length) {
			if ($label.text() !== label) $label.text(label);
			return;
		}
		$item.append(
			`<span class="workspace-dock-label">${frappe.utils.escape_html(String(label))}</span>`
		);
	});
}

function add_sidebar_search() {
	const $header = $(".body-sidebar .sidebar-header").first();
	if (!$header.length || $header.next(".staff-pro-sidebar-search").length) return;

	const $search = $(`
		<div class="staff-pro-sidebar-search" role="button" tabindex="0">
			${frappe.utils.icon("search", "sm")}
			<span>${__("Search")}</span>
		</div>
	`);
	$search.on("click", () => {
		if (frappe.search?.open_awesomebar_from_global_search_shortcut) {
			frappe.search.open_awesomebar_from_global_search_shortcut({ preventDefault() {} });
		} else if (frappe.searchdialog?.search?.toggle_global_search_dialog) {
			frappe.searchdialog.search.toggle_global_search_dialog();
		}
	});
	$header.after($search);
}

function patch_workspace_dock() {
	const Dock = frappe.ui && frappe.ui.WorkspaceDock;
	if (!Dock || Dock.prototype._staff_pro_labeled) return;
	Dock.prototype._staff_pro_labeled = true;

	const orig = Dock.prototype.make_workspace_item;
	Dock.prototype.make_workspace_item = function (workspace) {
		const $item = orig.call(this, workspace);
		if ($item && $item.length) {
			const label = workspace.title || workspace.label || workspace.name || "";
			if (label && !$item.children(".workspace-dock-label").length) {
				$item.append(
					`<span class="workspace-dock-label">${frappe.utils.escape_html(String(label))}</span>`
				);
			}
		}
		return $item;
	};
}

function watch_workspace_dock() {
	inject_sidebar_css();
	patch_workspace_dock();
	label_workspace_dock();
	add_sidebar_search();

	const dock = document.querySelector(".workspace-dock");
	const sidebar = document.querySelector(".body-sidebar");
	if (!dock && !sidebar) {
		setTimeout(watch_workspace_dock, 200);
		return;
	}

	const observer = new MutationObserver(() => {
		label_workspace_dock();
		add_sidebar_search();
	});
	if (dock) observer.observe(dock, { childList: true, subtree: true });
	if (sidebar) observer.observe(sidebar, { childList: true, subtree: true });
}

$(document).on("app_ready", watch_workspace_dock);

if (typeof frappe !== "undefined" && $(".workspace-dock, .body-sidebar").length) {
	watch_workspace_dock();
}

function redirect_single_app_screen() {
	// Skip the multi-app picker when Staff Pro BPO is the only visible app.
	const route = frappe.get_route?.() || [];
	const path = window.location.pathname || "";
	const on_apps = route[0] === "apps" || path === "/apps" || path.endsWith("/apps");
	if (!on_apps) return;

	const apps = frappe.boot?.apps || [];
	if (apps.length === 1 && apps[0]?.name === "hrms") {
		const home = apps[0].route || "/desk/workforce";
		window.location.href = home;
	}
}

$(document).on("app_ready", redirect_single_app_screen);
$(document).on("page-change", redirect_single_app_screen);
