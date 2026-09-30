<template>
	<ion-page>
		<ion-content>
			<div class="mx-auto flex w-full max-w-3xl flex-col gap-4 p-4 pb-16">
				<header class="flex items-start justify-between gap-3">
					<div>
						<p class="text-xs font-semibold uppercase tracking-widest text-gray-500">
							{{ __("Belize") }}
						</p>
						<h1 class="text-2xl font-semibold text-gray-900">{{ __("TD4 Supplementary") }}</h1>
						<p class="text-sm text-gray-600">
							{{ __("Statement of Emoluments Paid for income tax purposes.") }}
						</p>
					</div>
					<Button variant="ghost" @click="signOut">{{ __("Sign out") }}</Button>
				</header>

				<p v-if="loading" class="text-sm text-gray-500">{{ __("Loading...") }}</p>
				<p v-else-if="loadError" class="text-sm text-red-600">{{ loadError }}</p>

				<template v-else-if="form">
					<p
						v-if="!readOnly"
						class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
					>
						{{ __("Complete and sign this TD4. It is saved under your name.") }}
					</p>
					<p
						v-else
						class="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
					>
						{{
							form.filled_by_name
								? __("Signed and filed by {0}.", [form.filled_by_name])
								: __("This TD4 has been signed and filed.")
						}}
					</p>

					<p class="text-sm text-gray-600">
						{{
							__(
								"Commissions should be included in total emoluments and taxable emoluments. Total income (C) must equal taxable income (D) + non-taxable income (E) + commissions (F)."
							)
						}}
					</p>

					<section class="rounded-md border bg-white p-4">
						<h2 class="text-sm font-semibold uppercase tracking-wide text-gray-500">
							{{ __("Employer") }}
						</h2>
						<dl class="mt-3 grid gap-3 sm:grid-cols-2">
							<div>
								<dt class="text-xs text-gray-500">{{ __("Employer Name") }}</dt>
								<dd class="text-sm text-gray-900">{{ form.employer_name || "—" }}</dd>
							</div>
							<div>
								<dt class="text-xs text-gray-500">{{ __("(H) Employer TIN") }}</dt>
								<dd class="text-sm text-gray-900">{{ form.employer_tin || "—" }}</dd>
							</div>
							<div class="sm:col-span-2">
								<dt class="text-xs text-gray-500">{{ __("Employer Address") }}</dt>
								<dd class="whitespace-pre-line text-sm text-gray-900">
									{{ form.employer_address || "—" }}
								</dd>
							</div>
						</dl>
					</section>

					<section class="rounded-md border bg-white p-4">
						<h2 class="text-sm font-semibold uppercase tracking-wide text-gray-500">
							{{ __("Employee") }}
						</h2>
						<p class="mt-3 text-base font-medium text-gray-900">{{ form.employee_name }}</p>
						<label class="mt-3 block text-sm text-gray-700">
							{{ __("Employee Address") }}
							<textarea
								v-model="form.employee_address"
								rows="3"
								class="mt-1 w-full rounded-md border px-3 py-2 text-sm"
								:disabled="readOnly"
							/>
						</label>
						<div class="mt-3 grid gap-3 sm:grid-cols-2">
							<label class="block text-sm text-gray-700">
								{{ __("(A) Social Security") }}
								<input
									v-model="form.social_security"
									type="text"
									class="mt-1 w-full rounded-md border px-3 py-2 text-sm"
									:disabled="readOnly"
								/>
							</label>
							<label class="block text-sm text-gray-700">
								{{ __("(I) Employee TIN") }}
								<input
									v-model="form.employee_tin"
									type="text"
									class="mt-1 w-full rounded-md border px-3 py-2 text-sm"
									:disabled="readOnly"
								/>
							</label>
						</div>
					</section>

					<section class="rounded-md border bg-white p-4">
						<h2 class="text-sm font-semibold uppercase tracking-wide text-gray-500">
							{{ __("Emoluments") }}
						</h2>
						<div class="mt-3 grid gap-3 sm:grid-cols-2">
							<label class="block text-sm text-gray-700">
								{{ __("Reporting Year") }}
								<div class="mt-1 flex items-center justify-between rounded-md border px-2 py-1">
									<button
										type="button"
										class="h-9 w-9 rounded text-lg text-gray-700 disabled:opacity-40"
										:disabled="readOnly || Number(form.reporting_year) <= 2000"
										@click="shiftYear(-1)"
									>
										−
									</button>
									<span class="text-base font-semibold text-gray-900">{{ form.reporting_year }}</span>
									<button
										type="button"
										class="h-9 w-9 rounded text-lg text-gray-700 disabled:opacity-40"
										:disabled="readOnly || Number(form.reporting_year) >= 2100"
										@click="shiftYear(1)"
									>
										+
									</button>
								</div>
							</label>
							<label class="block text-sm text-gray-700">
								{{ __("(B) Number of Weeks") }}
								<input
									v-model="form.number_of_weeks"
									type="number"
									min="1"
									max="53"
									step="1"
									class="mt-1 w-full rounded-md border px-3 py-2 text-sm"
									:disabled="readOnly"
								/>
							</label>
							<label v-for="field in moneyFields" :key="field.name" class="block text-sm text-gray-700">
								{{ __(field.label) }}
								<input
									v-model="form[field.name]"
									type="number"
									min="0"
									step="0.01"
									class="mt-1 w-full rounded-md border px-3 py-2 text-sm"
									:disabled="readOnly"
								/>
							</label>
						</div>
						<p class="mt-3 text-sm" :class="incomeMatches ? 'text-green-700' : 'text-red-600'">
							{{
								incomeMatches
									? __("Income total matches (C).")
									: __("Total income (C) must equal (D) + (E) + (F). Current sum is {0}.", [
											formatMoney(partsTotal),
										])
							}}
						</p>
					</section>

					<section class="rounded-md border bg-white p-4">
						<h2 class="text-sm font-semibold uppercase tracking-wide text-gray-500">
							{{ __("Declaration") }}
						</h2>
						<div class="relative mt-3">
							<span class="block text-sm text-gray-700">{{ __("Date Signed") }}</span>
							<button
								type="button"
								class="mt-1 w-full rounded-md border px-3 py-2 text-left text-sm disabled:bg-gray-50"
								:disabled="readOnly"
								@click="dateOpen = !dateOpen"
							>
								{{ form.date_signed ? displayDate(form.date_signed) : __("Select a date") }}
							</button>
							<div
								v-if="dateOpen && !readOnly"
								class="absolute z-20 mt-1 w-full max-w-sm rounded-md border bg-white p-3 shadow-lg"
							>
								<div class="mb-2 flex items-center justify-between">
									<button type="button" class="rounded px-2 py-1 text-sm" @click="shiftMonth(-1)">
										{{ __("Prev") }}
									</button>
									<span class="text-sm font-medium">{{ monthLabel }}</span>
									<button
										type="button"
										class="rounded px-2 py-1 text-sm disabled:opacity-40"
										:disabled="!canGoForward"
										@click="shiftMonth(1)"
									>
										{{ __("Next") }}
									</button>
								</div>
								<div class="grid grid-cols-7 gap-1 text-center text-xs text-gray-500">
									<span v-for="weekday in weekdays" :key="weekday">{{ weekday }}</span>
								</div>
								<div class="mt-1 grid grid-cols-7 gap-1">
									<button
										v-for="day in calendarDays"
										:key="day.key"
										type="button"
										class="h-9 rounded text-sm"
										:class="dayClass(day)"
										:disabled="day.future || day.outside"
										@click="selectDate(day)"
									>
										{{ day.date.getDate() }}
									</button>
								</div>
							</div>
						</div>

						<div class="mt-4">
							<div class="flex items-center justify-between">
								<span class="text-sm text-gray-700">{{ __("Employee Signature") }}</span>
								<button
									v-if="!readOnly"
									type="button"
									class="text-sm text-gray-600 underline"
									@click="clearSignature"
								>
									{{ __("Clear") }}
								</button>
							</div>
							<p v-if="!readOnly" class="mt-1 text-xs text-gray-500">
								{{ __("Draw your signature in the box.") }}
							</p>
							<canvas
								v-if="!readOnly"
								ref="canvasRef"
								class="mt-2 h-40 w-full touch-none rounded-md border bg-white"
							/>
							<img
								v-else-if="form.signature"
								:src="form.signature"
								alt=""
								class="mt-2 h-40 w-full rounded-md border bg-white object-contain"
							/>
							<p v-else class="mt-2 text-sm text-gray-500">{{ __("No signature") }}</p>
						</div>
					</section>

					<p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>

					<div class="flex flex-wrap gap-3">
						<Button v-if="!readOnly" variant="solid" :loading="submitting" @click="submitForm">
							{{ __("Sign and submit") }}
						</Button>
						<a
							v-if="form.signed_pdf"
							:href="form.signed_pdf"
							target="_blank"
							rel="noopener"
							class="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium text-gray-800"
						>
							{{ __("Download signed PDF") }}
						</a>
						<Button v-if="readOnly" variant="outline" @click="router.push({ name: 'MyDocuments' })">
							{{ __("My Documents") }}
						</Button>
					</div>
				</template>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { createResource, toast } from "frappe-ui"
