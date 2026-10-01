import { computed, reactive } from "vue"
import { createResource, frappeRequest } from "frappe-ui"
import { frappeFormLogin } from "@/utils/frappeFormLogin"
import { getDeviceId } from "@/utils/rememberedUsers"
import { userResource } from "./user"
import { employeeResource } from "./employee"
import router from "@/router"

export const PORTAL_HOME_URL = "/agents/dashboard/attendance"

export function sessionUser() {
	let cookies = new URLSearchParams(document.cookie.split("; ").join("&"))
	let _sessionUser = cookies.get("user_id")
	if (_sessionUser === "Guest") {
		_sessionUser = null
	}
	return _sessionUser
}

function shouldEnterPortal(response) {
	if (!response || response.verification) return false
	if (response.message === "Password Reset") return false
	if (response.message === "Logged In") return true
	// Some Frappe builds only return home_page on success.
	return Boolean(response.home_page)
}

function enterPortalAfterLogin(usr) {
	session.user = sessionUser() || usr
	// Full navigation so session cookies and router guards load cleanly (Ionic + Frappe).
	window.location.assign(PORTAL_HOME_URL)
}

async function resolveKioskLoginUsername(username) {
	const value = (username || "").trim()
	if (!value) return value
	try {
		const response = await frappeRequest({
			url: "/api/method/hrms.api.kiosk.resolve_login",
			method: "GET",
			params: { username: value },
		})
		if (typeof response === "string" && response) return response
		if (response?.message) return response.message
		return value
	} catch {
		return value
	}
}

export const session = reactive({
	login: async (username, password, deviceId) => {
		const usr = await resolveKioskLoginUsername(username)
		const response = await frappeFormLogin({
			usr,
			pwd: password,
			device_id: deviceId || getDeviceId(),
		})
		if (shouldEnterPortal(response)) {
			enterPortalAfterLogin(usr)
		}
		return response
	},
	otp: async (tmp_id, otp, deviceId) => {
		const response = await frappeFormLogin({
			tmp_id,
			otp,
			device_id: deviceId || getDeviceId(),
		})
		if (shouldEnterPortal(response)) {
			enterPortalAfterLogin(session.user)
		}
		return response
	},
	logout: createResource({
		url: "logout",
		onSuccess() {
			userResource.reset()
			employeeResource.reset()

			session.user = sessionUser()
			router.replace({ name: "Login" })
			window.location.reload()
		},
	}),
	user: sessionUser(),
	isLoggedIn: computed(() => !!session.user),
})
