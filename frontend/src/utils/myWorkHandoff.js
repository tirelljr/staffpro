import { call } from "frappe-ui"

import { session } from "@/data/session"

export const MY_WORK_HANDOFF_KEY = "staff_pro_my_work_handoff"

/**
 * Desk My Work stores a one-time token, then opens /agents.
 * Redeem it so the portal continues the desk session without a password.
 */
export async function consumeMyWorkHandoff() {
	let token = ""
	try {
		token = sessionStorage.getItem(MY_WORK_HANDOFF_KEY) || ""
		if (token) sessionStorage.removeItem(MY_WORK_HANDOFF_KEY)
	} catch {
		return false
	}
	if (!token) return false

	try {
		const response = await call("hrms.hr.my_work_portal.consume_handoff", { token })
		const user = response?.user
		if (!user || user === "Guest") return false
		session.user = user
		if (!window.frappe) window.frappe = {}
		if (!window.frappe.boot) window.frappe.boot = {}
		window.frappe.boot.session_user = user
		window.frappe.boot.staff_pro_my_work = Boolean(response.my_work)
		return true
	} catch {
		return false
	}
}
