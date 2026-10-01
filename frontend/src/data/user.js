import router from "@/router"
import { createResource } from "frappe-ui"

export const userResource = createResource({
	url: "hrms.api.get_current_user_info",
	cache: "hrms:user",
	onError(error) {
		if (error && error.exc_type === "AuthenticationError") {
			if (window.location.pathname.includes("/login")) return
			// My Work already has a desk session. Sending them to Login would loop.
			if (window.frappe?.boot?.staff_pro_my_work) return
			router.push({ name: "Login" })
		}
	},
})
