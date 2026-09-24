import { computed, reactive } from "vue"
import { createResource, frappeRequest } from "frappe-ui"
import { frappeFormLogin } from "@/utils/frappeFormLogin"
import { getDeviceId } from "@/utils/rememberedUsers"
import { userResource } from "./user"
import { employeeResource } from "./employee"
import router from "@/router"

const PORTAL_HOME = { name: "AttendanceDashboard" }
const PORTAL_HOME_URL = "/agents/dashboard/attendance"

export function sessionUser() {
	let cookies = new URLSearchParams(document.cookie.split("; ").join("&"))
	let _sessionUser = cookies.get("user_id")
	if (_sessionUser === "Guest") {
		_sessionUser = null
	}
	return _sessionUser
}

async function handleLogin(response, usr) {
	if (response?.message !== "Logged In") return

	session.user = sessionUser() || usr
	await Promise.all([userResource.reload(), employeeResource.reload()])
	if (userResource.data?.name) {
		session.user = userResource.data.name
	}

	await router.replace(PORTAL_HOME)
	if (router.currentRoute.value.name === "Login") {
		window.location.assign(PORTAL_HOME_URL)
	}
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
		await handleLogin(response, usr)
		return response
	},
	otp: async (tmp_id, otp, deviceId) => {
		const response = await frappeFormLogin({
			tmp_id,
			otp,
			device_id: deviceId || getDeviceId(),
		})
		await handleLogin(response, session.user)
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
