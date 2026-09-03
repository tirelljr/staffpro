<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col sm:flex-row sm:flex-wrap gap-2 sm:items-center">
			<label class="flex flex-col gap-1 text-xs text-gray-500 font-medium">
				{{ __("From") }}
				<input
					type="date"
					class="rounded-md border border-gray-200 bg-white px-2.5 py-2 text-sm text-gray-800"
					:value="fromDate"
					@change="$emit('update:fromDate', $event.target.value)"
				/>
			</label>
			<label class="flex flex-col gap-1 text-xs text-gray-500 font-medium">
				{{ __("To") }}
				<input
					type="date"
					class="rounded-md border border-gray-200 bg-white px-2.5 py-2 text-sm text-gray-800"
					:value="toDate"
					@change="$emit('update:toDate', $event.target.value)"
				/>
			</label>
			<label class="flex flex-col gap-1 text-xs text-gray-500 font-medium sm:min-w-44">
				{{ __("Quick Dates") }}
				<select
					class="rounded-md border border-gray-200 bg-white px-2.5 py-2 text-sm text-gray-800"
					:value="preset"
					@change="$emit('update:preset', $event.target.value)"
				>
					<option v-for="option in presetOptions" :key="option.value" :value="option.value">
						{{ option.label }}
					</option>
				</select>
			</label>
			<label
				v-if="mode === 'day'"
				class="flex flex-col gap-1 text-xs text-gray-500 font-medium sm:min-w-44"
			>
				{{ __("Job / Absence") }}
				<select
					class="rounded-md border border-gray-200 bg-white px-2.5 py-2 text-sm text-gray-800"
					:value="jobFilter"
					@change="$emit('update:jobFilter', $event.target.value)"
				>
					<option value="">{{ __("All Jobs And Absence") }}</option>
					<option v-for="job in jobs" :key="job" :value="job">{{ job }}</option>
				</select>
			</label>
		</div>

		<div
			class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-md bg-gray-100 px-3 py-2.5"
		>
			<div v-if="mode === 'list'" class="text-sm font-semibold text-gray-800 text-center sm:flex-1">
				{{ employeeName }}
			</div>
			<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs sm:text-sm text-gray-600 font-medium sm:ml-auto">
				<span>{{ __("Total Hours:") }} {{ formatHours(displayTotals.total, true) }}</span>
				<span>{{ __("Unpaid Hours:") }} {{ formatHours(displayTotals.unpaid, true) }}</span>
				<span>{{ __("Paid Hours:") }} {{ formatHours(displayTotals.paid, true) }}</span>
			</div>
		</div>

		<div v-if="loading" class="text-sm text-gray-500 py-6 text-center">{{ __("Loading hours...") }}</div>
		<div v-else-if="!visibleRows.length" class="text-sm text-gray-500 py-6 text-center">
			{{ __("No hours for this date range.") }}
		</div>
		<div v-else class="overflow-x-auto -mx-1">
			<table class="w-full min-w-[720px] text-left text-xs text-gray-800 border-collapse">
				<thead>
					<tr class="bg-gray-100 text-gray-600 font-semibold">
						<th v-if="mode === 'day'" class="px-2 py-2 whitespace-nowrap">#</th>
						<th v-if="mode === 'list'" class="px-2 py-2 whitespace-nowrap">{{ __("Day") }}</th>
						<th class="px-2 py-2 whitespace-nowrap">{{ __("Date") }}</th>
						<th class="px-2 py-2 whitespace-nowrap">{{ __("In") }}</th>
						<th class="px-2 py-2 whitespace-nowrap">{{ __("Out") }}</th>
						<template v-if="mode === 'list'">
							<th class="px-2 py-2 whitespace-nowrap">{{ __("Reg") }}</th>
							<th class="px-2 py-2 whitespace-nowrap">{{ __("OT") }}</th>
							<th class="px-2 py-2 whitespace-nowrap">{{ __("DT") }}</th>
							<th class="px-2 py-2 whitespace-nowrap">{{ __("PTO") }}</th>
							<th class="px-2 py-2 whitespace-nowrap">{{ __("Paid") }}</th>
							<th class="px-2 py-2 whitespace-nowrap">{{ __("Unpaid") }}</th>
							<th class="px-2 py-2 whitespace-nowrap">{{ __("Total") }}</th>
						</template>
						<th v-else class="px-2 py-2 whitespace-nowrap">{{ __("Hours") }}</th>
						<th class="px-2 py-2 whitespace-nowrap">{{ __("Job/Absence") }}</th>
						<th class="px-2 py-2 whitespace-nowrap">{{ __("Shift") }}</th>
					</tr>
				</thead>
				<tbody>
					<template v-for="(row, index) in visibleRows" :key="rowKey(row, index)">
						<tr :class="row.empty ? 'text-gray-300' : index % 2 ? 'bg-gray-50' : 'bg-white'">
							<td v-if="mode === 'day'" class="px-2 py-2 align-top">{{ index + 1 }}</td>
							<td v-if="mode === 'list'" class="px-2 py-2 align-top whitespace-nowrap">
								{{ row.showDay ? dayLabel(row.attendance_date) : "" }}
							</td>
							<td class="px-2 py-2 align-top whitespace-nowrap">
								{{ row.showDay !== false ? dateLabel(row.attendance_date, mode) : "" }}
							</td>
							<td class="px-2 py-2 align-top whitespace-nowrap">{{ clockIn(row) }}</td>
							<td class="px-2 py-2 align-top whitespace-nowrap" :class="missingOut(row) ? 'text-red-600' : ''">
								{{ clockOut(row) }}
							</td>
							<template v-if="mode === 'list'">
								<td class="px-2 py-2 align-top whitespace-nowrap">{{ hoursCell(row.reg) }}</td>
								<td class="px-2 py-2 align-top whitespace-nowrap">{{ hoursCell(row.ot) }}</td>
								<td class="px-2 py-2 align-top whitespace-nowrap">{{ hoursCell(row.dt) }}</td>
								<td class="px-2 py-2 align-top whitespace-nowrap">{{ hoursCell(row.pto) }}</td>
								<td class="px-2 py-2 align-top whitespace-nowrap">{{ hoursCell(row.paid) }}</td>
								<td class="px-2 py-2 align-top whitespace-nowrap">{{ hoursCell(row.unpaid) }}</td>
								<td class="px-2 py-2 align-top whitespace-nowrap">{{ hoursCell(entryHours(row)) }}</td>
							</template>
							<td v-else class="px-2 py-2 align-top whitespace-nowrap">
								{{ formatHours(entryHours(row), true) }}
							</td>
							<td class="px-2 py-2 align-top whitespace-nowrap">{{ row.job || "" }}</td>
							<td class="px-2 py-2 align-top whitespace-nowrap">{{ row.shift || "" }}</td>
						</tr>
						<tr v-if="row.comments?.length" class="bg-white">
							<td :colspan="mode === 'list' ? 13 : 7" class="px-2 pb-2 pt-0 text-gray-500">
								<div v-for="(comment, commentIndex) in row.comments" :key="commentIndex">
									{{ formatHoursNote(comment) }}
								</div>
							</td>
						</tr>
					</template>
				</tbody>
				<tfoot v-if="mode === 'list'">
					<tr class="bg-sky-100 font-semibold text-gray-800">
						<td colspan="4"></td>
						<td class="px-2 py-2 whitespace-nowrap">{{ formatHours(displayTotals.reg, true) }}</td>
						<td class="px-2 py-2 whitespace-nowrap">{{ formatHours(displayTotals.ot, true) }}</td>
						<td class="px-2 py-2 whitespace-nowrap">{{ formatHours(displayTotals.dt, true) }}</td>
						<td class="px-2 py-2 whitespace-nowrap">{{ formatHours(displayTotals.pto, true) }}</td>
						<td class="px-2 py-2 whitespace-nowrap">{{ formatHours(displayTotals.paid, true) }}</td>
						<td class="px-2 py-2 whitespace-nowrap">{{ formatHours(displayTotals.unpaid, true) }}</td>
						<td class="px-2 py-2 whitespace-nowrap">{{ formatHours(displayTotals.total, true) }}</td>
						<td colspan="2"></td>
					</tr>
				</tfoot>
			</table>
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from "vue"

