<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex flex-col h-full w-full">
				<header
					class="flex flex-row bg-white shadow-sm py-4 px-3 items-center justify-between border-b sticky top-0 z-10"
				>
					<div class="flex flex-row items-center">
						<Button variant="ghost" class="!pl-0 hover:bg-white" @click="router.back()">
							<FeatherIcon name="chevron-left" class="h-5 w-5" />
						</Button>
						<h2 class="text-xl font-semibold text-gray-900">{{ __("Job Letter") }}</h2>
					</div>
				</header>

				<div v-if="loading" class="p-4 text-sm text-gray-500">{{ __("Loading...") }}</div>

				<div v-else class="flex flex-col gap-4 p-4">
					<p v-if="!props.id" class="text-sm text-gray-500">
						{{ __("Choose who this letter is addressed to, then review it before you submit.") }}
					</p>
					<div v-else class="flex flex-row items-center justify-between">
						<div class="text-sm text-gray-500">{{ letter.subject }}</div>
						<Badge
							variant="outline"
							:theme="colorMap[letter.status] || 'gray'"
							:label="__(letter.status)"
							size="md"
						/>
					</div>

					<template v-if="!props.id">
						<label class="block text-sm text-gray-700">
							{{ __("Addressed To") }}
							<input
								v-model="addressedTo"
								type="text"
								class="mt-1 w-full rounded-md border px-3 py-2 text-sm"
								:placeholder="__('Atlantic Bank Ltd.')"
							/>
						</label>
						<label class="block text-sm text-gray-700">
							{{ __("Recipient Address") }}
							<textarea
								v-model="recipientAddress"
								rows="3"
								class="mt-1 w-full rounded-md border px-3 py-2 text-sm"
								:placeholder="__('Street, city')"
							/>
						</label>
					</template>

					<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
						<label class="block text-sm text-gray-700">
							{{ __("Yearly Salary") }}
							<input
								:value="formatSalary(yearlySalary, false)"
								type="text"
								readonly
								tabindex="-1"
								class="mt-1 w-full rounded-md border bg-gray-50 px-3 py-2 text-sm text-gray-900"
							/>
						</label>
						<label class="block text-sm text-gray-700">
							{{ __("Biweekly Salary") }}
							<input
								:value="formatSalary(biweeklySalary, true)"
								type="text"
								readonly
								tabindex="-1"
								class="mt-1 w-full rounded-md border bg-gray-50 px-3 py-2 text-sm text-gray-900"
							/>
						</label>
					</div>
					<p class="text-xs text-gray-500">
						{{ __("Calculated from your hourly rate for an 80-hour pay period.") }}
					</p>

					<p v-if="preview.error && !props.id" class="text-sm text-red-600">
						{{ __("The letter preview could not be loaded.") }}
					</p>
					<iframe
						v-if="previewDocument"
						class="h-[1056px] w-full rounded-md border bg-white"
						:srcdoc="previewDocument"
						:title="__('Job letter preview')"
					></iframe>

					<Button
						v-if="!props.id"
						variant="solid"
						class="w-full py-5 text-base"
						:loading="submitting"
						@click="submitLetter"
					>
						{{ __("Submit for approval") }}
					</Button>

					<template v-else-if="letter.status === 'Resolved' && letter.request_type === 'Job Letter'">
						<Button variant="solid" class="w-full py-5 text-base" @click="downloadLetter">
							{{ __("Download PDF") }}
						</Button>
						<Button variant="subtle" class="w-full py-5 text-base" :loading="printing" @click="askForPrint">
							{{ __("Request office print") }}
						</Button>
					</template>

					<p v-else-if="props.id" class="text-sm text-gray-500">
						{{ __("Staff will review this letter. You can download it after it is approved.") }}
					</p>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { Badge, Button, FeatherIcon, createResource, toast } from "frappe-ui"
import { computed, inject, ref, watch } from "vue"
import { useRouter } from "vue-router"

import { myHRRequests, myJobLetters } from "@/data/hr_requests"

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

const __ = inject("$translate")
const router = useRouter()

const addressedTo = ref("")
const recipientAddress = ref("")
const yearlySalary = ref(null)
const biweeklySalary = ref(null)
const submitting = ref(false)
const printing = ref(false)
const previewHtml = ref("")
const letter = ref({})

const colorMap = {
	Open: "orange",
	"In Progress": "blue",
	"Waiting on Employee": "yellow",
	Resolved: "green",
	Rejected: "red",
	Cancelled: "gray",
}

const existing = createResource({
	url: "hrms.hr.job_letter.get_job_letter",
	onSuccess(data) {
		letter.value = data || {}
		previewHtml.value = data?.letter_html || ""
		yearlySalary.value = data?.annual_salary
		biweeklySalary.value = data?.biweekly_salary
	},
})

const preview = createResource({
	url: "hrms.hr.job_letter.preview_job_letter",
	onSuccess(data) {
		previewHtml.value = data?.html || ""
		yearlySalary.value = data?.annual_salary
		biweeklySalary.value = data?.biweekly_salary
	},
})

const loading = computed(() => Boolean(props.id) && existing.loading && !existing.data)

const previewDocument = computed(() => {
	if (!previewHtml.value) return ""
	return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:#fff;}</style></head><body>${previewHtml.value}</body></html>`
})

if (props.id) {
	existing.fetch({ name: props.id })
}

watch([addressedTo, recipientAddress], () => {
	if (props.id) return
	preview.submit({
		addressed_to: addressedTo.value,
		recipient_address: recipientAddress.value,
	})
}, { immediate: true })

function formatSalary(value, withCents) {
	const amount = Number(value)
	if (!Number.isFinite(amount)) return ""
	const cents = withCents || Math.abs(amount - Math.round(amount)) >= 0.005
	return new Intl.NumberFormat("en-US", {
		style: "currency",
		currency: "USD",
		minimumFractionDigits: cents ? 2 : 0,
		maximumFractionDigits: 2,
	}).format(amount)
}

async function submitLetter() {
	if (!addressedTo.value.trim()) {
		toast({ title: __("Addressed To"), text: __("Enter who the letter is addressed to.") })
		return
	}
	submitting.value = true
	try {
		const created = await createResource({
			url: "hrms.hr.job_letter.submit_job_letter",
		}).submit({
			addressed_to: addressedTo.value.trim(),
			recipient_address: recipientAddress.value,
		})
		myHRRequests.reload()
		myJobLetters.reload()
		router.replace({ name: "HRRequestDetailView", params: { id: created.name } })
	} catch (error) {
		toast({
			title: __("Error"),
			text: error?.messages?.[0] || __("The job letter could not be submitted."),
		})
	} finally {
		submitting.value = false
	}
}

function downloadLetter() {
	const url = `/api/method/hrms.hr.job_letter.download_letter_pdf?name=${encodeURIComponent(letter.value.name)}`
	window.open(url, "_blank")
}

async function askForPrint() {
	printing.value = true
	try {
		await createResource({
			url: "hrms.hr.job_letter.request_office_print",
		}).submit({ name: letter.value.name })
		toast({
			title: __("Print requested"),
			text: __("Staff can print this letter from Employee Requests."),
		})
	} catch (error) {
		toast({
			title: __("Error"),
			text: error?.messages?.[0] || __("The print request could not be sent."),
		})
	} finally {
		printing.value = false
	}
}
</script>
