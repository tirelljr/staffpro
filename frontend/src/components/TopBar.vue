<template>
	<header class="app-topbar">
		<div class="app-topbar__inner">
			<div class="app-topbar__left">
				<div class="app-topbar__id">{{ contextId }}</div>
				<div class="app-topbar__status">
					<span class="app-topbar__status-dot" />
					<span>{{ contextStatus }}</span>
				</div>
			</div>

			<div class="app-topbar__center">
				<button
					type="button"
					class="app-topbar__search"
					@click="openSearch"
				>
					<FeatherIcon name="search" class="h-4 w-4 shrink-0 text-gray-400" />
					<span class="app-topbar__search-placeholder">
						{{ __("Search attendance, leaves, expenses, help") }}
					</span>
					<kbd class="app-topbar__shortcut">{{ searchShortcut }}</kbd>
				</button>
			</div>

			<div class="app-topbar__right">
				<button
					type="button"
					class="app-topbar__icon-btn app-topbar__search-toggle"
					:title="__('Search')"
					@click="openSearch"
				>
					<FeatherIcon name="search" class="h-5 w-5 text-gray-800" />
				</button>

				<router-link
					:to="{ name: 'Notifications' }"
					class="app-topbar__icon-btn"
					:title="__('Notifications')"
				>
					<FeatherIcon name="bell" class="h-5 w-5 text-gray-800" />
					<span
						v-if="unreadCount"
						class="app-topbar__badge"
					>
						{{ unreadCount > 99 ? "99+" : unreadCount }}
					</span>
				</router-link>

				<router-link
					:to="{ name: 'Settings' }"
					class="app-topbar__icon-btn"
					:title="__('Settings')"
				>
					<FeatherIcon name="settings" class="h-5 w-5 text-gray-800" />
				</router-link>

				<div class="relative" ref="languageMenu">
					<button
						type="button"
						class="app-topbar__icon-btn app-topbar__lang"
						:title="__('Language')"
						@click="languageOpen = !languageOpen"
					>
						{{ languageLabel }}
					</button>
					<div v-if="languageOpen" class="app-topbar__menu">
						<button
							v-for="lang in languages"
							:key="lang.code"
							type="button"
							class="app-topbar__menu-item"
							:class="{ 'is-active': lang.code === currentLanguage }"
							@click="setLanguage(lang.code)"
						>
							{{ lang.label }}
						</button>
					</div>
				</div>

				<router-link
					:to="{ name: 'Profile' }"
					class="app-topbar__avatar"
					:title="__('Profile')"
				>
					<Avatar
						:image="user.data?.user_image"
						:label="user.data?.first_name || user.data?.full_name"
						size="xl"
					/>
				</router-link>
			</div>
		</div>
	</header>

	<Teleport to="body">
		<div
			v-if="searchOpen"
			class="app-topbar__overlay"
			@click.self="closeSearch"
		>
			<div class="app-topbar__palette" role="dialog" aria-modal="true">
				<div class="app-topbar__palette-input">
					<FeatherIcon name="search" class="h-5 w-5 shrink-0 text-gray-400" />
					<input
						ref="searchInput"
						v-model="query"
						type="search"
						:placeholder="__('Search attendance, leaves, expenses, help')"
						@keydown="onSearchKeydown"
					/>
					<kbd class="app-topbar__shortcut">ESC</kbd>
				</div>
				<ul v-if="filteredItems.length" class="app-topbar__results">
					<li
						v-for="(item, index) in filteredItems"
						:key="item.href || item.route"
					>
						<button
							type="button"
							class="app-topbar__result"
							:class="{ 'is-active': index === activeIndex }"
							@mouseenter="activeIndex = index"
							@click="goTo(item)"
						>
							<FeatherIcon :name="item.icon" class="h-4 w-4 text-gray-500" />
							<div class="min-w-0 text-left">
								<div class="truncate font-medium text-gray-900">{{ item.title }}</div>
								<div class="truncate text-xs text-gray-500">{{ item.group }}</div>
							</div>
						</button>
					</li>
				</ul>
				<div v-else class="app-topbar__empty">
					{{ __("No matching pages") }}
				</div>
			</div>
		</div>
	</Teleport>
