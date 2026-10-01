import router from "@/router"
import { createResource } from "frappe-ui"

export const employeeResource = createResource({
	url: "hrms.api.get_current_employee_info",
	cache: "hrms:employee",
	onError(error) {
		if (error && error.exc_type === "AuthenticationError") {
			// Avoid fighting an in-flight kiosk portal login (session cookie not ready yet).
			if (window.location.pathname.includes("/login")) return
			router.push({ name: "Login" })
		}
	},
})
