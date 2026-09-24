import { computed, reactive } from "vue"
import { createResource, call, frappeRequest } from "frappe-ui"
import { getDeviceId } from "@/utils/rememberedUsers"
import { userResource } from "./user"
import { employeeResource } from "./employee"
import router from "@/router"

export function sessionUser() {
	let cookies = new URLSearchParams(document.cookie.split("; ").join("&"))
	let _sessionUser = cookies.get("user_id")
	if (_sessionUser === "Guest") {
		_sessionUser = null
	}
	return _sessionUser
}

async function handleLogin(response) {
	if (response.message === "Logged In") {
		session.user = sessionUser()
		await Promise.all([userResource.reload(), employeeResource.reload()])
		await router.replace({ path: "/" })
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
		const response = await call("login", {
			usr,
			pwd: password,
			device_id: deviceId || getDeviceId(),
		})
		await handleLogin(response)
		return response
	},
	otp: async (tmp_id, otp, deviceId) => {
		const response = await call("login", {
			tmp_id,
			otp,
			device_id: deviceId || getDeviceId(),
		})
		await handleLogin(response)
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