import { computed, inject, nextTick, onMounted, onUnmounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

const __ = inject("$translate")
const session = inject("$session")
const route = useRoute()
const router = useRouter()

const moneyFields = [
	{ name: "total_income", label: "(C) Total Income from Employment" },
	{ name: "total_taxable_income", label: "(D) Total Taxable Income" },
	{ name: "non_taxable_income", label: "(E) Non-Taxable Income" },
	{ name: "commissions", label: "(F) Commissions" },
	{ name: "tax_deducted", label: "(G) Tax Deducted at Source" },
]

const weekdays = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
const form = ref(null)
const loading = ref(true)
const loadError = ref("")
const errorMessage = ref("")
const submitting = ref(false)
const dateOpen = ref(false)
const viewMonth = ref(startOfMonth(new Date()))
const canvasRef = ref(null)
const hasInk = ref(false)

let inkContext = null
let drawing = false
let canvasTries = 0

const readOnly = computed(() => form.value?.status === "Submitted")

const partsTotal = computed(() => {
	if (!form.value) return 0
	return cents(form.value.total_taxable_income) + cents(form.value.non_taxable_income) + cents(form.value.commissions)
})

const incomeMatches = computed(() => cents(form.value?.total_income) === partsTotal.value)

const monthLabel = computed(() =>
	viewMonth.value.toLocaleDateString(undefined, { month: "long", year: "numeric" })
)

const canGoForward = computed(() => {
	const next = new Date(viewMonth.value.getFullYear(), viewMonth.value.getMonth() + 1, 1)
	return next <= startOfMonth(new Date())
})

const calendarDays = computed(() => {
	const start = new Date(viewMonth.value.getFullYear(), viewMonth.value.getMonth(), 1)
	const gridStart = new Date(start)
	gridStart.setDate(1 - start.getDay())
	const today = startOfDay(new Date())
	const days = []
	for (let index = 0; index < 42; index += 1) {
		const date = new Date(gridStart)
		date.setDate(gridStart.getDate() + index)
		days.push({
			key: formatISODate(date),
			date,
			outside: date.getMonth() !== start.getMonth(),
			future: startOfDay(date) > today,
			selected: form.value?.date_signed === formatISODate(date),
		})
	}
	return days
})

const loader = createResource({
	url: "hrms.hr.doctype.td4_form.td4_form.get_td4",
})

watch(
	() => route.params.id,
	() => loadForm(),
	{ immediate: true }
)

watch(loading, async (isLoading) => {
	if (!isLoading && form.value?.status === "Requested") {
		await nextTick()
		prepareCanvas()
	}
})

onMounted(() => {
	window.addEventListener("pointerup", stopDrawing)
})

onUnmounted(() => {
	window.removeEventListener("pointerup", stopDrawing)
})

async function loadForm() {
	const name = route.params.id
	if (!name) return
	inkContext = null
	hasInk.value = false
	canvasTries = 0
	loading.value = true
	loadError.value = ""
	errorMessage.value = ""
	try {
		const data = await loader.submit({ name })
		form.value = {
			...data,
			reporting_year: data.reporting_year || new Date().getFullYear(),
			date_signed: data.date_signed || formatISODate(new Date()),
		}
		if (form.value.date_signed) {
			viewMonth.value = startOfMonth(parseISODate(form.value.date_signed))
		}
	} catch (error) {
		form.value = null
		loadError.value = error?.messages?.[0] || __("This TD4 could not be opened.")
	} finally {
		loading.value = false
	}
}

function shiftYear(delta) {
	const next = Number(form.value.reporting_year || new Date().getFullYear()) + delta
	if (next < 2000 || next > 2100) return
	form.value.reporting_year = next
}

function shiftMonth(delta) {
	const next = new Date(viewMonth.value.getFullYear(), viewMonth.value.getMonth() + delta, 1)
	if (next > startOfMonth(new Date())) return
	viewMonth.value = next
}

function selectDate(day) {
	if (day.future) return
	form.value.date_signed = formatISODate(day.date)
	dateOpen.value = false
}

function dayClass(day) {
	if (day.selected) return "bg-gray-900 text-white"
	if (day.future || day.outside) return "text-gray-300"
	return "text-gray-800 hover:bg-gray-100"
}

function prepareCanvas() {
	const canvas = canvasRef.value
	if (!canvas || readOnly.value) return
	const ratio = window.devicePixelRatio || 1
	const width = canvas.clientWidth || canvas.parentElement?.clientWidth || 320
	if (!canvas.clientWidth && canvasTries < 8) {
		canvasTries += 1
		requestAnimationFrame(prepareCanvas)
		return
	}
	const height = 160
	canvas.width = Math.floor(width * ratio)
	canvas.height = Math.floor(height * ratio)
	inkContext = canvas.getContext("2d")
	inkContext.setTransform(ratio, 0, 0, ratio, 0, 0)
	inkContext.lineWidth = 2.2
	inkContext.lineCap = "round"
	inkContext.lineJoin = "round"
	inkContext.strokeStyle = "#111827"
	hasInk.value = false
	canvas.onpointerdown = startDrawing
	canvas.onpointermove = draw
}

function startDrawing(event) {
	if (!inkContext) return
	drawing = true
	hasInk.value = true
	inkContext.beginPath()
	const point = pointerPos(event)
	inkContext.moveTo(point.x, point.y)
	canvasRef.value.setPointerCapture?.(event.pointerId)
}

function draw(event) {
	if (!drawing || !inkContext) return
	const point = pointerPos(event)
	inkContext.lineTo(point.x, point.y)
	inkContext.stroke()
}

function stopDrawing() {
	drawing = false
}

function pointerPos(event) {
	const rect = canvasRef.value.getBoundingClientRect()
	return { x: event.clientX - rect.left, y: event.clientY - rect.top }
}

function clearSignature() {
	const canvas = canvasRef.value
	if (!canvas || !inkContext) return
	const ratio = window.devicePixelRatio || 1
	inkContext.setTransform(1, 0, 0, 1, 0, 0)
	inkContext.clearRect(0, 0, canvas.width, canvas.height)
	inkContext.setTransform(ratio, 0, 0, ratio, 0, 0)
	hasInk.value = false
}

async function submitForm() {
	errorMessage.value = ""
	const weeks = Number(form.value.number_of_weeks)
	if (!String(form.value.employee_address || "").trim()) {
		errorMessage.value = __("Employee address is required.")
		return
	}
	if (!String(form.value.social_security || "").trim() || !String(form.value.employee_tin || "").trim()) {
		errorMessage.value = __("Social security number and employee TIN are required.")
		return
	}
	if (!Number.isInteger(weeks) || weeks < 1 || weeks > 53) {
		errorMessage.value = __("Number of weeks must be a whole number from 1 to 53.")
		return
	}
	if (!form.value.date_signed) {
		errorMessage.value = __("Date signed is required.")
		return
	}
	if (!hasInk.value) {
		errorMessage.value = __("Sign the form before submitting.")
		return
	}
	if (!incomeMatches.value) {
		errorMessage.value = __("Total income (C) must equal taxable income (D) + non-taxable income (E) + commissions (F).")
		return
	}
	submitting.value = true
	try {
		await createResource({
			url: "hrms.hr.doctype.td4_form.td4_form.submit_td4",
		}).submit({
			name: form.value.name,
			values: {
				reporting_year: Number(form.value.reporting_year),
				employee_address: form.value.employee_address,
				social_security: form.value.social_security,
				employee_tin: form.value.employee_tin,
				number_of_weeks: Number(form.value.number_of_weeks),
				total_income: Number(form.value.total_income || 0),
				total_taxable_income: Number(form.value.total_taxable_income || 0),
				non_taxable_income: Number(form.value.non_taxable_income || 0),
				commissions: Number(form.value.commissions || 0),
				tax_deducted: Number(form.value.tax_deducted || 0),
				date_signed: form.value.date_signed,
				signature: canvasRef.value.toDataURL("image/png"),
			},
		})
		toast({
			title: __("Success"),
			text: __("Your TD4 has been signed and filed."),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
		router.replace({ name: "AttendanceDashboard" })
	} catch (error) {
		errorMessage.value = error?.messages?.[0] || __("The TD4 could not be submitted.")
	} finally {
		submitting.value = false
	}
}

function signOut() {
	session.logout.submit()
}

function cents(value) {
	const number = Number(value)
	if (!Number.isFinite(number)) return 0
	return Math.round(number * 100)
}

function formatMoney(valueInCents) {
	return (valueInCents / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatISODate(date) {
	const month = String(date.getMonth() + 1).padStart(2, "0")
	const day = String(date.getDate()).padStart(2, "0")
	return `${date.getFullYear()}-${month}-${day}`
}

function parseISODate(value) {
	const [year, month, day] = String(value).slice(0, 10).split("-").map(Number)
	return new Date(year, month - 1, day)
}

function startOfMonth(date) {
	return new Date(date.getFullYear(), date.getMonth(), 1)
}

function startOfDay(date) {
	return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function displayDate(value) {
	const date = parseISODate(value)
	const day = String(date.getDate()).padStart(2, "0")
	const month = String(date.getMonth() + 1).padStart(2, "0")
	return `${day}-${month}-${date.getFullYear()}`
}
</script>
