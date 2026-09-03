import { createResource } from "frappe-ui"

export const employeeUpcomingPay = createResource({
	url: "hrms.api.get_employee_upcoming_pay",
	auto: true,
	cache: "hrms:employee_upcoming_pay",
})
