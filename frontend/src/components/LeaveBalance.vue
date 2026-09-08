<template>
	<div class="flex flex-col w-full">
		<div class="flex flex-row justify-between items-center px-4">
			<div class="text-lg text-gray-800 font-bold">{{ __("Leave Balance") }} </div>
			<router-link
				:to="{ name: 'LeaveApplicationListView' }"
				v-slot="{ navigate }"
				v-if="leaveBalance.data"
			>
				<div
					@click="navigate"
					class="text-sm text-gray-800 font-semibold cursor-pointer underline underline-offset-2"
				>
					{{ __("View Leave History") }}
				</div>
			</router-link>
		</div>

		<!-- Leave Balance Dashboard -->
		<div
			class="flex flex-row gap-4 overflow-x-auto py-2 mt-3"
			v-if="leaveBalance.data"
		>
			<div
				v-for="(allocation, leave_type, index) in leaveBalance.data"
				:key="leave_type"
				class="flex flex-col bg-white border-none rounded-[20px] shadow-[0_8px_28px_rgba(16,24,40,0.06)] gap-3 p-5 items-center first:ml-4 min-w-[148px]"
			>
				<SemicircleChart
					:percentage="allocation.balance_percentage"
					:colorClass="getChartColor(index)"
				/>
				<div class="text-gray-900 font-bold text-base tracking-tight">
					{{ `${allocation.balance_leaves} of ${allocation.allocated_leaves}` }}
				</div>
				<div class="text-gray-400 font-medium text-sm w-28 leading-4 text-center">
					{{ __("{0} balance", [__(leave_type, null, "Leave Type")]) }}
				</div>
				<div class="w-full h-1.5 rounded-full bg-[#eef1f6] overflow-hidden">
					<div
						class="h-full rounded-full"
						:style="{
							width: `${Math.max(0, Math.min(100, allocation.balance_percentage || 0))}%`,
							background: getChartHex(index),
						}"
					></div>
				</div>
			</div>
		</div>

		<EmptyState :message="__('You have no leaves allocated')" v-else />
	</div>
</template>

<script setup>
import SemicircleChart from "@/components/SemicircleChart.vue"
import { leaveBalance } from "@/data/leaves"
import { inject } from "vue"

const __ = inject("$translate")
const CHART_HEX = ["#7c5cfc", "#3ddc97", "#ff6b8a", "#ff9f43"]
const getChartColor = (index) => {
	const chartColors = ["text-[#918ef5]", "text-[#3ddc97]", "text-[#fb7185]"]
	return chartColors[index % chartColors.length]
}
const getChartHex = (index) => CHART_HEX[index % CHART_HEX.length]
</script>
