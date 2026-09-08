const SIDEBAR_CSS = `
.workspace-dock,
.dock,
.body-sidebar,
.body-sidebar-container {
	font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif !important;
	-webkit-font-smoothing: antialiased !important;
}

html, body {
	min-height: 100% !important;
	min-height: 100vh !important;
	min-height: 100dvh !important;
}

/* Dock — Frappe v17 uses .dock; older builds used .workspace-dock */
.workspace-dock,
.dock {
	align-self: stretch !important;
	position: sticky !important;
	top: 0 !important;
	bottom: 0 !important;
	flex: 0 0 72px !important;
	width: 72px !important;
	height: 100% !important;
	min-height: 100vh !important;
	min-height: 100dvh !important;
	max-height: none !important;
	display: flex !important;
	flex-direction: column !important;
	align-items: center !important;
	background: #ffffff !important;
	border-right: 1px solid #ececec !important;
	padding: 10px 0 12px !important;
}
body.staff-pro-has-topbar .workspace-dock,
body.staff-pro-has-topbar .dock {
	min-height: calc(100vh - var(--staff-pro-topbar-height, 56px)) !important;
	min-height: calc(100dvh - var(--staff-pro-topbar-height, 56px)) !important;
}
.workspace-dock .workspace-dock-logo,
.dock .dock-logo {
	height: auto !important;
	padding: 4px 0 8px !important;
}
.workspace-dock .workspace-dock-logo a,
.dock .dock-logo a {
	width: 32px !important;
	height: 32px !important;
	border-radius: 8px !important;
	overflow: hidden !important;
}
.workspace-dock .workspace-dock-items,
.workspace-dock .workspace-dock-shortcuts,
.workspace-dock .staff-pro-dock-integrations,
.dock .dock-items,
.dock .dock-shortcuts,
.dock .staff-pro-dock-integrations {
	width: 100% !important;
	padding: 0 4px !important;
	gap: 4px !important;
	align-items: center !important;
}
.workspace-dock .workspace-dock-items,
.dock .dock-items {
	flex: 1 1 auto !important;
	min-height: 0 !important;
	overflow-y: auto !important;
	scrollbar-width: none !important;
}
.workspace-dock .workspace-dock-items::-webkit-scrollbar,
.dock .dock-items::-webkit-scrollbar {
	display: none !important;
}
.workspace-dock .staff-pro-dock-integrations,
.dock .staff-pro-dock-integrations {
	flex: 0 0 auto !important;
	display: flex !important;
	flex-direction: column !important;
	padding-bottom: 4px !important;
}
.workspace-dock > .workspace-dock-item,
.workspace-dock .workspace-dock-items > .workspace-dock-item,
.workspace-dock .workspace-dock-shortcuts > .workspace-dock-item,
.workspace-dock .staff-pro-dock-integrations > .workspace-dock-item,
.dock > .dock-item,
.dock .dock-items > .dock-item,
.dock .dock-shortcuts > .dock-item,
.dock .staff-pro-dock-integrations > .dock-item,
.dock .staff-pro-dock-integrations > .workspace-dock-item {
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
.workspace-dock button.workspace-dock-item,
.dock button.dock-item,
.dock button.workspace-dock-item {
	display: flex !important;
	flex-direction: column !important;
	align-items: center !important;
	justify-content: flex-start !important;
	width: 56px !important;
	height: auto !important;
	min-height: 64px !important;
	padding: 6px 2px 6px !important;
	gap: 5px !important;
	border: 0 !important;
	border-radius: 8px !important;
	background: transparent !important;
	box-shadow: none !important;
	overflow: visible !important;
	color: #000000 !important;
	font-size: 11px !important;
	line-height: 1.15 !important;
	text-indent: 0 !important;
	text-transform: none !important;
}
.workspace-dock button.workspace-dock-item::after,
.dock button.dock-item::after,
.dock button.workspace-dock-item::after {
	content: attr(aria-label) !important;
	display: block !important;
	width: 100% !important;
	max-width: 64px !important;
	margin-top: 2px !important;
	font-size: 11px !important;
	font-weight: 500 !important;
	line-height: 1.15 !important;
	letter-spacing: 0 !important;
	color: #000000 !important;
	text-align: center !important;
	white-space: normal !important;
	word-break: break-word !important;
	text-transform: none !important;
}
.workspace-dock button.workspace-dock-item:has(.workspace-dock-label)::after,
.dock button.dock-item:has(.workspace-dock-label)::after,
.dock button.dock-item:has(.dock-label)::after,
.dock button.workspace-dock-item:has(.workspace-dock-label)::after {
	content: none !important;
	display: none !important;
}
.workspace-dock .workspace-dock-icon,
.workspace-dock button.workspace-dock-item .sidebar-item-icon,
.dock .dock-icon,
.dock button.dock-item .sidebar-item-icon {
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	flex-shrink: 0 !important;
}
.workspace-dock .workspace-dock-item svg,
.workspace-dock .workspace-dock-item .icon,
.workspace-dock .workspace-dock-item img,
.dock .dock-item svg,
.dock .dock-item .icon,
.dock .dock-item img {
	display: block !important;
	width: 22px !important;
	height: 22px !important;
	min-width: 22px !important;
	min-height: 22px !important;
	color: #000000 !important;
}
.workspace-dock .staff-pro-dock-integrations .workspace-dock-item img,
.workspace-dock .staff-pro-dock-integrations .workspace-dock-item svg,
.workspace-dock button.workspace-dock-item.staff-pro-dock-brand-icon img,
.dock .staff-pro-dock-integrations .dock-item img,
.dock .staff-pro-dock-integrations .workspace-dock-item img,
.dock button.dock-item.staff-pro-dock-brand-icon img {
	width: 22px !important;
	height: 22px !important;
	min-width: 22px !important;
	min-height: 22px !important;
	color: unset !important;
	object-fit: contain !important;
	border-radius: 5px !important;
}
.workspace-dock button.workspace-dock-item:hover,
.dock button.dock-item:hover {
	background: #ececee !important;
}
.workspace-dock button.workspace-dock-item.active,
.dock button.dock-item.active {
	background: #e8e8ea !important;
	color: #000000 !important;
}
.workspace-dock button.workspace-dock-item.active::before,
.dock button.dock-item.active::before {
	display: none !important;
}
.workspace-dock .workspace-dock-label,
.workspace-dock button.workspace-dock-item .workspace-dock-label,
.dock .dock-label,
.dock button.dock-item .workspace-dock-label,
.dock button.dock-item .dock-label {
	display: block !important;
	width: 100% !important;
	max-width: 56px !important;
	margin-top: 2px !important;
	font-size: 11px !important;
	font-weight: 500 !important;
	line-height: 1.15 !important;
	letter-spacing: 0 !important;
	color: #000000 !important;
	text-align: center !important;
	white-space: normal !important;
	overflow: hidden !important;
	word-break: break-word !important;
}
.workspace-dock .workspace-dock-shortcuts .workspace-dock-item,
.workspace-dock .staff-pro-dock-integrations .workspace-dock-item,
.dock .dock-shortcuts .dock-item,
.dock .staff-pro-dock-integrations .dock-item,
.dock .staff-pro-dock-integrations .workspace-dock-item {
	min-height: 56px !important;
	padding: 4px 2px 4px !important;
}
.workspace-dock .workspace-dock-divider,
.dock .dock-divider {
	width: 28px !important;
	height: 1px !important;
	margin: 8px auto !important;
	background: #e5e7eb !important;
}
.workspace-dock .staff-pro-integrations-divider,
.dock .staff-pro-integrations-divider {
	flex: 0 0 auto !important;
}
.dock .dock-shortcuts:empty,
.dock .dock-shortcuts:empty + .dock-divider {
	display: none !important;
}
.dock .dock-user {
	width: 32px !important;
	height: 32px !important;
	margin-top: 4px !important;
	padding: 0 !important;
	border: 0 !important;
	background: transparent !important;
}

:root {
	--sidebar-width: 260px;
}

/* Pin workspace submenus next to the dock — Frappe overlays .body-sidebar
   (position: absolute) over a 100vh placeholder. Forcing relative put the
   panel back in a column flex, so the placeholder stacked above it and the
   submenu landed at the bottom of the page. */
.body-sidebar-container {
	align-self: stretch !important;
	position: sticky !important;
	top: 0 !important;
	bottom: 0 !important;
	display: flex !important;
	flex-direction: row !important;
	flex-wrap: nowrap !important;
	align-items: stretch !important;
	height: 100% !important;
	min-height: 100vh !important;
	min-height: 100dvh !important;
	max-height: none !important;
	overflow: hidden !important;
}
body.staff-pro-has-topbar .body-sidebar-container {
	min-height: calc(100vh - var(--staff-pro-topbar-height, 56px)) !important;
	min-height: calc(100dvh - var(--staff-pro-topbar-height, 56px)) !important;
}

/* Body sidebar */
.body-sidebar {
	position: relative !important;
	top: 0 !important;
	bottom: 0 !important;
	align-self: stretch !important;
	height: 100% !important;
	min-height: 100% !important;
	max-height: none !important;
	overflow-x: hidden !important;
	overflow-y: auto !important;
	background: #ffffff !important;
	border-right: 1px solid #ececec !important;
	padding: 8px 8px 10px !important;
}
.body-sidebar-container.expanded .body-sidebar {
	width: var(--sidebar-width, 260px) !important;
}
.body-sidebar-container.expanded .body-sidebar-placeholder {
	display: none !important;
	width: 0 !important;
	height: 0 !important;
	flex: 0 0 0 !important;
}
.body-sidebar .sidebar-header {
	display: flex !important;
	align-items: center !important;
	padding: 14px 36px 10px 8px !important;
	margin: 0 0 2px !important;
}
.body-sidebar .sidebar-header .drop-icon {
	display: none !important;
}
.body-sidebar .sidebar-header .header-icon,
.body-sidebar .sidebar-header > img,
.body-sidebar .sidebar-header .sidebar-item-icon {
	display: none !important;
}
.body-sidebar .sidebar-header .header-title,
.body-sidebar .sidebar-header .workspace-title,
.body-sidebar .sidebar-header span:not(.drop-icon):not(.icon):not(.sidebar-item-icon) {
	font-size: 11px !important;
	font-weight: 700 !important;
	letter-spacing: 0.06em !important;
	text-transform: uppercase !important;
	color: #2c2e30 !important;
	line-height: 1.3 !important;
}
.body-sidebar .sidebar-items {
	padding: 0 2px 8px !important;
}
.body-sidebar .standard-sidebar-item {
	margin: 0 !important;
	padding: 0 !important;
	border-radius: 8px !important;
	overflow: visible !important;
	background: transparent !important;
	box-shadow: none !important;
}
.body-sidebar .standard-sidebar-item .item-anchor {
	display: flex !important;
	flex-direction: row !important;
	align-items: center !important;
	height: auto !important;
	min-height: 44px !important;
	padding: 10px 8px !important;
	gap: 10px !important;
	color: #2c2e30 !important;
	text-decoration: none !important;
}
.body-sidebar .standard-sidebar-item .sidebar-item-icon {
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	width: 28px !important;
	height: 28px !important;
	min-width: 28px !important;
	padding: 0 !important;
	margin: 0 !important;
	border-radius: 50% !important;
	background: #0f1b2d !important;
	color: var(--sp-icon-accent, #90ba93) !important;
	flex-shrink: 0 !important;
}
.body-sidebar .standard-sidebar-item .sidebar-item-icon svg,
.body-sidebar .standard-sidebar-item .sidebar-item-icon .icon,
.body-sidebar .standard-sidebar-item .sidebar-item-icon .text-ink-gray-7,
.body-sidebar .standard-sidebar-item .sidebar-item-icon .current-color {
	width: 14px !important;
	height: 14px !important;
	color: inherit !important;
}
.body-sidebar .standard-sidebar-item .sidebar-item-icon:not(.staff-pro-glyph) svg,
.body-sidebar .standard-sidebar-item .sidebar-item-icon:not(.staff-pro-glyph) svg * {
	stroke: currentColor !important;
	stroke-width: 1.85 !important;
	fill: none !important;
}
.body-sidebar .standard-sidebar-item .sidebar-item-icon.staff-pro-glyph svg,
.body-sidebar .standard-sidebar-item .sidebar-item-icon.staff-pro-glyph svg * {
	width: 14px !important;
	height: 14px !important;
	fill: currentColor !important;
	stroke: none !important;
}
.body-sidebar .standard-sidebar-item .sidebar-item-icon.staff-pro-section-icon svg,
.body-sidebar .standard-sidebar-item .sidebar-item-icon.staff-pro-section-icon svg * {
	width: 14px !important;
	height: 14px !important;
	stroke: currentColor !important;
	fill: none !important;
	stroke-width: 1.85 !important;
}
.body-sidebar .standard-sidebar-item .sidebar-item-icon:empty::before {
	content: "";
	width: 8px;
	height: 8px;
	border-radius: 3px 7px 4px 6px;
	background: currentColor;
}
.body-sidebar .standard-sidebar-item .sidebar-item-label {
	flex: 1 1 auto !important;
	font-size: 14px !important;
	font-weight: 500 !important;
	line-height: 1.35 !important;
	letter-spacing: 0 !important;
	color: #2c2c2c !important;
	margin-left: 0 !important;
}
.body-sidebar .standard-sidebar-item:hover,
.body-sidebar .standard-sidebar-item.hover {
	background: transparent !important;
}
.body-sidebar .standard-sidebar-item:not(:has(.drop-icon)):not(:has(.section-break)):hover,
.body-sidebar .standard-sidebar-item:not(:has(.drop-icon)):not(:has(.section-break)).hover {
	background: #f4f5f7 !important;
}
.body-sidebar .standard-sidebar-item.active-sidebar,
.body-sidebar .standard-sidebar-item.selected,
.body-sidebar .active-sidebar {
	background: transparent !important;
	box-shadow: none !important;
}
.body-sidebar .standard-sidebar-item:not(:has(.drop-icon)):not(:has(.section-break)).active-sidebar,
.body-sidebar .standard-sidebar-item:not(:has(.drop-icon)):not(:has(.section-break)).selected {
	background: #f4f5f7 !important;
}
.body-sidebar .standard-sidebar-item:not(:has(.drop-icon)).active-sidebar .sidebar-item-label,
.body-sidebar .standard-sidebar-item:not(:has(.drop-icon)).selected .sidebar-item-label {
	font-weight: 700 !important;
}
.body-sidebar .sidebar-item-control {
	margin-left: auto !important;
	display: flex !important;
	align-items: center !important;
}
.body-sidebar .sidebar-item-control .drop-icon {
	width: 18px !important;
	height: 18px !important;
	color: #b0b4ba !important;
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	position: relative !important;
}
.body-sidebar .sidebar-item-control .drop-icon svg,
.body-sidebar .sidebar-item-control .drop-icon .icon {
	display: none !important;
}
.body-sidebar .sidebar-item-control .drop-icon::after {
	content: "" !important;
	width: 6px !important;
	height: 6px !important;
	border-right: 1.5px solid #b0b4ba !important;
	border-bottom: 1.5px solid #b0b4ba !important;
	transform: rotate(-135deg) !important;
	margin-top: 2px !important;
}
.body-sidebar .sidebar-item-control .drop-icon[data-state="closed"]::after {
	transform: rotate(45deg) !important;
	margin-top: -3px !important;
}
.body-sidebar .section-break,
.body-sidebar .section-break .sidebar-item-label {
	font-size: 14px !important;
	font-weight: 500 !important;
	letter-spacing: 0 !important;
	text-transform: none !important;
	color: #2c2e30 !important;
	margin-left: 0 !important;
}
.body-sidebar .indent + .nested-container,
.body-sidebar .nested-container {
	margin: 0 0 6px !important;
	padding: 0 !important;
	border: 0 !important;
	border-left: 0 !important;
}
.body-sidebar .nested-container.hidden {
	display: none !important;
	margin: 0 !important;
}
.body-sidebar .nested-container .standard-sidebar-item {
	margin: 0 0 2px !important;
	border-radius: 8px !important;
	overflow: hidden !important;
}
.body-sidebar .nested-container .standard-sidebar-item .item-anchor {
	height: auto !important;
	min-height: 34px !important;
	padding: 6px 10px 6px 36px !important;
	gap: 8px !important;
}
.body-sidebar .nested-container .sidebar-item-icon,
.body-sidebar .nested-container .staff-pro-sub-icon {
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	width: 16px !important;
	height: 16px !important;
	min-width: 16px !important;
	border-radius: 0 !important;
	background: transparent !important;
	color: #8b8f94 !important;
}
.body-sidebar .nested-container .sidebar-item-icon svg,
.body-sidebar .nested-container .sidebar-item-icon .icon,
.body-sidebar .nested-container .sidebar-item-icon svg * {
	width: 14px !important;
	height: 14px !important;
	stroke: #8b8f94 !important;
	fill: none !important;
	stroke-width: 1.7 !important;
}
.body-sidebar .nested-container .sidebar-item-label {
	font-size: 13px !important;
	font-weight: 400 !important;
	line-height: 1.35 !important;
	color: #000000 !important;
}
.body-sidebar .nested-container .standard-sidebar-item:hover,
.body-sidebar .nested-container .standard-sidebar-item.hover {
	background: #f4f5f7 !important;
}
.body-sidebar .nested-container .standard-sidebar-item.active-sidebar,
.body-sidebar .nested-container .standard-sidebar-item.selected {
	background: #f4f5f7 !important;
	box-shadow: none !important;
}
.body-sidebar .nested-container .standard-sidebar-item:hover .sidebar-item-label,
.body-sidebar .nested-container .standard-sidebar-item.active-sidebar .sidebar-item-label,
.body-sidebar .nested-container .standard-sidebar-item.selected .sidebar-item-label {
	font-weight: 700 !important;
	color: #2c2c2c !important;
}
.body-sidebar .nested-container .standard-sidebar-item.active-sidebar .sidebar-item-icon,
.body-sidebar .nested-container .standard-sidebar-item.selected .sidebar-item-icon,
.body-sidebar .nested-container .standard-sidebar-item:hover .sidebar-item-icon {
	color: #2c2c2c !important;
}
.body-sidebar .nested-container .standard-sidebar-item.active-sidebar .sidebar-item-icon svg,
.body-sidebar .nested-container .standard-sidebar-item.active-sidebar .sidebar-item-icon svg *,
.body-sidebar .nested-container .standard-sidebar-item.selected .sidebar-item-icon svg,
.body-sidebar .nested-container .standard-sidebar-item.selected .sidebar-item-icon svg *,
.body-sidebar .nested-container .standard-sidebar-item:hover .sidebar-item-icon svg,
.body-sidebar .nested-container .standard-sidebar-item:hover .sidebar-item-icon svg * {
	stroke: #2c2c2c !important;
}
.body-sidebar .collapse-sidebar-link,
.body-sidebar .collapse-sidebar-link.sidebar-toggle-btn {
	position: absolute !important;
	top: 12px !important;
	right: 6px !important;
	z-index: 3 !important;
	display: inline-flex !important;
	align-items: center !important;
	justify-content: center !important;
	width: 24px !important;
	height: 24px !important;
	margin: 0 !important;
	padding: 0 !important;
	color: #000000 !important;
	background: transparent !important;
	border: 0 !important;
	box-shadow: none !important;
	cursor: pointer !important;
}
.body-sidebar .collapse-sidebar-link svg,
.body-sidebar .collapse-sidebar-link .icon,
.body-sidebar .collapse-sidebar-link svg * {
	width: 16px !important;
	height: 16px !important;
	color: #000000 !important;
	stroke: #000000 !important;
	fill: none !important;
}
.body-sidebar-container:not(.expanded) {
	width: 0 !important;
	height: 0 !important;
	min-height: 0 !important;
	max-height: none !important;
	overflow: visible !important;
}
.body-sidebar-container:not(.expanded) .body-sidebar-placeholder {
	width: 0 !important;
	height: 0 !important;
}
.body-sidebar-container:not(.expanded) .body-sidebar {
	width: 0 !important;
	height: 0 !important;
	min-height: 0 !important;
	background: transparent !important;
	border-right-color: transparent !important;
	pointer-events: none;
}
.body-sidebar-container:not(.expanded) .body-sidebar .collapse-sidebar-link {
	pointer-events: auto !important;
}

body.staff-pro-hide-form-sidebar .layout-side-section.right,
body.staff-pro-hide-form-sidebar .page-head .sidebar-toggle-btn,
body.staff-pro-hide-form-sidebar .layout-main .sidebar-toggle-btn:not(.collapse-sidebar-link) {
	display: none !important;
}
body.staff-pro-hide-form-sidebar .layout-main.layout-two-column {
	display: flex;
}
body.staff-pro-hide-form-sidebar .layout-main-section-wrapper {
	flex: 1 1 100% !important;
	width: 100% !important;
	max-width: 100% !important;
}
.form-footer .staff-pro-hide-new-email,
.form-footer .timeline-actions,
.form-footer .timeline-item.timeline-action,
.form-footer .document-email-link-container {
	display: none !important;
}
.page-head .menu-btn-group,
.page-head .menu-more-button {
	display: none !important;
}
.frappe-menu.context-menu .dropdown-menu-item.staff-pro-hide-help {
	display: none !important;
}
[id^="page-List/"] .view-switcher,
[id^="page-List/"] .views-switcher,
[id^="page-List/"] .page-actions .custom-actions:not(:has(> :not(.view-switcher, .views-switcher))) {
	display: none !important;
}
.match-type-dropdown-btn,
.standard-filter-section .input-group-btn:has(.match-type-dropdown-btn),
.filter-box .input-group-btn:has(.match-type-dropdown-btn),
.filter-field .input-group-btn:has(.match-type-dropdown-btn) {
	display: none !important;
}
.standard-filter-section .input-group .form-control,
.standard-filter-section .input-group input,
.standard-filter-section .input-group select,
.filter-box .input-group .form-control,
.filter-field .input-group .form-control {
	border-top-left-radius: 6px !important;
	border-bottom-left-radius: 6px !important;
}
[id="page-Employee"] .form-sidebar .modified-by,
[id="page-Employee"] .form-sidebar .created-by,
[id="page-Employee"] .form-sidebar .sidebar-section:has(.modified-by),
[id="page-Employee"] .form-sidebar .sidebar-section.text-muted.pt-3 {
	display: none !important;
}
.form-sidebar .form-attachments,
.form-sidebar .form-tags,
.form-sidebar .form-shared,
.form-sidebar .sidebar-section.form-attachments,
.form-sidebar .sidebar-section.form-tags,
.form-sidebar .sidebar-section.form-shared {
	display: none !important;
}

/* Hide Frappe module onboarding (Getting Started / Accounting Onboarding) everywhere */
.user-onboarding,
.onb-panel,
.body-sidebar .onboarding-sidebar,
.onboarding-widget-box,
.widget.onboarding-widget,
.workspace-page .onboarding-widget {
	display: none !important;
}
`;

