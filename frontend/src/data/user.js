import router from "@/router"
import { createResource } from "frappe-ui"

export const userResource = createResource({
	url: "hrms.api.get_current_user_info",
	cache: "hrms:user",
	onError(error) {
		if (error && error.exc_type === "AuthenticationError") {
			if (window.location.pathname.includes("/login")) return
			router.push({ name: "Login" })
		}
	},
})