</template>

<script setup>
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { Avatar, FeatherIcon, call } from "frappe-ui"

import { unreadNotificationsCount } from "@/data/notifications"
import { canOpenDesk, DESK_SHORTCUTS } from "@/utils/deskAccess"

const user = inject("$user")
const employee = inject("$employee")
const __ = inject("$translate")
const router = useRouter()

const showDeskShortcuts = computed(() => canOpenDesk(user.data))

const searchItems = computed(() => {
	const items = [
		{ title: __("Attendance"), group: __("Dashboards"), icon: "clock", route: "AttendanceDashboard" },
		{ title: __("Leaves"), group: __("Dashboards"), icon: "calendar", route: "LeavesDashboard" },
		{ title: __("Expense Claims"), group: __("Dashboards"), icon: "credit-card", route: "ExpenseClaimsDashboard" },
		{ title: __("Salary Slips"), group: __("Dashboards"), icon: "file-text", route: "SalarySlipsDashboard" },
		{ title: __("Attendance Requests"), group: __("Attendance"), icon: "check-square", route: "AttendanceRequestListView" },
		{ title: __("Employee Checkins"), group: __("Attendance"), icon: "log-in", route: "EmployeeCheckinListView" },
		{ title: __("Shift Requests"), group: __("Attendance"), icon: "repeat", route: "ShiftRequestListView" },
		{ title: __("Shift Assignments"), group: __("Attendance"), icon: "briefcase", route: "ShiftAssignmentListView" },
		{ title: __("Leave Applications"), group: __("Leaves"), icon: "sun", route: "LeaveApplicationListView" },
		{ title: __("Expense Claims"), group: __("Expenses"), icon: "pocket", route: "ExpenseClaimListView" },
		{ title: __("Employee Advances"), group: __("Expenses"), icon: "dollar-sign", route: "EmployeeAdvanceListView" },
		{ title: __("Notifications"), group: __("Account"), icon: "bell", route: "Notifications" },
		{ title: __("Settings"), group: __("Account"), icon: "settings", route: "Settings" },
		{ title: __("Profile"), group: __("Account"), icon: "user", route: "Profile" },
	]
	if (showDeskShortcuts.value) {
		for (const shortcut of DESK_SHORTCUTS) {
			items.push({
				title: __(shortcut.title),
				group: __("Desk"),
				icon: shortcut.icon,
				href: shortcut.path,
			})
		}
	}
	return items
})

const searchOpen = ref(false)
const query = ref("")
const activeIndex = ref(0)
const searchInput = ref(null)
const languageOpen = ref(false)
const languageMenu = ref(null)

const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)
const searchShortcut = isMac ? "⌘K" : "Ctrl K"

const languages = [
	{ code: "en", label: "English" },
	{ code: "es", label: "Español" },
	{ code: "fr", label: "Français" },
	{ code: "ar", label: "العربية" },
	{ code: "hi", label: "हिन्दी" },
]

const currentLanguage = computed(() => {
	const lang = window.frappe?.boot?.lang || "en"
	return lang.split("-")[0].toLowerCase()
})

const languageLabel = computed(() => currentLanguage.value.slice(0, 2).toUpperCase())

const contextId = computed(() => {
	return (employee.data?.name || user.data?.name || "").toUpperCase()
})

const contextStatus = computed(() => {
	return employee.data?.designation || __("Active")
})

const unreadCount = computed(() => unreadNotificationsCount.data || 0)

const filteredItems = computed(() => {
	const q = query.value.trim().toLowerCase()
	if (!q) return searchItems.value
	return searchItems.value.filter((item) => {
		return (
			item.title.toLowerCase().includes(q) ||
			item.group.toLowerCase().includes(q)
		)
	})
})

watch(query, () => {
	activeIndex.value = 0
})

async function openSearch() {
	searchOpen.value = true
	query.value = ""
	activeIndex.value = 0
	await nextTick()
	searchInput.value?.focus()
}

