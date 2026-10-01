/** Roles that can open Frappe Desk (admin / HR / accounts). */
const DESK_ROLES = new Set([
	"Administrator",
	"System Manager",
	"HR Manager",
	"HR User",
	"HR Assistant",
	"Accounts Manager",
	"Accounts User",
	"Payroll Manager",
])

export const HR_ASSISTANT_ROLE = "HR Assistant"

export function isHrAssistant(user) {
	if (!user?.roles?.length) return false
	return user.roles.includes(HR_ASSISTANT_ROLE)
}

export function isMyWorkSession() {
	return Boolean(window.frappe?.boot?.staff_pro_my_work)
}

/**
 * HR Assistants who are also active employees use the /agents PWA for clock-in and self-service.
 * The agents page boot flag is set from the desk session, so My Work does not depend on a
 * JavaScript-readable user_id cookie.
 */
export function canUseMyWorkPortal(user) {
	if (isMyWorkSession()) return true
	return isHrAssistant(user)
}

/**
 * True when the user should see the Desk bridge from the employee PWA.
 * Pure ESS / Website User employees stay in /agents.
 */
export function canOpenDesk(user) {
	if (!user) return false
	if (user.user_type && user.user_type === "Website User") {
		return false
	}
	const roles = user.roles || []
	if (!roles.length) return false
	return roles.some((role) => DESK_ROLES.has(role))
}

export const DESK_HOME = "/desk/dashboard-view/Human Resource"

export const DESK_SHORTCUTS = [
	{ title: "People", path: "/desk/dashboard-view/Human Resource", icon: "users" },
	{ title: "Time", path: "/desk/time", icon: "clock" },
	{ title: "Payroll", path: "/desk/pay", icon: "dollar-sign" },
	{ title: "Talent", path: "/desk/talent", icon: "award" },
	{ title: "Finance", path: "/desk/finance", icon: "file-text" },
	{ title: "Admin", path: "/desk/admin", icon: "settings" },
]
