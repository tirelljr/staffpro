<template>
	<div class="flex flex-col w-full gap-5">
		<div class="text-lg text-gray-800 font-bold">{{ __("Attendance Calendar") }}</div>

		<div class="flex p-1 bg-gray-200 rounded">
			<button
				v-for="option in viewOptions"
				:key="option.key"
				class="px-3 py-2 transition-all rounded-[7px] flex-auto font-medium text-sm"
				:class="
					activeView === option.key
						? 'bg-white drop-shadow text-gray-900'
						: 'text-gray-600'
				"
				@click="activeView = option.key"
			>
				{{ option.label }}
			</button>
		</div>

		<div v-if="activeView === 'calendar'" class="flex flex-col gap-6 bg-white py-6 px-3.5 rounded-lg border-none">
			<!-- Month Change -->
			<div class="flex flex-row justify-between items-center px-4">
				<Button
					icon="chevron-left"
					variant="ghost"
					@click="firstOfMonth = firstOfMonth.subtract(1, 'M')"
				/>
				<span class="text-lg text-gray-800 font-bold">
					{{ firstOfMonth.format("MMMM") }} {{ firstOfMonth.format("YYYY") }}
				</span>
				<Button
					icon="chevron-right"
					variant="ghost"
					@click="firstOfMonth = firstOfMonth.add(1, 'M')"
				/>
			</div>

			<!-- Calendar -->
			<div class="grid grid-cols-7 gap-y-3">
				<div
					v-for="day in DAYS"
					:key="day"
					class="flex justify-center text-gray-600 text-sm font-medium leading-6"
				>
					{{ day }}
				</div>
				<div v-for="blank in firstOfMonth.get('d')" :key="`blank-${blank}`" />
				<div v-for="index in firstOfMonth.endOf('M').get('D')" :key="index">
					<div
						class="h-8 w-8 flex rounded-full mx-auto"
						:class="getEventOnDate(index) && colorMap[getEventOnDate(index)]"
					>
						<span class="text-gray-800 text-sm font-medium m-auto">
							{{ index }}
						</span>
					</div>
				</div>
			</div>

			<hr />

			<!-- Summary -->
			<div class="grid grid-cols-4 mx-2">
				<div v-for="status in summaryStatuses" :key="status" class="flex flex-col gap-1">
					<div class="flex flex-row gap-1 items-center">
						<span class="rounded full h-3 w-3" :class="colorMap[status]" />
						<span class="text-gray-600 text-sm font-medium leading-5"> {{ __(status) }} </span>
					</div>
					<span class="text-gray-800 text-base font-semibold leading-6 mx-auto">
						{{ summary[status] || 0 }}
					</span>
				</div>
			</div>
		</div>

		<div
			v-else-if="activeView === 'day' || activeView === 'list'"
			class="flex flex-col gap-4 bg-white py-6 px-3.5 rounded-lg border-none"
		>
			<AttendanceHoursView
				:mode="activeView"
				:from-date="fromDate"
				:to-date="toDate"
				:preset="preset"
				:job-filter="jobFilter"
				:rows="hoursBoard.data?.rows || []"
				:totals="hoursBoard.data?.totals || {}"
				:jobs="hoursBoard.data?.jobs || []"
				:employee-name="hoursBoard.data?.employee_name || ''"
				:loading="hoursBoard.loading"
				@update:from-date="onFromDate"
				@update:to-date="onToDate"
				@update:preset="onPreset"
				@update:job-filter="jobFilter = $event"
				@note-added="fetchHours"
			/>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { createResource } from "frappe-ui"

import AttendanceHoursView from "@/components/AttendanceHoursView.vue"
import { employeeUpcomingPay } from "@/data/hours"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const socket = inject("$socket")
const firstOfMonth = ref(dayjs().date(1).startOf("D"))
const activeView = ref("day")
const fromDate = ref(dayjs().format("YYYY-MM-DD"))
const toDate = ref(dayjs().format("YYYY-MM-DD"))
const preset = ref("current_pay_period")
const jobFilter = ref("")