function closeSearch() {
	searchOpen.value = false
	query.value = ""
	activeIndex.value = 0
}

function goTo(item) {
	closeSearch()
	if (item.href) {
		window.location.href = item.href
		return
	}
	router.push({ name: item.route })
}

function onSearchKeydown(event) {
	if (event.key === "Escape") {
		event.preventDefault()
		closeSearch()
		return
	}
	if (event.key === "ArrowDown") {
		event.preventDefault()
		activeIndex.value = Math.min(activeIndex.value + 1, filteredItems.value.length - 1)
		return
	}
	if (event.key === "ArrowUp") {
		event.preventDefault()
		activeIndex.value = Math.max(activeIndex.value - 1, 0)
		return
	}
	if (event.key === "Enter") {
		event.preventDefault()
		const item = filteredItems.value[activeIndex.value]
		if (item) goTo(item)
	}
}

function onGlobalKeydown(event) {
	const key = event.key?.toLowerCase()
	if ((event.metaKey || event.ctrlKey) && key === "k") {
		event.preventDefault()
		if (searchOpen.value) closeSearch()
		else openSearch()
	}
}

function onDocumentClick(event) {
	if (languageOpen.value && languageMenu.value && !languageMenu.value.contains(event.target)) {
		languageOpen.value = false
	}
}

async function setLanguage(code) {
	languageOpen.value = false
	if (code === currentLanguage.value || !user.data?.name) return
	try {
		await call("frappe.client.set_value", {
			doctype: "User",
			name: user.data.name,
			fieldname: "language",
			value: code,
		})
		window.location.reload()
	} catch (error) {
		console.error("Failed to update language", error)
	}
}

onMounted(() => {
	window.addEventListener("keydown", onGlobalKeydown)
	document.addEventListener("click", onDocumentClick)
})

onBeforeUnmount(() => {
	window.removeEventListener("keydown", onGlobalKeydown)
	document.removeEventListener("click", onDocumentClick)
})
</script>

<style scoped>
.app-topbar {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	z-index: 1100;
	height: var(--app-topbar-height);
	padding-top: env(safe-area-inset-top);
	background: #ffffff;
	border-bottom: 1px solid #eef0f2;
}

.app-topbar__inner {
	display: grid;
	grid-template-columns: minmax(9rem, 1fr) minmax(0, 36rem) minmax(9rem, 1fr);
	align-items: center;
	gap: 1rem;
	height: 4rem;
	padding: 0 1.25rem;
}

.app-topbar__left {
	min-width: 0;
	display: flex;
	flex-direction: column;
	justify-content: center;
	gap: 0.125rem;
}

.app-topbar__id {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	font-size: 0.6875rem;
	font-weight: 500;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: #9ca3af;
}

.app-topbar__status {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	font-size: 0.9375rem;
	font-weight: 700;
	color: #111827;
	line-height: 1.2;
}