const PARENT_GLYPHS = {
	home: `<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 1.2 1.6 7.1v7.2h4.2V9.8h4.4v4.5h4.2V7.1L8 1.2z"/></svg>`,
	bowtie: `<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M2.1 3.05c0-.72.58-1.15 1.32-1.15h9.16c.74 0 1.32.43 1.32 1.15 0 .38-.16.72-.48 1.04L9.7 8l3.72 3.91c.32.32.48.66.48 1.04 0 .72-.58 1.15-1.32 1.15H3.42c-.74 0-1.32-.43-1.32-1.15 0-.38.16-.72.48-1.04L6.3 8 2.58 4.09A1.4 1.4 0 0 1 2.1 3.05z"/></svg>`,
	chevron: `<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M3.05 2.7 8.7 8 3.05 13.3l1.7 1.6L12.2 8 4.75 1.1 3.05 2.7z"/></svg>`,
	bars: `<svg viewBox="0 0 16 16" aria-hidden="true"><rect fill="currentColor" x="1.7" y="9.1" width="3.5" height="5.1" rx="1"/><rect fill="currentColor" x="6.25" y="5.6" width="3.5" height="8.6" rx="1"/><rect fill="currentColor" x="10.8" y="2.6" width="3.5" height="11.6" rx="1"/></svg>`,
	person: `<svg viewBox="0 0 16 16" aria-hidden="true"><circle fill="currentColor" cx="8" cy="4.7" r="2.75"/><path fill="currentColor" d="M2.45 14.15c.25-3.05 2.3-4.8 5.55-4.8s5.3 1.75 5.55 4.8H2.45z"/></svg>`,
	leaf: `<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M13.7 2.45c-3.9-.55-8.35 1.25-9.75 5.35-1 2.85.25 5.5 2.7 6.55 2.65 1.15 5.7-.15 7.15-2.85 1.65-2.9 1.4-8.45-.1-9.05z"/></svg>`,
	plus: `<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M6.35 2.15h3.3v4.05h4.05v3.3H9.65v4.05h-3.3V9.5H2.3V6.2h4.05V2.15z"/></svg>`,
	diamond: `<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 1.45 14.55 8 8 14.55 1.45 8 8 1.45z"/></svg>`,
	clock: `<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 1.35a6.65 6.65 0 1 0 0 13.3 6.65 6.65 0 0 0 0-13.3zm.75 3.35H7.1v4.2l3.35 2 .85-1.35-2.55-1.5V4.7z"/></svg>`,
	wallet: `<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M2.15 4.35h11.7v1.45H3.55v7.9H2.15V4.35zm1.85 2.25h9.9c.7 0 1.25.5 1.25 1.2v5.1c0 .7-.55 1.2-1.25 1.2H4c-.7 0-1.25-.5-1.25-1.2v-5.1c0-.7.55-1.2 1.25-1.2zm7.7 2.25a1.15 1.15 0 1 0 0 2.3 1.15 1.15 0 0 0 0-2.3z"/></svg>`,
	gear: `<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M6.55 1.55h2.9l.35 1.55 1.45.6 1.5-.9 2.05 2.05-.9 1.5.6 1.45 1.55.35v2.9l-1.55.35-.6 1.45.9 1.5-2.05 2.05-1.5-.9-1.45.6-.35 1.55h-2.9l-.35-1.55-1.45-.6-1.5.9-2.05-2.05.9-1.5-.6-1.45L1.55 9.45v-2.9l1.55-.35.6-1.45-.9-1.5 2.05-2.05 1.5.9 1.45-.6.35-1.55zM8 6.15A1.85 1.85 0 1 0 8 9.85 1.85 1.85 0 0 0 8 6.15z"/></svg>`,
	grid: `<svg viewBox="0 0 16 16" aria-hidden="true"><rect fill="currentColor" x="1.9" y="1.9" width="5.3" height="5.3" rx="1.2"/><rect fill="currentColor" x="8.8" y="1.9" width="5.3" height="5.3" rx="1.2"/><rect fill="currentColor" x="1.9" y="8.8" width="5.3" height="5.3" rx="1.2"/><rect fill="currentColor" x="8.8" y="8.8" width="5.3" height="5.3" rx="1.2"/></svg>`,
	plane: `<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M14.7 8 2.15 2.7l.65 4.25 5.3 1.05-5.3 1.05-.65 4.25L14.7 8z"/></svg>`,
	file: `<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M3.9 1.7h5.3L13.1 5.6v8.7c0 .55-.45 1-1 1H3.9c-.55 0-1-.45-1-1V2.7c0-.55.45-1 1-1zm4.7.85v3.45h3.45L8.6 2.55z"/></svg>`,
};

