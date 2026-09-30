<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<div v-if="props.id && requestKind.loading" class="p-4 text-sm text-gray-500">
				{{ __("Loading...") }}
			</div>
			<JobLetter v-else-if="isJobLetter" :id="props.id" />
			<FormView
				v-else-if="formFields.data"
				doctype="HR Request"
				v-model="hrRequest"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="allowAttachments"
				:showDownloadPDFButton="showDownloadPDF"
				@validateForm="validateForm"
			/>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { createResource } from "frappe-ui"
import { computed, ref, watch, inject } from "vue"
import { useRoute } from "vue-router"

import FormView from "@/components/FormView.vue"
import JobLetter from "@/views/hr_request/JobLetter.vue"

const employee = inject("$employee")
const route = useRoute()

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

const HIDDEN_ON_CREATE = [
	"employee",
	"employee_name",
	"company",
	"designation",
	"department",
	"date_of_joining",
	"status",
	"assigned_to",
	"assigned_to_name",
	"resolution",
	"resolved_on",
	"resolution_section",
]

const READONLY_ON_DETAIL = [
	"employee",
	"employee_name",
	"company",
	"designation",
	"department",
	"date_of_joining",
	"status",
	"assigned_to",
	"assigned_to_name",
	"resolution",
	"resolved_on",
]

const JOB_LETTER_FIELDS = [
	"letter_purpose",
	"addressed_to",
	"job_letter_section",
	"recipient_address",
	"honorific",
	"annual_salary",
	"biweekly_salary",
	"letter_preview",
]

const hrRequest = ref({})

const requestKind = createResource({
	url: "hrms.hr.job_letter.get_request_kind",
	params: props.id ? { name: props.id } : {},
	auto: Boolean(props.id),
})

const isJobLetter = computed(() => {
	if (props.id) return requestKind.data?.request_type === "Job Letter"
	return route.query.request_type === "Job Letter" || hrRequest.value.request_type === "Job Letter"
})

const allowAttachments = computed(() => !isJobLetter.value)

const showDownloadPDF = computed(
	() => hrRequest.value.request_type === "Job Letter" && ["Resolved", "Approved"].includes(hrRequest.value.status)
)

const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "HR Request" },
	auto: true,
	transform(data) {
		return data
			.filter((field) => field.fieldtype !== "Column Break")
			.map((field) => {
				if (!props.id && HIDDEN_ON_CREATE.includes(field.fieldname)) {
					field.hidden = true
				}
				if (props.id && READONLY_ON_DETAIL.includes(field.fieldname)) {
					field.read_only = true
				}
				if (field.fieldname === "annual_salary" || field.fieldname === "biweekly_salary") {
					field.read_only = true
				}
				if (JOB_LETTER_FIELDS.includes(field.fieldname)) {
					field.hidden = (hrRequest.value.request_type || route.query.request_type) !== "Job Letter"
				}
				return field
			})
	},
})

watch(
	() => route.query.request_type,
	(requestType) => {
		if (!props.id && requestType && !hrRequest.value.request_type) {
			hrRequest.value.request_type = requestType
			if (requestType === "Job Letter" && !hrRequest.value.subject) {
				hrRequest.value.subject = "Job Letter Request"
			}
		}
	},
	{ immediate: true }
)

watch(
	() => hrRequest.value.request_type,
	(requestType) => {
		if (!formFields.data) return
		formFields.data.forEach((field) => {
			if (JOB_LETTER_FIELDS.includes(field.fieldname)) {
				field.hidden = requestType !== "Job Letter"
			}
		})
		if (requestType === "Job Letter" && !hrRequest.value.subject) {
			hrRequest.value.subject = "Job Letter Request"
		}
	}
)

watch(
	() => hrRequest.value.employee,
	(employeeId) => {
		if (props.id && employeeId && employeeId !== employee.data.name) {
			formFields.data?.forEach((field) => {
				field.read_only = true
			})
		}
	}
)

function validateForm() {
	hrRequest.value.employee = employee.data.name
	hrRequest.value.company = employee.data.company
	if (!hrRequest.value.status) hrRequest.value.status = "Open"
	if (!hrRequest.value.priority) hrRequest.value.priority = "Medium"
	if (hrRequest.value.request_type === "Job Letter" && !hrRequest.value.subject) {
		hrRequest.value.subject = "Job Letter Request"
	}
}
</script>