import { formatClock, formatHours, formatHoursNote } from "@/utils/formatters"

const props = defineProps({
	mode: {
		type: String,
		default: "day",
	},
	fromDate: {
		type: String,
		default: "",
	},
	toDate: {
		type: String,
		default: "",
	},
	preset: {
		type: String,
		default: "current_pay_period",
	},
	jobFilter: {
		type: String,
		default: "",
	},
	rows: {
		type: Array,
		default: () => [],
	},
	totals: {
		type: Object,
		default: () => ({}),
	},
	jobs: {
		type: Array,
		default: () => [],
	},
	employeeName: {
		type: String,
		default: "",
	},
	loading: {
		type: Boolean,
		default: false,
	},
})

defineEmits(["update:fromDate", "update:toDate", "update:preset", "update:jobFilter"])

const dayjs = inject("$dayjs")
const __ = inject("$translate")

const presetOptions = [
	{ value: "custom", label: __("Custom") },
	{ value: "today", label: __("Today") },
	{ value: "this_week", label: __("This Week") },
	{ value: "last_week", label: __("Last Week") },
	{ value: "this_month", label: __("This Month") },
	{ value: "previous_pay_period", label: __("Previous Pay Period") },
	{ value: "current_pay_period", label: __("Current Pay Period") },
]

