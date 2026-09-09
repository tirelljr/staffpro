import { computed, reactive } from "vue"
import { createResource, call } from "frappe-ui"
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

function handleLogin(response) {
	if (response.message === "Logged In") {
		userResource.reload()
		employeeResource.reload()

		session.user = sessionUser()
		router.replace({ path: "/" })
	}
}

export const session = reactive({
	login: async (username, password) => {
		let usr = username
		try {
			const resolved = await call("hrms.api.kiosk.resolve_login", { username })
			if (resolved) usr = resolved
		} catch {
			// Fall back to the typed value; Frappe login still accepts email.
		}
		const response = await call("login", { usr, pwd: password, device_id: getDeviceId() })
		handleLogin(response)
		return response
	},
	otp: async (tmp_id, otp) => {
		const response = await call("login", { tmp_id, otp, device_id: getDeviceId() })
		handleLogin(response)
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
