/** Roles that can open Frappe Desk (admin / HR / accounts). */
const DESK_ROLES = new Set([
	"Administrator",
	"System Manager",
	"HR Manager",
	"HR User",
	"Accounts Manager",
	"Accounts User",
	"Payroll Manager",
])

/**
 * True when the user should see the Desk bridge from the employee PWA.
 * Pure ESS / Website User employees stay in /hrms.
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

export const DESK_HOME = "/desk/workforce"

export const DESK_SHORTCUTS = [
	{ title: "People", path: "/desk/workforce", icon: "users" },
	{ title: "Time", path: "/desk/time", icon: "clock" },
	{ title: "Pay", path: "/desk/pay", icon: "dollar-sign" },
	{ title: "Talent", path: "/desk/talent", icon: "award" },
	{ title: "Finance & Admin", path: "/desk/finance-&-admin", icon: "briefcase" },
]
