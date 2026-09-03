import { computed } from "vue"
import { createResource } from "frappe-ui"
import { employeeResource } from "./employee"

export const JOB_LETTER_READY_STATUSES = ["Resolved", "Approved"]

export function canDownloadJobLetter(doc) {
	return doc?.request_type === "Job Letter" && JOB_LETTER_READY_STATUSES.includes(doc?.status)
}

const transformRequestData = (data) => {
	return (data || []).map((request) => {
		request.doctype = "HR Request"
		return request
	})
}

export const hrRequestSummary = createResource({
	url: "hrms.api.get_hr_request_summary",
	auto: true,
	cache: "hrms:hr_request_summary",
})

export const myHRRequests = createResource({
	url: "hrms.api.get_hr_requests",
	params: {
		employee: employeeResource.data.name,
		limit: 10,
	},
	auto: true,
	cache: "hrms:my_hr_requests",
	transform(data) {
		return transformRequestData(data)
	},
	onSuccess() {
		hrRequestSummary.reload()
		myJobLetters.reload()
	},
})

export const myJobLetters = createResource({
	url: "hrms.api.get_hr_requests",
	params: {
		employee: employeeResource.data.name,
		request_type: "Job Letter",
		limit: 10,
	},
	auto: true,
	cache: "hrms:my_job_letters",
	transform(data) {
		return transformRequestData(data)
	},
})

export const hrRequestTypes = createResource({
	url: "hrms.api.get_hr_request_types",
	auto: true,
	cache: "hrms:hr_request_types",
})

export const approvedJobLetters = computed(() =>
	(myJobLetters.data || []).filter((request) => canDownloadJobLetter(request))
)
