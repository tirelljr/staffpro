<template>
	<div class="flex flex-col w-full gap-5" v-if="summary.data">
		<div class="text-lg text-gray-800 font-bold">{{ __("Request Summary") }}</div>
		<div class="flex flex-col gap-4 bg-white py-3 px-3.5 rounded-lg border-none">
			<div class="flex flex-row justify-between">
				<div class="flex flex-col gap-1">
					<div class="flex flex-row gap-1 items-center">
						<span class="text-gray-600 text-sm font-medium leading-5">
							{{ __("Open") }}
						</span>
						<FeatherIcon name="alert-circle" class="text-yellow-500 h-3 w-3" />
					</div>
					<span class="text-gray-800 text-base font-semibold leading-6">
						{{ summary.data.open || 0 }}
					</span>
				</div>
				<div class="flex flex-col gap-1">
					<div class="flex flex-row gap-1 items-center">
						<span class="text-gray-600 text-sm font-medium leading-5">
							{{ __("In Progress") }}
						</span>
						<FeatherIcon name="clock" class="text-blue-500 h-3 w-3" />
					</div>
					<span class="text-gray-800 text-base font-semibold leading-6">
						{{ summary.data.in_progress || 0 }}
					</span>
				</div>
				<div class="flex flex-col gap-1">
					<div class="flex flex-row gap-1 items-center">
						<span class="text-gray-600 text-sm font-medium leading-5">
							{{ __("Resolved") }}
						</span>
						<FeatherIcon name="check-circle" class="text-green-500 h-3 w-3" />
					</div>
					<span class="text-gray-800 text-base font-semibold leading-6">
						{{ summary.data.resolved || 0 }}
					</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui"
import { hrRequestSummary as summary } from "@/data/hr_requests"
</script>