const PARENT_STYLES = [
	{ test: /^dashboard$/i, glyph: "home", hue: "#90BA93" },
	{ test: /^employee$|^people$|^team$/i, glyph: "person", hue: "#11A5DD" },
	{ test: /organizational|org chart/i, glyph: "plus", hue: "#90BA93" },
	{ test: /onboarding|recruit|talent|hiring|job opening|job applicant|interview|job offer|appointment/i, glyph: "person", hue: "#11A5DD" },
	{ test: /separation|grievance/i, glyph: "person", hue: "#16678C" },
	{ test: /expense|bill|claim|advance/i, glyph: "chevron", hue: "#90BA93" },
	{ test: /payroll|pay$|salary|wallet/i, glyph: "wallet", hue: "#90BA93" },
	{ test: /tax|benefit|exemption/i, glyph: "leaf", hue: "#205B76" },
	{ test: /leave|holiday/i, glyph: "leaf", hue: "#90BA93" },
	{ test: /time|attendance|shift|roster|overtime|checkin/i, glyph: "clock", hue: "#11A5DD" },
	{ test: /performance|appraisal|goal|kra/i, glyph: "bars", hue: "#90BA93" },
	{ test: /accounting|account|journal|finance|chart of accounts/i, glyph: "bowtie", hue: "#90BA93" },
	{ test: /admin|role|permission|user$/i, glyph: "gear", hue: "#16678C" },
	{ test: /report/i, glyph: "bars", hue: "#11A5DD" },
	{ test: /setup|settings/i, glyph: "gear", hue: "#16678C" },
	{ test: /planning|staffing/i, glyph: "diamond", hue: "#11A5DD" },
	{ test: /marketing/i, glyph: "diamond", hue: "#11A5DD" },
];

const SUBMENU_ICONS = {
	"chart of accounts": "book",
	"journal entry": "book-open",
	"payment entry": "credit-card",
	"bank reconciliation tool": "landmark",
	"general ledger": "book-open",
	"profit and loss statement": "bar-chart-2",
	"trial balance": "scale",
	"accounts receivable": "arrow-down-left",
	"accounts payable": "arrow-up-right",
	user: "user",
	role: "shield",
	"role permission manager": "key",
	"system settings": "settings",
	"customize form": "sliders",
	"print format": "printer",
	"email account": "mail",
	"website settings": "globe",
	company: "building",
	branch: "git-branch",
	department: "network",
	designation: "badge",
	"employee group": "users",
	"employee grade": "layers",
	"employee skill map": "map",
	"grievance type": "flag",
	"training program": "graduation-cap",
	"training event": "calendar",
	"training feedback": "message-square",
	"training result": "check-circle",
	"employee exits": "log-out",
	"employee birthday": "cake",
	"employee information": "file-text",
	"employee analytics": "bar-chart-2",
	"unpaid expense claim": "alert-circle",
	"expense claim type": "tag",
	"leave balance": "calendar-check",
	"leave balance summary": "calendar-range",
	"employees working on a holiday": "sun",
	"holiday list": "calendar",
	"holiday list assignment": "calendar-plus",
	"leave period": "clock",
	"leave policy": "file-check",
	"leave block list": "slash",
	"leave type": "tag",
	"leave control panel": "sliders",
	"leave policy assignment": "user-check",
	"leave allocation": "pie-chart",
	"monthly attendance sheet": "calendar",
	"shift attendance": "clock",
	"employee hours utilization": "timer",
	"project profitability": "trending-up",
	"shift type": "layers",
	"shift location": "map-pin",
	"shift schedule": "calendar-range",
	"activity type": "tag",
	timesheet: "clock",
	"overtime type": "timer",
	"overtime slip": "file-text",
	"income tax computation": "calculator",
	"income tax deductions": "minus-circle",
	"professional tax deductions": "minus-circle",
	"accrued earnings report": "bar-chart-2",
	"income tax slab": "layers",
	"exemption category": "tag",
	"exemption declaration": "file-text",
	"exemption proof submission": "upload",
	"exemption submission proof": "upload",
	"benefit application": "heart",
	"benefit claim": "heart",
	"salary register": "book",
	"employee ctc break-up": "pie-chart",
	"salary component": "coins",
	"salary structure": "layers",
	"payroll settings": "settings",
	"hr settings": "settings",
	"job requisition": "file-plus",
	"staffing plan": "users",
	"employee referral": "user-plus",
	"recruitment analytics": "bar-chart-2",
	"interview type": "video",
	"job opening template": "file-text",
	"appointment letter template": "file-text",
	"job offer term template": "file-text",
	"job portal": "globe",
	"appraisal template": "file-text",
	kra: "target",
	"employee feedback criteria": "list",
	"appraisal overview": "bar-chart-2",
	"job opening": "user-round-plus",
	"job applicant": "circle-user-round",
	interview: "videotape",
	"job offer": "user-round-check",
	goal: "goal",
	"payroll entry": "banknote-arrow-up",
	"salary structure assignment": "hand-coins",
	"salary slip": "wallet",
	"expense claim": "arrow-down-from-line",
	"employee onboarding": "user-star",
	"employee separation": "user-round-minus",
	"employee grievance": "user-lock",
	"organizational chart": "building-2",
	"employee promotion": "graduation-cap",
	"employee performance feedback": "trending-up",
	"appraisal cycle": "orbit",
	"appointment letter": "file-text",
	"additional salary": "piggy-bank",
	"salary withholding": "banknote-x",
	"social security": "shield",
	"social security deductions": "shield",
	"ss contribution table": "shield",
	"social security contribution table": "shield",
	"employee advance": "upload",
	"employee checkin": "pointer",
	"attendance request": "calendar-check",
	"shift request": "bell-dot",
	"employee attendance tool": "wrench",
	"leave application": "clipboard-pen",
	"leave encashment": "coins",
	roster: "calendar-range",
	dashboard: "home",
	settings: "settings",
	agents: "square-user-round",
	"data analytics": "bar-chart-2",
	"in / out today": "log-in",
	"team structure": "building-2",
	"new hire onboarding": "user-star",
	offboarding: "user-round-minus",
	"concerns & escalations": "user-lock",
	"clock in/out": "pointer",
	"schedule correction": "calendar-check",
	"shift swap": "bell-dot",
	"bulk attendance": "wrench",
	"time off request": "clipboard-pen",
	"paid time off": "sun",
	"pto cash-out": "coins",
	"time off admin": "sliders-horizontal",
	"extra hours": "calendar-clock",
	"open positions": "user-round-plus",
	candidates: "circle-user-round",
	interviews: "videotape",
	"offer letters": "user-round-check",
	"qa feedback": "trending-up",
	"run payroll": "banknote-arrow-up",
	"pay stubs": "wallet",
	"current pay stubs": "wallet",
	"past pay stubs": "archive",
	reimbursements: "arrow-down-from-line",
	"cash advances": "upload",
	"client invoices": "receipt",
	clients: "building",
	"posted invoices": "file-text",
	"outstanding invoices": "arrow-down-left",
	"record payment": "credit-card",
	"unpaid reimbursements": "alert-circle",
};