.app-topbar__status-dot {
	width: 0.5rem;
	height: 0.5rem;
	border-radius: 9999px;
	background: var(--sp-cyan, #00a6e8);
	flex-shrink: 0;
}

.app-topbar__center {
	display: flex;
	justify-content: center;
}

.app-topbar__search {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	width: 100%;
	max-width: 36rem;
	height: 2.5rem;
	padding: 0 0.75rem 0 1rem;
	border: none;
	border-radius: 9999px;
	background: #f3f4f6;
	text-align: left;
	cursor: pointer;
}

.app-topbar__search:hover,
.app-topbar__search:focus-visible {
	background: #eceef1;
	outline: none;
}

.app-topbar__search-placeholder {
	flex: 1;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	font-size: 0.875rem;
	color: #9ca3af;
}

.app-topbar__shortcut {
	display: none;
	align-items: center;
	justify-content: center;
	min-width: 1.75rem;
	height: 1.375rem;
	padding: 0 0.375rem;
	border-radius: 0.25rem;
	background: #ffffff;
	box-shadow: 0 0 0 1px #e5e7eb;
	font-family: inherit;
	font-size: 0.6875rem;
	font-weight: 600;
	color: #9ca3af;
}

.app-topbar__right {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 0.625rem;
}

.app-topbar__icon-btn {
	position: relative;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 2.5rem;
	height: 2.5rem;
	border: none;
	border-radius: 9999px;
	background: #f3f4f6;
	color: #111827;
	cursor: pointer;
	text-decoration: none;
}

.app-topbar__icon-btn:hover,
.app-topbar__avatar:hover {
	background: #eceef1;
}

.app-topbar__search-toggle {
	display: none;
}

.app-topbar__lang {
	font-size: 0.75rem;
	font-weight: 700;
	letter-spacing: 0.02em;
}

.app-topbar__badge {
	position: absolute;
	top: -0.2rem;
	right: -0.2rem;
	min-width: 1.15rem;
	height: 1.15rem;
	padding: 0 0.25rem;
	border-radius: 9999px;
	background: #111827;
	color: #ffffff;
	font-size: 0.625rem;
	font-weight: 700;
	line-height: 1.15rem;
	text-align: center;
}

.app-topbar__avatar {
	display: inline-flex;
	border-radius: 9999px;
	overflow: hidden;
}

.app-topbar__avatar :deep(.flex) {
	width: 2.5rem;
	height: 2.5rem;
}

.app-topbar__menu {
	position: absolute;
	top: calc(100% + 0.5rem);
	right: 0;
	z-index: 20;
	min-width: 9rem;
	padding: 0.25rem;
	border-radius: 0.75rem;
	background: #ffffff;
	box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
	border: 1px solid #eef0f2;
}

.app-topbar__menu-item {
	display: block;
	width: 100%;
	padding: 0.5rem 0.75rem;
	border: none;
	border-radius: 0.5rem;
	background: transparent;
	text-align: left;
	font-size: 0.8125rem;
	color: #111827;
}

.app-topbar__menu-item:hover,
.app-topbar__menu-item.is-active {
	background: #f3f4f6;
}

.app-topbar__overlay {
	position: fixed;
	inset: 0;
	z-index: 2000;
	display: flex;
	justify-content: center;
	padding: 12vh 1rem 1rem;
	background: rgba(17, 24, 39, 0.28);
}

.app-topbar__palette {
	width: min(36rem, 100%);
	max-height: min(28rem, 70vh);
	overflow: hidden;
	display: flex;
	flex-direction: column;
	border-radius: 1rem;
	background: #ffffff;
	box-shadow: 0 20px 50px rgba(15, 23, 42, 0.18);
}

.app-topbar__palette-input {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	padding: 0.875rem 1rem;
	border-bottom: 1px solid #eef0f2;
}

.app-topbar__palette-input input {
	flex: 1;
	min-width: 0;
	border: none;
	outline: none;
	font-size: 0.9375rem;
	background: transparent;
}

.app-topbar__results {
	margin: 0;
	padding: 0.5rem;
	overflow-y: auto;
	list-style: none;
}

.app-topbar__result {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	width: 100%;
	padding: 0.625rem 0.75rem;
	border: none;
	border-radius: 0.75rem;
	background: transparent;
}

.app-topbar__result.is-active,
.app-topbar__result:hover {
	background: #f3f4f6;
}

.app-topbar__empty {
	padding: 1.5rem 1rem;
	text-align: center;
	font-size: 0.875rem;
	color: #6b7280;
}

@media (min-width: 640px) {
	.app-topbar__shortcut {
		display: inline-flex;
	}
}

@media (max-width: 767px) {
	.app-topbar__inner {
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 0.5rem;
		padding: 0 0.75rem;
	}

	.app-topbar__center {
		display: none;
	}

	.app-topbar__search-toggle {
		display: inline-flex;
	}

	.app-topbar__lang {
		display: none;
	}

	.app-topbar__right {
		gap: 0.375rem;
	}

	.app-topbar__icon-btn,
	.app-topbar__avatar :deep(.flex) {
		width: 2.25rem;
		height: 2.25rem;
	}
}
</style>