const viewOptions = [
	{ key: "calendar", label: __("Calendar") },
	{ key: "day", label: __("Day View") },
	{ key: "list", label: __("List View") },
]

const colorMap = {
	Present: "bg-green-300",
	"Work From Home": "bg-green-300",
	"Half Day": "bg-yellow-200",
	Absent: "bg-red-200",
	"On Leave": "bg-blue-300",
	Holiday: "bg-gray-300",
}

// __("Present"), __("Half Day"), __("Absent"), __("On Leave"), __("Work From Home")
const summaryStatuses = ["Present", "Half Day", "Absent", "On Leave"]

const summary = computed(() => {
	const summary = {}

	for (const status of Object.values(calendarEvents.data || {})) {
		let updatedStatus = status === "Work From Home" ? "Present" : status
		if (updatedStatus in summary) {
			summary[updatedStatus] += 1
		} else {
			summary[updatedStatus] = 1
		}
	}

	return summary
})

watch(
	() => firstOfMonth.value,
	() => {
		calendarEvents.fetch()
	}
)

const getEventOnDate = (date) => {
	return calendarEvents.data?.[firstOfMonth.value.date(date).format("YYYY-MM-DD")]
}

const getFirstLetter = (s) => Array.from(s.trim())[0] // Unicode

const DAYS = [
	getFirstLetter(__("Sunday")),
	getFirstLetter(__("Monday")),
	getFirstLetter(__("Tuesday")),
	getFirstLetter(__("Wednesday")),
	getFirstLetter(__("Thursday")),
	getFirstLetter(__("Friday")),
	getFirstLetter(__("Saturday")),
]

const calendarEvents = createResource({
	url: "hrms.api.get_attendance_calendar_events",
	auto: true,
	cache: "hrms:attendance_calendar_events",
	makeParams() {
		return {
			from_date: firstOfMonth.value.format("YYYY-MM-DD"),
			to_date: firstOfMonth.value.endOf("M").format("YYYY-MM-DD"),
		}
	},
})

const hoursBoard = createResource({
	url: "hrms.api.get_employee_hours",
	auto: false,
	cache: "hrms:employee_hours",
	makeParams() {
		if (preset.value && preset.value !== "custom") {
			return { preset: preset.value }
		}
		return {
			from_date: fromDate.value,
			to_date: toDate.value,
		}
	},
	onSuccess(data) {
		if (data?.from_date) fromDate.value = data.from_date
		if (data?.to_date) toDate.value = data.to_date
	},
})

function fetchHours() {
	hoursBoard.reload()
}

function onFromDate(value) {
	fromDate.value = value
	preset.value = "custom"
	if (fromDate.value && toDate.value && fromDate.value > toDate.value) {
		toDate.value = fromDate.value
	}
	fetchHours()
}

function onToDate(value) {
	toDate.value = value
	preset.value = "custom"
	if (fromDate.value && toDate.value && fromDate.value > toDate.value) {
		fromDate.value = toDate.value
	}
	fetchHours()
}

function onPreset(value) {
	preset.value = value
	if (value !== "custom") fetchHours()
}

watch(
	activeView,
	(view) => {
		if (view !== "calendar" && !hoursBoard.data) {
			fetchHours()
		}
	},
	{ immediate: true }
)

function onHoursListUpdate(data) {
	if (data.doctype === "Attendance" || data.doctype === "Employee Checkin") {
		if (activeView.value !== "calendar") fetchHours()
		employeeUpcomingPay.reload()
	}
}

onMounted(() => {
	socket?.emit("doctype_subscribe", "Attendance")
	socket?.emit("doctype_subscribe", "Employee Checkin")
	socket?.on("list_update", onHoursListUpdate)
})

onBeforeUnmount(() => {
	socket?.emit("doctype_unsubscribe", "Attendance")
	socket?.emit("doctype_unsubscribe", "Employee Checkin")
	socket?.off("list_update", onHoursListUpdate)
})
</script>