const SECTION_ICONS = {
	accounting: "coins",
	admin: "settings",
	"leave admin": "sliders-horizontal",
	overtime: "calendar-clock",
	planning: "align-start-horizontal",
	reports: "notepad-text",
	setup: "database",
	"tax & benefits": "badge-alert",
	"social security": "shield",
	"other statutory": "landmark",
	"time off admin": "sliders-horizontal",
	"extra hours": "calendar-clock",
	"workforce planning": "align-start-horizontal",
};

const SUBMENU_KEYWORD_ICONS = [
	{ test: /account|ledger|journal/i, icon: "book-open" },
	{ test: /payment|bank|wallet|salary|pay/i, icon: "credit-card" },
	{ test: /report|analytic|overview/i, icon: "bar-chart-2" },
	{ test: /user|employee|driver/i, icon: "user" },
	{ test: /setting|setup/i, icon: "settings" },
	{ test: /template|letter|policy/i, icon: "file-text" },
	{ test: /calendar|holiday|leave|shift|roster/i, icon: "calendar" },
	{ test: /tax|benefit/i, icon: "tag" },
	{ test: /goal|appraisal|kra/i, icon: "target" },
	{ test: /job|interview|recruit/i, icon: "briefcase" },
	{ test: /department|branch|company/i, icon: "building" },
	{ test: /type|category|component/i, icon: "tag" },
];

function sidebar_item_label($item) {
	return ($item.find(".sidebar-item-label").first().text() || "").trim();
}

function sidebar_href_to_link(href) {
	if (!href) return "";
	try {
		const path = String(href).split("?")[0].replace(/\/$/, "");
		const parts = path.split("/").filter(Boolean);
		let last = parts[parts.length - 1] || "";
		if (!last || ["List", "view", "app", "desk"].includes(last)) {
			last = parts[parts.length - 2] || "";
		}
		if (!last) return "";
		if (last === "organizational-chart") return "organizational-chart";
		if (last === "paid-time-off") return "paid-time-off";
		return last
			.split("-")
			.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
			.join(" ");
	} catch (e) {
		return "";
	}
}

function bpo_sidebar_maps() {
	return frappe.boot?.staff_pro_bpo_sidebar_labels || { by_link: {}, by_label: {} };
}

function bpo_sidebar_label(currentLabel, href) {
	const maps = bpo_sidebar_maps();
	const linkKey = sidebar_href_to_link(href);
	if (linkKey && maps.by_link?.[linkKey]) {
		return maps.by_link[linkKey];
	}
	if (currentLabel && maps.by_label?.[currentLabel]) {
		return maps.by_label[currentLabel];
	}
	return currentLabel;
}

function apply_bpo_sidebar_label($item) {
	const $label = $item.find(".sidebar-item-label").first();
	if (!$label.length) return;

	const current = ($label.text() || "").trim();
	if (!current) return;
	if (current.toLowerCase() === "past pay stubs") return;

	const href = ($item.find(".item-anchor").attr("href") || "").trim();
	const next = bpo_sidebar_label(current, href);
	if (!next || next === current) return;

	$label.text(__(next));
	$item.attr("data-sp-bpo-label", next);
}

function parent_look(label) {
	for (const rule of PARENT_STYLES) {
		if (rule.test.test(label)) return rule;
	}
	return { glyph: "plus", hue: "#90BA93" };
}

function section_icon_name(label) {
	const key = label.toLowerCase();
	if (SECTION_ICONS[key]) return SECTION_ICONS[key];
	return submenu_icon_name(label);
}

function submenu_icon_name(label) {
	const key = label.toLowerCase();
	if (SUBMENU_ICONS[key]) return SUBMENU_ICONS[key];
	for (const rule of SUBMENU_KEYWORD_ICONS) {
		if (rule.test.test(label)) return rule.icon;
	}
	return "file-text";
}

function lucide_icon_html(name) {
	try {
		const html = frappe.utils.icon(name, "sm");
		if (html && String(html).includes("svg")) return html;
	} catch (e) {
		/* use fallback */
	}
	return `<svg class="icon icon-sm" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>`;
}

function apply_top_level_icon($item, $icon, label) {
	const look = parent_look(label);
	$item[0]?.style?.setProperty("--sp-icon-accent", look.hue);

	let iconName = "file-text";
	if (/^dashboard$/i.test(label)) {
		iconName = "home";
	} else {
		iconName = submenu_icon_name(label);
	}

	if ($icon.attr("data-sp-icon") === iconName && $icon.find("svg").length) {
		return;
	}

	$icon.removeClass("staff-pro-glyph staff-pro-sub-icon staff-pro-icon-fallback");
	$icon.addClass("staff-pro-section-icon");
	$icon.attr("data-sp-icon", iconName);
	$icon.html(lucide_icon_html(iconName));
}

function apply_section_icon($item, $icon, label) {
	const look = parent_look(label);
	$item[0].style.setProperty("--sp-icon-accent", look.hue);
	$icon.removeClass("staff-pro-glyph staff-pro-sub-icon staff-pro-icon-fallback");
	$icon.addClass("staff-pro-section-icon");
	const iconName = section_icon_name(label);
	$icon.attr("data-sp-icon", iconName);
	$icon.html(lucide_icon_html(iconName));
}

function apply_submenu_icon($icon, label) {
	const iconName = submenu_icon_name(label);
	if ($icon.attr("data-sp-icon") === iconName && $icon.find("svg").length) {
		return;
	}
	$icon.removeClass("staff-pro-glyph staff-pro-section-icon staff-pro-icon-fallback");
	$icon.addClass("staff-pro-sub-icon");
	$icon.attr("data-sp-icon", iconName);
	$icon.html(lucide_icon_html(iconName));
}

function is_section_header($item) {
	if ($item.hasClass("section-break") || $item.find(".section-break").length) {
		return true;
	}
	return Boolean($item.find(".sidebar-item-control .drop-icon").length && !$item.find(".item-anchor[href]").length);
}

function hidden_has(list, value) {
	if (!value || !list || !list.length) return false;
	const needle = String(value).toLowerCase();
	return list.some((item) => String(item).toLowerCase() === needle);
}

function is_hidden_sidebar_item($item) {
	const maps = bpo_sidebar_maps();
	const hiddenLabels = maps.hidden_labels || [];
	const hiddenLinks = maps.hidden_links || [];
	const label = sidebar_item_label($item);
	const href = ($item.find(".item-anchor").attr("href") || "").trim();

	// Section headers stay so nested BPO links (Clients, Posted Invoices) remain visible
	// until migrate replaces the Finance sidebar. Leaf ERP items are removed immediately.
	if (!is_section_header($item) && hidden_has(hiddenLabels, label)) {
		return true;
	}

	const linkKey = sidebar_href_to_link(href);
	if (hidden_has(hiddenLinks, linkKey) || hidden_has(hiddenLabels, linkKey)) {
		return true;
	}

	let path = href;
	try {
		path = decodeURIComponent(new URL(href, window.location.origin).pathname);
	} catch (e) {
		/* keep raw href */
	}
	const last = path.replace(/\/$/, "").split("/").filter(Boolean).pop() || "";
	if (hidden_has(hiddenLinks, last) || hidden_has(hiddenLinks, last.replace(/-/g, " "))) {
		return true;
	}
	return /\/query-report\/(General Ledger|Accounts Payable)\/?$/i.test(path);
}

const SIDEBAR_COLLAPSE_ICON = `<svg class="icon icon-sm" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="2" y="2.5" width="12" height="11" rx="1.5" stroke="#000000" stroke-width="1.5"/><path d="M6.25 2.5v11" stroke="#000000" stroke-width="1.5"/><path d="M11.2 6.15 8.7 8l2.5 1.85" stroke="#000000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const SIDEBAR_EXPAND_ICON = `<svg class="icon icon-sm" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="2" y="2.5" width="12" height="11" rx="1.5" stroke="#000000" stroke-width="1.5"/><path d="M6.25 2.5v11" stroke="#000000" stroke-width="1.5"/><path d="M8.7 6.15 11.2 8l-2.5 1.85" stroke="#000000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

