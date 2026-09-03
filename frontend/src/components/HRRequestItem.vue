<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<RequestIcon class="h-5 w-5 text-gray-500" />
			<div class="flex flex-col items-start gap-1.5">
				<div class="text-base font-normal text-gray-800">
					{{ __(props.doc.request_type) }}
				</div>
				<div class="text-xs font-normal text-gray-500">
					{{ props.doc.subject }}
				</div>
			</div>
		</template>
		<template #right>
			<Button
				v-if="showDownload"
				variant="ghost"
				class="!px-2"
				@click.stop="downloadLetter"
			>
				<FeatherIcon name="download" class="h-4 w-4 text-gray-600" />
			</Button>
			<Badge variant="outline" :theme="colorMap[status] || 'gray'" :label="__(status)" size="md" />
			<FeatherIcon name="chevron-right" class="h-5 w-5 text-gray-500" />
		</template>
	</ListItem>
</template>

<script setup>
import { computed } from "vue"
import { Badge, Button, FeatherIcon } from "frappe-ui"

import ListItem from "@/components/ListItem.vue"
import RequestIcon from "@/components/icons/RequestIcon.vue"
import { canDownloadJobLetter } from "@/data/hr_requests"
import { useDownloadPDF } from "@/utils/commonUtils"

const { downloadPDF } = useDownloadPDF()

const props = defineProps({
	doc: {
		type: Object,
	},
	isTeamRequest: {
		type: Boolean,
		default: false,
	},
	workflowStateField: {
		type: String,
		required: false,
	},
})

const status = computed(() => {
	return props.workflowStateField ? props.doc[props.workflowStateField] : props.doc.status
})

const showDownload = computed(() => canDownloadJobLetter(props.doc))

function downloadLetter() {
	downloadPDF({
		doctype: "HR Request",
		docname: props.doc.name,
		filename: props.doc.subject || props.doc.name,
		print_format: "Job Letter",
	})
}

const colorMap = {
	Open: "orange",
	"In Progress": "blue",
	"Waiting on Employee": "yellow",
	Resolved: "green",
	Rejected: "red",
	Cancelled: "gray",
}
</script>