const filteredRows = computed(() => {
	const rows = props.rows || []
	if (props.mode !== "day" || !props.jobFilter) return rows
	return rows.filter((row) => (row.job || "") === props.jobFilter)
})

const displayTotals = computed(() => {
	if (props.mode !== "day" || !props.jobFilter) {
		return props.totals || {}
	}
	const totals = {
		reg: 0,
		ot: 0,
		dt: 0,
		pto: 0,
		paid: 0,
		unpaid: 0,
		total: 0,
	}
	for (const row of filteredRows.value) {
		totals.reg += Number(row.reg || 0)
		totals.ot += Number(row.ot || 0)
		totals.dt += Number(row.dt || 0)
		totals.pto += Number(row.pto || 0)
		totals.paid += Number(row.paid || 0)
		totals.unpaid += Number(row.unpaid || 0)
		totals.total += Number(row.total || row.working_hours || 0)
	}
	return totals
})

const visibleRows = computed(() => {
	if (props.mode === "day") {
		return [...filteredRows.value].sort((a, b) => {
			const dateCmp = String(a.attendance_date || "").localeCompare(String(b.attendance_date || ""))
			if (dateCmp) return dateCmp
			return String(a.in_time || "").localeCompare(String(b.in_time || ""))
		})
	}

	const byDate = {}
	for (const row of filteredRows.value) {
		const key = isoDate(row.attendance_date)
		if (!key) continue
		if (!byDate[key]) byDate[key] = []
		byDate[key].push(row)
	}

	const dates = datesInRange(props.fromDate, props.toDate)
	const result = []
	for (const date of dates) {
		const dayRows = byDate[date] || []
		if (!dayRows.length) {
			result.push({ attendance_date: date, showDay: true, empty: true })
			continue
		}
		dayRows
			.slice()
			.sort((a, b) => String(a.in_time || "").localeCompare(String(b.in_time || "")))
			.forEach((row, index) => {
				result.push({ ...row, showDay: index === 0, empty: false })
			})
	}
	return result
})

function isoDate(value) {
	if (!value) return ""
	const parsed = dayjs(value)
	return parsed.isValid() ? parsed.format("YYYY-MM-DD") : String(value).slice(0, 10)
}

function datesInRange(from, to) {
	const start = dayjs(from)
	const end = dayjs(to)
	if (!start.isValid() || !end.isValid() || end.isBefore(start, "day")) return []
	const dates = []
	let cursor = start.startOf("day")
	const last = end.startOf("day")
	while (!cursor.isAfter(last, "day")) {
		dates.push(cursor.format("YYYY-MM-DD"))
		cursor = cursor.add(1, "day")
	}
	return dates
}

function dayLabel(value) {
	const parsed = dayjs(value)
	return parsed.isValid() ? parsed.format("ddd") : ""
}

function dateLabel(value, mode) {
	const parsed = dayjs(value)
	if (!parsed.isValid()) return value || ""
	return mode === "list" ? parsed.format("MM/DD") : `${parsed.format("MM-DD")}, ${parsed.format("ddd")}`
}

function entryHours(row) {
	if (!row || row.empty) return 0
	return Number(row.total || row.working_hours || 0)
}

function hoursCell(value) {
	return formatHours(value, false)
}

function missingOut(row) {
	return Boolean(row?.in_time && !row?.out_time && !row?.empty)
}

function clockIn(row) {
	return formatClock(row?.in_time)
}

function clockOut(row) {
	if (missingOut(row)) return "na"
	return formatClock(row?.out_time)
}

function rowKey(row, index) {
	return [row.name, row.kind, row.in_time, row.out_time, row.attendance_date, index].join(":")
}
</script>