function style_sidebar_collapse_toggle() {
	const sidebar = document.querySelector(".body-sidebar");
	if (!sidebar) return;

	const expanded = document.querySelector(".body-sidebar-container")?.classList.contains("expanded") !== false;
	const icon = expanded ? SIDEBAR_COLLAPSE_ICON : SIDEBAR_EXPAND_ICON;
	const state = expanded ? "expanded" : "collapsed";

	sidebar.querySelectorAll(".collapse-sidebar-link").forEach((btn) => {
		if (btn.getAttribute("data-sp-collapse") !== state || !btn.querySelector("svg")) {
			btn.setAttribute("data-sp-collapse", state);
			btn.innerHTML = icon;
		}
		if (!btn.dataset.spCollapseBound) {
			btn.dataset.spCollapseBound = "1";
			btn.addEventListener("click", (event) => event.stopPropagation());
		}
	});
}

function enhance_sidebar_menus() {
	style_sidebar_collapse_toggle();
	$(".body-sidebar .standard-sidebar-item").each(function () {
		const $item = $(this);
		if (is_hidden_sidebar_item($item)) {
			$item.closest(".sidebar-item-container").hide();
			return;
		}
		apply_bpo_sidebar_label($item);
		const nested = $item.closest(".nested-container").length > 0;
		const $anchor = $item.find(".item-anchor").first();
		const $target = $anchor.length ? $anchor : $item;

		const label = sidebar_item_label($item);
		if (!label) return;

		let $icon = $target.children(".sidebar-item-icon");
		if (!$icon.length) {
			$icon = $('<span class="sidebar-item-icon staff-pro-icon-fallback" aria-hidden="true"></span>');
			$target.prepend($icon);
		}

		if (nested) {
			apply_submenu_icon($icon, label);
		} else if (is_section_header($item)) {
			if ($item.attr("data-sp-section") !== label) {
				apply_section_icon($item, $icon, label);
				$item.attr("data-sp-section", label);
			}
		} else {
			apply_top_level_icon($item, $icon, label);
		}

		prefer_employee_image_sidebar_link($anchor);
		bind_pay_stubs_sidebar_item($item, $anchor, label);

		const $wrapper = $item.parent();
		const $nested = $wrapper.children(".nested-container");
		const $drop = $item.find(".sidebar-item-control .drop-icon").first();
		if ($drop.length && $nested.length) {
			const closed = $nested.hasClass("hidden");
			const next = closed ? "closed" : "opened";
			if ($drop.attr("data-state") !== next) {
				$drop.attr("data-state", next);
			}
		}
	});
	sync_pay_stubs_sidebar_state();
}

const PAY_STUBS_MODE_KEY = "staff_pro_pay_stubs_view";

function pay_stubs_sidebar_mode(label) {
	const key = (label || "").trim().toLowerCase();
	if (key === "past pay stubs") return "past";
	if (key === "current pay stubs" || key === "pay stubs") return "current";
	return "";
}

function bind_pay_stubs_sidebar_item($item, $anchor, label) {
	const mode = pay_stubs_sidebar_mode(label);
	if (!mode || !$anchor?.length) return;

	$anchor.attr("data-sp-pay-stubs", mode);
	$anchor.off("click.paystubs").on("click.paystubs", function (e) {
		e.preventDefault();
		e.stopPropagation();
		open_pay_stubs_list(mode);
	});
}

function open_pay_stubs_list(mode) {
	try {
		sessionStorage.setItem(PAY_STUBS_MODE_KEY, mode);
	} catch (err) {
		/* ignore */
	}
	frappe.route_options = {
		payment_status: mode === "past" ? "Paid" : "Not Paid",
	};

	const route = frappe.get_route() || [];
	const on_list = route[0] === "List" && route[1] === "Salary Slip";
	if (on_list && window.cur_list?.doctype === "Salary Slip") {
		if (typeof window.cur_list._staff_pro_pay_status !== "undefined") {
			window.cur_list._staff_pro_pay_status = null;
		}
		if (window.cur_list.filter_area) {
			window.cur_list.filter_area.remove("payment_status");
			window.cur_list.filter_area.add([
				[window.cur_list.doctype, "payment_status", "=", mode === "past" ? "Paid" : "Not Paid"],
			]);
		}
		if (typeof frappe.listview_settings["Salary Slip"]?.refresh === "function") {
			frappe.listview_settings["Salary Slip"].refresh(window.cur_list);
		}
		sync_pay_stubs_sidebar_state();
		return;
	}

	frappe.set_route("List", "Salary Slip");
}

function sync_pay_stubs_sidebar_state() {
	const route = frappe.get_route() || [];
	const on_list = route[0] === "List" && route[1] === "Salary Slip";
	if (!on_list) return;

	let mode = "current";
	try {
		mode = sessionStorage.getItem(PAY_STUBS_MODE_KEY) || "current";
	} catch (err) {
		mode = "current";
	}

	$(".body-sidebar .standard-sidebar-item").each(function () {
		const $item = $(this);
		const item_mode = pay_stubs_sidebar_mode(sidebar_item_label($item));
		if (!item_mode) return;
		$item.toggleClass("active-sidebar", item_mode === mode);
	});
}

function employee_image_view_href() {
	return "/desk/employee/view/image";
}

function is_employee_list_href(href) {
	if (!href) return false;
	try {
		const path = new URL(href, window.location.origin).pathname.replace(/\/$/, "") || "/";
		return /^\/(desk|app)\/employee(?:\/view\/list)?$/i.test(path);
	} catch (e) {
		return false;
	}
}

function prefer_employee_image_sidebar_link($anchor) {
	if (!$anchor?.length) return;
	const href = ($anchor.attr("href") || "").trim();
	if (!is_employee_list_href(href)) return;
	$anchor.attr("href", employee_image_view_href());
}

function inject_sidebar_css() {
	let style = document.getElementById("staff-pro-sidebar-css");
	if (!style) {
		style = document.createElement("style");
		style.id = "staff-pro-sidebar-css";
		document.head.appendChild(style);
	}
	style.textContent = SIDEBAR_CSS;
}

function staff_pro_brand() {
	return (
		frappe.boot?.staff_pro_brand || {
			title: "Staff Pro BPO",
			logo_url: "/assets/hrms/images/staff-pro-bpo-logo.png",
		}
	);
}

const HR_SIDEBARS = [
	"workforce",
	"people",
	"time",
	"pay",
	"payroll",
	"ss and taxes",
	"talent",
	"finance",
	"finance & admin",
	"finance and admin",
	"admin",
];

function staff_pro_is_hr_sidebar(name) {
	const key = String(name || "")
		.toLowerCase()
		.replace(/[-_]/g, " ");
	return HR_SIDEBARS.includes(key);
}

function staff_pro_hr_home_sidebar() {
	if (staff_pro_sidebar_payload("People")) return "People";
	if (staff_pro_sidebar_payload("Workforce")) return "Workforce";
	return "People";
}

function staff_pro_accounting_home_sidebar() {
	if (staff_pro_sidebar_payload("Finance")) return "Finance";
	if (staff_pro_sidebar_payload("Home")) return "Home";
	if (staff_pro_sidebar_payload("Invoicing")) return "Invoicing";
	if (staff_pro_sidebar_payload("Accounting")) return "Accounting";
	return "Finance";
}

function staff_pro_admin_home_sidebar() {
	if (staff_pro_sidebar_payload("Admin")) return "Admin";
	return "Admin";
}

function staff_pro_current_portal() {
	if (!should_use_staff_pro_desk_home()) return null;

	const path = (window.location.pathname || "").replace(/\/$/, "");
	const route = frappe.get_route?.() || [];

	if (path.startsWith("/app")) {
		return "admin";
	}

	if (is_already_on_staff_pro_desk_home(route)) {
		return "hr";
	}

	const workspaceRoute = route[0] === "Workspaces" ? route[route.length - 1] : route[0];
	if (staff_pro_is_hr_sidebar(workspaceRoute)) {
		return "hr";
	}

	if (staff_pro_is_hr_sidebar(frappe.app?.sidebar?.current_module || frappe.app?.sidebar?.sidebar_title)) {
		return "hr";
	}

	const routes = frappe.boot?.staff_pro_portal_routes || {};
	const accountingRoute = (routes.accounting || "/desk/finance").replace(/\/$/, "");
	if (path === accountingRoute || path.startsWith(`${accountingRoute}/`)) {
		return "accounting";
	}

	const app = frappe.app?.sidebar?.get_sidebar_app?.();
	if (app?.app_name === "hrms") return "hr";
	if (app?.app_name === "frappe") return "admin";
	if (app?.app_name === "erpnext") return "accounting";

	return "hr";
}

function staff_pro_can_access_hr() {
	return should_use_staff_pro_desk_home();
}

function shortcut_label($item) {
	if ($item.hasClass("staff-pro-dock-hr")) {
		return __("HR");
	}
	if ($item.hasClass("staff-pro-dock-accounting")) {
		return __("Accounting");
	}
	if ($item.hasClass("staff-pro-dock-admin")) {
		return __("Admin");
	}
	if ($item.hasClass("navbar-modal-search-mobile") || $item.find("#icon-search, .icon-search").length) {
		return __("Search");
	}
	if ($item.hasClass("sidebar-notification") || $item.find("#icon-bell, .icon-bell").length) {
		return __("Alerts");
	}
	return "";
}

function staff_pro_portal_route(key) {
	const routes = frappe.boot?.staff_pro_portal_routes || {};
	return routes[key] || (key === "accounting" ? "/desk/finance" : "/desk/admin");
}

function staff_pro_can_access_accounting() {
	if (frappe.session.user === "Administrator") return true;
	return frappe.user.has_role(["Accounts User", "Accounts Manager"]);
}

function staff_pro_can_access_admin() {
	if (frappe.session.user === "Administrator") return true;
	return frappe.user.has_role(["System Manager", "Workspace Manager"]);
}

function staff_pro_clear_pinned_sidebar() {
	const sidebar = frappe.app?.sidebar;
	if (sidebar) sidebar._staff_pro_pinned_sidebar = null;
}

function staff_pro_remember_sidebar(name) {
	if (!name) return;
	try {
		localStorage.setItem("selected_sidebar", name);
		localStorage.setItem("selected_module", name);
	} catch (e) {
		/* ignore */
	}
}

function staff_pro_activate_sidebar(name) {
	const sidebar = frappe.app?.sidebar;
	staff_pro_remember_sidebar(name);
	if (!sidebar || !name) return;
	sidebar._staff_pro_pinned_sidebar = name;
	sidebar.open?.();
	if (typeof sidebar.select_module === "function") {
		sidebar.select_module(name);
	} else if (staff_pro_sidebar_payload(name) && typeof sidebar.select_sidebar === "function") {
		sidebar.select_sidebar(name);
	}
	sidebar.refresh_header?.();
	sidebar.refresh_dock?.();
}

