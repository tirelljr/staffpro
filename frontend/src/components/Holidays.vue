<template>
	<div class="flex flex-col gap-5 w-full">
		<div class="flex flex-row justify-between items-center">
			<div class="text-lg text-gray-800 font-bold">{{ __("Upcoming Holidays") }}</div>
			<div
				v-if="holidays?.data?.length"
				id="open-holiday-list"
				class="text-sm text-gray-800 font-semibold cursor-pointer underline underline-offset-2"
			>
				{{ __("View All") }}
			</div>
		</div>

		<div class="flex flex-col bg-white rounded" v-if="upcomingHolidays?.length">
			<div
				class="flex flex-col gap-3 p-4 border-b"
				v-for="holiday in upcomingHolidays"
				:key="holiday.holiday_date"
			>
				<div class="flex flex-row items-center justify-between gap-3">
					<div class="flex flex-row items-center gap-3 grow min-w-0">
						<FeatherIcon name="calendar" class="h-5 w-5 text-gray-500 shrink-0" />
						<div class="text-base font-normal text-gray-800">
							{{ __(holiday.description) }}
						</div>
					</div>
					<div class="text-base font-bold text-gray-800 shrink-0">
						{{ holiday.formatted_holiday_date }}
					</div>
				</div>
				<div class="pl-8">
					<Switch
						v-if="holiday.can_toggle"
						size="sm"
						:label="holiday.will_work ? __('Working') : __('Not Working')"
						:model-value="!!holiday.will_work"
						:disabled="!!holiday.saving"
						@update:model-value="(value) => setWorking(holiday, value)"
					/>
					<div v-else-if="!holiday.is_work_day" class="text-sm text-gray-500">
						{{ __("Weekly off") }}
					</div>
				</div>
			</div>
		</div>

		<EmptyState :message="__('You have no upcoming holidays')" v-else-if="!holidays.loading" />
	</div>

	<ion-modal
		ref="modal"
		v-if="holidays?.data?.length"
		trigger="open-holiday-list"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<div class="bg-white w-full flex flex-col items-center justify-center pb-5">
			<div class="w-full pt-8 pb-5 border-b text-center">
				<span class="text-gray-900 font-bold text-lg">{{ __("Holiday List") }}</span>
			</div>
			<div class="w-full flex flex-col items-center justify-center gap-5 p-4">
				<div
					v-for="holiday in holidays.data"
					:key="holiday.holiday_date"
					class="flex flex-col gap-2 w-full"
				>
					<div class="flex flex-row items-center justify-between w-full gap-3">
						<div class="flex flex-row items-center gap-3 grow min-w-0">
							<FeatherIcon name="calendar" class="h-5 w-5 text-gray-500 shrink-0" />
							<div class="text-base font-normal text-gray-800">
								{{ __(holiday.description) }}
							</div>
						</div>
						<div
							:class="[
								'text-base font-bold shrink-0',
								holiday.is_upcoming ? 'text-gray-800' : 'text-gray-500',
							]"
						>
							{{ holiday.formatted_holiday_date }}
						</div>
					</div>
					<div class="pl-8" v-if="holiday.can_toggle || !holiday.is_work_day">
						<Switch
							v-if="holiday.can_toggle"
							size="sm"
							:label="holiday.will_work ? __('Working') : __('Not Working')"
							:model-value="!!holiday.will_work"
							:disabled="!!holiday.saving"
							@update:model-value="(value) => setWorking(holiday, value)"
						/>
						<div v-else class="text-sm text-gray-500">
							{{ __("Weekly off") }}
						</div>
					</div>
				</div>
			</div>
		</div>
	</ion-modal>
</template>

<script setup>
import { inject, computed } from "vue"
import { IonModal } from "@ionic/vue"
import { FeatherIcon, Switch, createResource } from "frappe-ui"

const employee = inject("$employee")
const dayjs = inject("$dayjs")
const __ = inject("$translate")

const holidays = createResource({
	url: "hrms.api.get_holidays_for_employee",
	params: {
		employee: employee.data.name,
	},
	auto: true,
	transform: (data) => {
		return (data || []).map((holiday) => {
			const holidayDate = dayjs(holiday.holiday_date)
			holiday.is_upcoming = !holidayDate.isBefore(dayjs(), "day")
			holiday.formatted_holiday_date = holidayDate.format("ddd, D MMM YYYY")
			holiday.saving = false
			return holiday
		})
	},
})

const upcomingHolidays = computed(() => {
	const filteredHolidays = holidays.data?.filter((holiday) => holiday.is_upcoming)
	return filteredHolidays?.slice(0, 5)
})

const election = createResource({
	url: "hrms.api.set_holiday_work_election",
	auto: false,
})

async function setWorking(holiday, willWork) {
	if (holiday.saving) {
		return
	}
	const previous = holiday.will_work
	holiday.will_work = willWork
	holiday.saving = true
	try {
		await election.submit({
			employee: employee.data.name,
			holiday_date: holiday.holiday_date,
			will_work: willWork ? 1 : 0,
		})
	} catch {
		holiday.will_work = previous
	} finally {
		holiday.saving = false
	}
}
</script>