function staff_pro_open_portal(key) {
	const homeSidebar =
		key === "hr"
			? staff_pro_hr_home_sidebar()
			: key === "accounting"
				? staff_pro_accounting_home_sidebar()
				: key === "admin"
					? staff_pro_admin_home_sidebar()
					: null;
	if (homeSidebar) {
		staff_pro_activate_sidebar(homeSidebar);
	} else {
		staff_pro_clear_pinned_sidebar();
	}

	const route = typeof key === "string" && !key.startsWith("/") ? staff_pro_portal_route(key) : key;
	if (!route) return;
	window.location.href = route;
}

function staff_pro_dock_shortcuts() {
	const portal = staff_pro_current_portal();
	const shortcuts = [];

	if (portal !== "hr") {
		shortcuts.push({
			name: "hr",
			icon: "briefcase",
			label: __("HR"),
			css_class: "staff-pro-dock-hr",
			condition: () => staff_pro_can_access_hr(),
			on_click: () => staff_pro_open_portal("hr"),
		});
	}

	return shortcuts;
}

const STAFF_PRO_INTEGRATIONS_FALLBACK = [
	{
		name: "whatsapp",
		label: "WhatsApp",
		url: "https://web.whatsapp.com",
		icon: "/assets/hrms/images/integrations/whatsapp.svg",
	},
	{
		name: "freshdesk",
		label: "Freshdesk",
		url: "https://freshdesk.com/login",
		icon: "/assets/hrms/images/integrations/freshdesk.svg",
	},
];

function staff_pro_integrations() {
	const fromBoot = frappe.boot?.staff_pro_integrations;
	const items = Array.isArray(fromBoot) && fromBoot.length ? fromBoot : STAFF_PRO_INTEGRATIONS_FALLBACK;
	return items
		.filter((item) => {
			const name = String(item.name || "").toLowerCase();
			return name !== "quickbooks" && name !== "teams";
		})
		.map((item) => {
			const fallback =
				STAFF_PRO_INTEGRATIONS_FALLBACK.find((row) => row.name === item.name) || {};
			const name = item.name || fallback.name;
			return {
				name,
				label: __(item.label || fallback.label || name),
				url: item.url || fallback.url,
				icon: item.icon || `/assets/hrms/images/integrations/${name}.svg`,
			};
		});
}

function staff_pro_dock_class() {
	return frappe.ui?.Dock || frappe.ui?.WorkspaceDock;
}

function staff_pro_dock_instance() {
	return frappe.app?.sidebar?.dock || frappe.app?.sidebar?.workspace_dock;
}

function staff_pro_dock_root() {
	return $(".dock, .workspace-dock");
}

function render_staff_pro_dock_integrations() {
	if (!should_use_staff_pro_desk_home()) return;

	const $dock = staff_pro_dock_root();
	if (!$dock.length) return;
	$dock.addClass("staff-pro-dock");

	let $wrap = $dock.children(".staff-pro-dock-integrations");
	if (!$wrap.length) {
		const $divider = $(
			'<div class="workspace-dock-divider dock-divider staff-pro-integrations-divider" role="separator"></div>'
		);
		$wrap = $('<div class="staff-pro-dock-integrations"></div>');
		const $user = $dock.children(".workspace-dock-user, .dock-user");
		if ($user.length) {
			$user.before($divider, $wrap);
		} else {
			$dock.append($divider, $wrap);
		}
	}

	const items = staff_pro_integrations().filter((item) => item.url);
	const signature = items.map((item) => `${item.name}:${item.url}`).join("|");
	if ($wrap.attr("data-sp-integrations") === signature && $wrap.children().length === items.length) {
		return;
	}

	$wrap.empty();
	items.forEach((item) => {
		const label = frappe.utils.escape_html(item.label);
		const icon = frappe.utils.escape_html(item.icon);
		const $item = $(`
			<button type="button" class="workspace-dock-item dock-item staff-pro-dock-integration staff-pro-dock-brand-icon"
				data-sp-integration="${frappe.utils.escape_html(item.name)}"
				aria-label="${label}"
				title="${label}">
				<span class="workspace-dock-icon dock-icon" aria-hidden="true">
					<img src="${icon}" alt="" />
				</span>
				<span class="workspace-dock-label dock-label">${label}</span>
			</button>
		`);
		$item.on("click", () => {
			window.open(item.url, "_blank", "noopener,noreferrer");
		});
		$wrap.append($item);
	});
	$wrap.attr("data-sp-integrations", signature);
}

function patch_workspace_dock_shortcuts() {
	const Dock = staff_pro_dock_class();
	if (!Dock || Dock.prototype._staff_pro_shortcuts) return;
	Dock.prototype._staff_pro_shortcuts = true;

	Dock.prototype.get_shortcuts = function () {
		if (!should_use_staff_pro_desk_home()) {
			return [
				{
					name: "search",
					icon: "search",
					label: __("Search"),
					css_class: "navbar-modal-search-mobile",
					condition: () => frappe.boot.desk_settings.search_bar,
				},
				{
					name: "notifications",
					icon: "bell",
					label: __("Notifications"),
					css_class: "sidebar-notification",
					condition: () => frappe.boot.desk_settings.notifications,
					badge: `<span class="notification-count hidden" aria-live="polite"></span>`,
					on_click: () => this.toggle_notifications(),
					setup: ($item) => {
						this.sync_notification_count(
							$item,
							frappe.boot.notification_unread_count || 0
						);
					},
				},
			];
		}
		return staff_pro_dock_shortcuts();
	};
}

function patch_workspace_dock_logo() {
	const Dock = staff_pro_dock_class();
	if (!Dock || Dock.prototype._staff_pro_logo) return;
	Dock.prototype._staff_pro_logo = true;

	const original = Dock.prototype.render_logo;
	Dock.prototype.render_logo = function () {
		if (!should_use_staff_pro_desk_home()) {
			return original.call(this);
		}

		const brand = staff_pro_brand();
		const homePath = staff_pro_desk_home_path();

		this.$logo.empty();
		const $link = $(
			`<a href="${homePath}" title="${frappe.utils.escape_html(brand.title)}" aria-label="${frappe.utils.escape_html(brand.title)}">
				<img src="${frappe.utils.escape_html(brand.logo_url)}" alt="${frappe.utils.escape_html(brand.title)}" />
			</a>`
		);
		$link.on("click", (e) => {
			e.preventDefault();
			staff_pro_open_portal("hr");
		});
		this.$logo.append($link);
	};
}

function staff_pro_sidebar_workspace_title(sidebar) {
	const name = sidebar?.current_module || sidebar?.sidebar_title;
	if (!name) return staff_pro_brand().title;

	const workspace = frappe.workspaces?.[frappe.router.slug(name)];
	return workspace?.title || workspace?.label || name;
}

function patch_sidebar_header_branding() {
	const Header = frappe.ui && frappe.ui.SidebarHeader;
	if (!Header || Header.prototype._staff_pro_brand) return;
	Header.prototype._staff_pro_brand = true;

	const originalTitle = Header.prototype.get_display_title;
	Header.prototype.get_display_title = function () {
		if (should_use_staff_pro_desk_home()) {
			return staff_pro_sidebar_workspace_title(this.sidebar);
		}
		return originalTitle.call(this);
	};

	const originalIcon = Header.prototype.get_default_icon;
	Header.prototype.get_default_icon = function () {
		if (should_use_staff_pro_desk_home()) {
			return staff_pro_brand().logo_url;
		}
		return originalIcon.call(this);
	};
}

function staff_pro_sidebar_payload(name) {
	if (!name) return null;
	const lower = String(name).toLowerCase();
	const spaced = lower.replace(/[-_]/g, " ");
	const dashed = lower.replace(/\s+/g, "-");

	const items = frappe.boot?.workspace_sidebar_item;
	if (items) {
		const found = items[name] || items[lower] || items[spaced] || items[dashed];
		if (found) return found;
	}

	const modules = frappe.boot?.module_sidebars;
	if (!modules) return null;
	if (modules[name]) return modules[name];
	for (const [key, value] of Object.entries(modules)) {
		const keyLower = String(key).toLowerCase();
		if (keyLower === lower || keyLower === spaced || keyLower === dashed) {
			return value;
		}
		const title = String(value?.title || "").toLowerCase();
		if (title && (title === lower || title === spaced)) {
			return value;
		}
	}
	return null;
}

function patch_sidebar_workspace_switch() {
	const Sidebar = frappe.ui && frappe.ui.Sidebar;
	if (!Sidebar || Sidebar.prototype._staff_pro_workspace_switch) return;
	Sidebar.prototype._staff_pro_workspace_switch = true;

	const originalOpenWorkspace = Sidebar.prototype.open_workspace;
	Sidebar.prototype.open_workspace = function (name) {
		if (!should_use_staff_pro_desk_home()) {
			return originalOpenWorkspace.call(this, name);
		}

		this._staff_pro_pinned_sidebar = name;
		this.open?.();
		if (typeof this.select_module === "function" && staff_pro_sidebar_payload(name)) {
			this.select_module(name);
		} else if (staff_pro_sidebar_payload(name) && typeof this.select_sidebar === "function") {
			this.select_sidebar(name);
		}

		if (typeof this.open_module === "function" && staff_pro_sidebar_payload(name)) {
			this.open_module(name);
			return;
		}

		const route = this.get_first_sidebar_route?.(name);
		if (route) {
			frappe.set_route(route);
			return;
		}

		return originalOpenWorkspace.call(this, name);
	};

	const originalSetWorkspaceSidebar = Sidebar.prototype.set_workspace_sidebar;
	Sidebar.prototype.set_workspace_sidebar = function () {
		if (should_use_staff_pro_desk_home()) {
			const portal = staff_pro_current_portal();
			let pinned = this._staff_pro_pinned_sidebar;
			const current = this.current_module || this.sidebar_title;

			if (portal === "hr" && pinned && !staff_pro_is_hr_sidebar(pinned)) {
				this._staff_pro_pinned_sidebar = null;
				pinned = null;
			}

			if (
				pinned &&
				staff_pro_sidebar_payload(pinned) &&
				(portal !== "hr" || staff_pro_is_hr_sidebar(pinned))
			) {
				if (typeof this.select_module === "function") {
					this.select_module(pinned);
				} else {
					this.select_sidebar?.(pinned);
				}
				this.set_active_workspace_item?.();
				this.refresh_dock?.();
				return;
			}

			if (portal === "hr" && !staff_pro_is_hr_sidebar(current)) {
				const home = staff_pro_hr_home_sidebar();
				staff_pro_remember_sidebar(home);
				if (typeof this.select_module === "function") {
					this.select_module(home);
				} else {
					this.select_sidebar?.(home);
				}
				this.set_active_workspace_item?.();
				this.refresh_header?.();
				this.refresh_dock?.();
				return;
			}
		}
		return originalSetWorkspaceSidebar.call(this);
	};
}

function refresh_staff_pro_dock_shortcuts() {
	if (!should_use_staff_pro_desk_home()) return;

	patch_workspace_dock_shortcuts();
	patch_workspace_dock_logo();

	const dock = staff_pro_dock_instance();
	if (!dock?.$shortcuts) return;

	const portal = staff_pro_current_portal();
	const expectedShortcuts = staff_pro_dock_shortcuts();
	const hasExpectedShortcuts = expectedShortcuts.length
		? Boolean(
				dock.$shortcuts.children(
					".staff-pro-dock-hr, .staff-pro-dock-accounting, .staff-pro-dock-admin"
				).length
			)
		: true;
	if (
		dock._staff_pro_portal === portal &&
		hasExpectedShortcuts &&
		dock.$dock?.children(".staff-pro-dock-integrations").length
	) {
		label_workspace_dock();
		render_staff_pro_dock_integrations();
		return;
	}

	dock._staff_pro_portal = portal;
	dock.rendered = null;
	dock.$shortcuts.find('[data-toggle="tooltip"]').tooltip("dispose");
	dock.$shortcuts.empty();
	dock.render_shortcuts();
	label_workspace_dock();
	render_staff_pro_dock_integrations();
	dock.render_logo();
	frappe.app?.sidebar?.refresh_dock?.();
}

const DOCK_LABELS = {
	pay: "Payroll",
};

const DOCK_ICONS = {
	people: "/assets/hrms/images/integrations/teams.svg",
	pay: "coins",
	payroll: "coins",
	"ss and taxes": "/assets/hrms/images/belize-ssb-logo.png",
	time: "clock",
	talent: "user-plus",
	finance: "/assets/hrms/images/integrations/quickbooks.svg",
	"finance & admin": "/assets/hrms/images/integrations/quickbooks.svg",
	"finance and admin": "/assets/hrms/images/integrations/quickbooks.svg",
	hr: "briefcase",
	accounting: "file-text",
	admin: "settings",
	"hr admin": "users",
	invoicing: "file-text",
	payments: "credit-card",
	"financial reports": "bar-chart-2",
	projects: "folder-kanban",
	"erpnext settings": "settings",
};

function display_dock_label(label) {
	if (!label) return label;
	return DOCK_LABELS[String(label).toLowerCase()] || label;
}

function is_dock_image_icon(icon) {
	return typeof icon === "string" && (icon.startsWith("/") || /\.(svg|png|jpe?g|webp)(\?|$)/i.test(icon));
}

function dock_icon_html(name) {
	try {
		const html = frappe.utils.icon(name, "sm");
		if (html && String(html).includes("svg")) return html;
	} catch (e) {
		/* use fallback */
	}
	return lucide_icon_html(name);
}

function apply_dock_icon($item, label) {
	if ($item.hasClass("staff-pro-dock-integration") || $item.closest(".staff-pro-dock-integrations").length) {
		return;
	}
	const iconName = DOCK_ICONS[(label || "").toLowerCase()];
	if (!iconName) return;
	if ($item.attr("data-sp-dock-icon") === iconName) return;

	const isImage = is_dock_image_icon(iconName);
	let html = "";
	if (isImage) {
		html = `<img src="${frappe.utils.escape_html(iconName)}" alt="" />`;
	} else {
		html = dock_icon_html(iconName);
		if (!html || !String(html).includes("svg")) return;
	}

	let $wrap = $item.children(".workspace-dock-icon, .dock-icon, .sidebar-item-icon").first();
	if (!$wrap.length) {
		$wrap = $('<span class="workspace-dock-icon dock-icon" aria-hidden="true"></span>');
		$item.prepend($wrap);
	}
	$wrap.html(html);
	$item.toggleClass("staff-pro-dock-brand-icon", isImage);
	$item.children("svg, .icon, img").not($wrap.find("svg, .icon, img")).remove();
	$item.attr("data-sp-dock-icon", iconName);
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
	$(".workspace-dock button.workspace-dock-item, .dock button.dock-item").each(function () {
		const $item = $(this);
		const rawLabel = dock_item_label($item);
		if (!rawLabel) return;
		const label = display_dock_label(rawLabel);
		if (label !== rawLabel) {
			$item.attr("aria-label", label);
		}

		apply_dock_icon($item, label);

		let $label = $item.children(".workspace-dock-label, .dock-label");
		if ($label.length) {
			if ($label.text() !== label) $label.text(label);
			return;
		}
		$item.append(
			`<span class="workspace-dock-label dock-label">${frappe.utils.escape_html(String(label))}</span>`
		);
	});
}

function remove_sidebar_search() {
	$(".body-sidebar .staff-pro-sidebar-search").remove();
}

function patch_workspace_dock() {
	patch_workspace_dock_shortcuts();
	patch_workspace_dock_logo();
	patch_sidebar_header_branding();
	patch_sidebar_workspace_switch();

	const Dock = staff_pro_dock_class();
	if (!Dock || Dock.prototype._staff_pro_labeled) return;
	Dock.prototype._staff_pro_labeled = true;

	const origItem = Dock.prototype.make_dock_item || Dock.prototype.make_workspace_item;
	if (!origItem) return;

	const patched = function (entry) {
		const rawLabel = entry.label || entry.title || entry.name || "";
		const label = display_dock_label(rawLabel);
		const mappedIcon =
			DOCK_ICONS[String(label).toLowerCase()] || DOCK_ICONS[String(rawLabel).toLowerCase()];
		if (mappedIcon && !is_dock_image_icon(mappedIcon)) {
			entry = Object.assign({}, entry, { icon: mappedIcon, label });
		} else if (label !== rawLabel) {
			entry = Object.assign({}, entry, { label });
		}
		const $item = origItem.call(this, entry);
		if ($item && $item.length) {
			if (label && !$item.children(".workspace-dock-label, .dock-label").length) {
				$item.append(
					`<span class="workspace-dock-label dock-label">${frappe.utils.escape_html(String(label))}</span>`
				);
			}
			apply_dock_icon($item, label);
		}
		return $item;
	};

	if (Dock.prototype.make_dock_item) {
		Dock.prototype.make_dock_item = patched;
	}
	if (Dock.prototype.make_workspace_item) {
		Dock.prototype.make_workspace_item = patched;
	}
}

function disable_app_onboarding() {
	if (frappe.boot) {
		frappe.boot.sysdefaults = frappe.boot.sysdefaults || {};
		frappe.boot.sysdefaults.enable_onboarding = 0;
	}

	const Sidebar = frappe.ui && frappe.ui.Sidebar;
	if (Sidebar && !Sidebar.prototype._staff_pro_onboarding_disabled) {
		Sidebar.prototype._staff_pro_onboarding_disabled = true;
		Sidebar.prototype.setup_onboarding = function () {
			this.remove_onboarding_wrapper?.();
			this.wrapper?.find(".onboarding-sidebar").addClass("hidden");
		};
		Sidebar.prototype.remove_onboarding_wrapper = function () {
			this.$onboarding?.empty();
			this.wrapper?.find(".onboarding-sidebar").addClass("hidden");
		};
	}

	document.querySelectorAll(".user-onboarding, .onb-panel").forEach((el) => el.remove());
	document.querySelectorAll(".onboarding-sidebar").forEach((el) => el.classList.add("hidden"));

	const onboardingStyles = document.getElementById("user-onboarding-styles");
	if (onboardingStyles) onboardingStyles.remove();
	document.querySelectorAll(".main-section").forEach((el) => {
		if (el.style.paddingBottom === "90px") el.style.paddingBottom = "";
	});
}

function is_help_menu_label(label) {
	const text = String(label || "").trim();
	if (!text) return false;
	if (/^help$/i.test(text)) return true;
	try {
		return text === __("Help");
	} catch (e) {
		return false;
	}
}

function is_help_menu_item(item) {
	if (!item || item.is_divider) return false;
	if (item.name === "help") return true;
	return is_help_menu_label(item.label);
}

function hide_help_context_menu_items() {
	document.querySelectorAll(".frappe-menu.context-menu .dropdown-menu-item").forEach((item) => {
		const title = item.querySelector(".menu-item-title");
		const text = (title?.textContent || item.querySelector("a")?.textContent || "").trim();
		if (!is_help_menu_label(text)) return;
		item.classList.add("staff-pro-hide-help");
		item.remove();
	});
}

function disable_sidebar_help() {
	if (frappe.boot?.navbar_settings) {
		frappe.boot.navbar_settings.help_dropdown = [];
	}
	if (frappe.help) {
		frappe.help.help_links = {};
	}

	const Header = frappe.ui && frappe.ui.SidebarHeader;
	if (Header && !Header.prototype._staff_pro_help_disabled) {
		Header.prototype._staff_pro_help_disabled = true;
		Header.prototype.get_help_siblings = function () {
			return [];
		};
		const original_system_items = Header.prototype.system_items;
		if (original_system_items) {
			Header.prototype.system_items = function () {
				return (original_system_items.call(this) || []).filter((item) => !is_help_menu_item(item));
			};
		}
	}

	const Menu = frappe.ui && frappe.ui.menu;
	if (Menu && !Menu.prototype._staff_pro_help_disabled) {
		Menu.prototype._staff_pro_help_disabled = true;
		const original_add = Menu.prototype.add_menu_item;
		Menu.prototype.add_menu_item = function (item) {
			if (is_help_menu_item(item)) return;
			return original_add.call(this, item);
		};
	}

	if (frappe.ui?.create_menu && !frappe.ui.create_menu._staff_pro_help_disabled) {
		const original_create = frappe.ui.create_menu;
		frappe.ui.create_menu = function (opts) {
			if (opts?.menu_items) {
				opts = Object.assign({}, opts, {
					menu_items: opts.menu_items.filter((item) => !is_help_menu_item(item)),
				});
			}
			return original_create(opts);
		};
		frappe.ui.create_menu._staff_pro_help_disabled = true;
	}

	const header = frappe.app?.sidebar?.header;
	if (header?.refresh_menu) header.refresh_menu();
	if (header?.menu?.menu_items) {
		header.menu.menu_items = (header.menu.menu_items || []).filter((item) => !is_help_menu_item(item));
	}

	hide_help_context_menu_items();
}

function watch_workspace_dock() {
	inject_sidebar_css();
	disable_app_onboarding();
	disable_sidebar_help();
	patch_workspace_dock();
	patch_form_sidebar_policy();
	apply_form_sidebar_policy();
	refresh_staff_pro_dock_shortcuts();
	label_workspace_dock();
	render_staff_pro_dock_integrations();
	remove_sidebar_search();
	enhance_sidebar_menus();
	style_sidebar_collapse_toggle();

	const dock = document.querySelector(".dock, .workspace-dock");
	const sidebar = document.querySelector(".body-sidebar");
	const container = document.querySelector(".body-sidebar-container");
	if (!dock && !sidebar && !container) {
		setTimeout(watch_workspace_dock, 200);
		return;
	}

	const observer = new MutationObserver(() => {
		patch_workspace_dock();
		refresh_staff_pro_dock_shortcuts();
		label_workspace_dock();
		render_staff_pro_dock_integrations();
		remove_sidebar_search();
		enhance_sidebar_menus();
		style_sidebar_collapse_toggle();
		disable_app_onboarding();
		disable_sidebar_help();
	});
	if (dock) observer.observe(dock, { childList: true, subtree: true });
	if (container) observer.observe(container, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
	else if (sidebar) observer.observe(sidebar, { childList: true, subtree: true });
}

$(document).on("app_ready", watch_workspace_dock);
$(document).on("app_ready", disable_app_onboarding);
$(document).on("app_ready", disable_sidebar_help);
$(document).on("page-change", disable_app_onboarding);
$(document).on("page-change", disable_sidebar_help);

if (typeof frappe !== "undefined") {
	disable_app_onboarding();
	disable_sidebar_help();
	if ($(".dock, .workspace-dock, .body-sidebar").length) {
		watch_workspace_dock();
	}
}

function should_use_staff_pro_desk_home() {
	return Boolean(frappe.boot?.staff_pro_skip_desktop);
}

const STAFF_PRO_DESK_HOME_FALLBACK = ["dashboard-view", "Human Resource"];

function staff_pro_desk_home_route() {
	const home = frappe.boot?.staff_pro_desk_home;
	if (Array.isArray(home) && home.length) return home;
	if (typeof home === "string" && home.includes("/")) return home.split("/");
	if (typeof home === "string" && home) return [home];
	return STAFF_PRO_DESK_HOME_FALLBACK;
}

function staff_pro_desk_home_path() {
	const route = staff_pro_desk_home_route();
	return `/desk/${route.map((part) => encodeURIComponent(part)).join("/")}`;
}

function is_already_on_staff_pro_desk_home(route = frappe.get_route?.() || []) {
	const homeRoute = staff_pro_desk_home_route();
	const path = (window.location.pathname || "").replace(/\/$/, "") || "/";

	if (route[0] === homeRoute[0] && (route[1] || "") === (homeRoute[1] || "")) {
		return true;
	}

	if (path === staff_pro_desk_home_path()) {
		return true;
	}

	return false;
}

const STAFF_PRO_WORKSPACE_DASHBOARDS = {
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
	"ss and taxes": ["dashboard-view", "SS and Taxes"],
};

function staff_pro_workspace_dashboard_route(route = []) {
	const raw = route[0] === "Workspaces" ? route[1] : route[0];
	const key = String(raw || "")
		.toLowerCase()
		.replace(/-/g, " ")
		.trim();
	return STAFF_PRO_WORKSPACE_DASHBOARDS[key] || null;
}

function is_staff_pro_desktop_route(route = frappe.get_route?.() || [], options = {}) {
	if (is_already_on_staff_pro_desk_home(route)) return false;

	const path = (window.location.pathname || "").replace(/\/$/, "") || "/";
	const on_apps = route[0] === "apps" || path === "/apps" || path.endsWith("/apps") || path === "/app/apps";
	const on_desktop_page = route[0] === "desktop" || path.endsWith("/desktop");
	const on_empty_desk_route = !route[0] && (path === "/desk" || path === "/app" || path === "/");
	const on_bare_dashboard = (route[0] === "dashboard-view" || route[0] === "dashboard") && !route[1];
	const on_workspace_home = Boolean(staff_pro_workspace_dashboard_route(route));
	const on_workforce_bootstrap =
		options.includeWorkforceBootstrap &&
		(route[0]?.toLowerCase() === "workforce" || /\/desk\/workforce\/?$/.test(path));
	return on_apps || on_desktop_page || on_empty_desk_route || on_bare_dashboard || on_workspace_home || on_workforce_bootstrap;
}

function redirect_staff_pro_desk_home(options = {}) {
	if (!should_use_staff_pro_desk_home() || window._staff_pro_desk_redirecting) return;

	const route = frappe.get_route?.() || [];
	if (!is_staff_pro_desktop_route(route, options)) return;

	const target = staff_pro_workspace_dashboard_route(route) || staff_pro_desk_home_route();
	window._staff_pro_desk_redirecting = true;
	Promise.resolve(frappe.set_route(...target)).finally(() => {
		window._staff_pro_desk_redirecting = false;
	});
}

function patch_staff_pro_desktop_redirect() {
	const pageview = frappe.views?.pageview;
	if (!pageview || pageview._staff_pro_desktop_redirect) return;
	pageview._staff_pro_desktop_redirect = true;

	const original_show = pageview.show.bind(pageview);
	pageview.show = function (name) {
		if (should_use_staff_pro_desk_home() && (!name || name === "desktop" || name === "apps")) {
			redirect_staff_pro_desk_home();
			return;
		}
		const workspace_home = staff_pro_workspace_dashboard_route([name]);
		if (should_use_staff_pro_desk_home() && workspace_home) {
			window._staff_pro_desk_redirecting = true;
			Promise.resolve(frappe.set_route(...workspace_home)).finally(() => {
				window._staff_pro_desk_redirecting = false;
			});
			return;
		}
		return original_show(name);
	};
}

function employee_list_view_from_route(route = frappe.get_route?.() || []) {
	const path = (window.location.pathname || "").replace(/\/$/, "").toLowerCase();
	if (/\/employee\/view\/image$/i.test(path)) return "Image";
	if (route[0] === "List" && route[1] === "Employee") return route[2] || "List";
	if (path === "/desk/employee" || path === "/app/employee") return "List";
	if (/\/employee\/view\/list$/i.test(path)) return "List";
	return null;
}

function prefer_employee_image_view() {
	try {
		const meta = frappe.get_meta?.("Employee");
		if (meta) meta.default_view = "Image";
	} catch (e) {
		// Meta may not be loaded yet.
	}

	const settings = frappe.model?.user_settings;
	if (settings) {
		settings.Employee = settings.Employee || {};
		if (settings.Employee.last_view !== "Image") {
			settings.Employee.last_view = "Image";
			settings.save?.("Employee", "last_view", "Image");
		}
	}

	const view = employee_list_view_from_route();
	if (view !== "List") return;
	if (window._staff_pro_employee_image_redirecting) return;

	window._staff_pro_employee_image_redirecting = true;
	Promise.resolve(frappe.set_route("List", "Employee", "Image")).finally(() => {
		window._staff_pro_employee_image_redirecting = false;
	});
}

function staff_pro_page_hide_menu(page) {
	if (typeof page?.hide_menu === "function") {
		page.hide_menu();
	}
}

function hide_page_menu() {
	document.querySelectorAll(".page-head .menu-btn-group, .page-head .menu-more-button").forEach((el) => {
		el.classList.add("hidden", "hide");
		el.style.display = "none";
	});

	staff_pro_page_hide_menu(window.cur_frm?.page);
	staff_pro_page_hide_menu(window.cur_list?.page);

	const current = frappe.container?.page;
	if (current) {
		staff_pro_page_hide_menu(current);
	}

	const pages = frappe.ui?.pages;
	if (pages && typeof pages === "object") {
		Object.values(pages).forEach((page) => staff_pro_page_hide_menu(page));
	}
}

function hide_list_page_chrome() {
	const route = frappe.get_route?.() || [];
	if (route[0] !== "List") return;

	document
		.querySelectorAll(
			'[id^="page-List/"] .view-switcher, [id^="page-List/"] .views-switcher, [id^="page-List/"] .match-type-dropdown-btn',
		)
		.forEach((el) => {
			el.classList.add("hidden", "hide");
			el.style.display = "none";
		});

	hide_page_menu();
}

const PROFILE_FORM_DOCTYPES = new Set(["Employee", "User"]);

function staff_pro_current_form_doctype() {
	const route = frappe.get_route?.() || [];
	if (route[0] === "Form" && route[1]) {
		return route[1];
	}
	if (typeof cur_frm !== "undefined" && cur_frm?.doctype && cur_frm.page?.wrapper?.is(":visible")) {
		return cur_frm.doctype;
	}
	return null;
}

function hide_form_sidebar_attachments_tags_share() {
	document
		.querySelectorAll(
			".form-sidebar .form-attachments, .form-sidebar .form-tags, .form-sidebar .form-shared",
		)
		.forEach((el) => {
			el.classList.add("hidden", "hide");
			el.style.display = "none";
		});
}

function apply_form_sidebar_policy() {
	const doctype = staff_pro_current_form_doctype();
	const hide = Boolean(doctype) && !PROFILE_FORM_DOCTYPES.has(doctype);
	document.body.classList.toggle("staff-pro-hide-form-sidebar", hide);
	hide_form_sidebar_attachments_tags_share();
}

function patch_form_sidebar_policy() {
	const Form = frappe.ui?.form?.Form;
	if (!Form || Form.prototype._staff_pro_sidebar_policy) return;
	Form.prototype._staff_pro_sidebar_policy = true;

	const original = Form.prototype.refresh;
	Form.prototype.refresh = function (...args) {
		const result = original.apply(this, args);
		apply_form_sidebar_policy();
		hide_page_menu();
		return result;
	};
}

function patch_list_page_chrome() {
	const ListView = frappe.views?.ListView;
	if (!ListView || ListView.prototype._staff_pro_list_chrome) return;
	ListView.prototype._staff_pro_list_chrome = true;

	const original = ListView.prototype.refresh;
	ListView.prototype.refresh = function (...args) {
		const result = original.apply(this, args);
		hide_list_page_chrome();
		return result;
	};
}

$(document).on("app_ready", patch_staff_pro_desktop_redirect);
$(document).on("app_ready", () => redirect_staff_pro_desk_home({ includeWorkforceBootstrap: true }));
$(document).on("app_ready", prefer_employee_image_view);
$(document).on("app_ready", patch_form_sidebar_policy);
$(document).on("app_ready", patch_list_page_chrome);
$(document).on("app_ready", apply_form_sidebar_policy);
$(document).on("app_ready", hide_page_menu);
$(document).on("app_ready", hide_list_page_chrome);
$(document).on("page-change", () => redirect_staff_pro_desk_home());
$(document).on("page-change", refresh_staff_pro_dock_shortcuts);
$(document).on("page-change", enhance_sidebar_menus);
$(document).on("page-change", prefer_employee_image_view);
$(document).on("page-change", hide_page_menu);
$(document).on("page-change", hide_list_page_chrome);
$(document).on("page-change", apply_form_sidebar_policy);
