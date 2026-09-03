<template>
	<BaseLayout :pageTitle="__('Requests')">
		<template #body>
			<div class="flex flex-col mt-7 mb-7 p-4 gap-7">
				<HRRequestSummary />

				<div class="flex flex-col gap-3 w-full">
					<router-link
						:to="{ name: 'HRRequestFormView', query: { request_type: 'Job Letter' } }"
						v-slot="{ navigate }"
					>
						<Button @click="navigate" variant="solid" class="w-full py-5 text-base">
							{{ __("Request a Job Letter") }}
						</Button>
					</router-link>
					<router-link :to="{ name: 'HRRequestFormView' }" v-slot="{ navigate }">
						<Button @click="navigate" variant="subtle" class="w-full py-5 text-base">
							{{ __("New Request") }}
						</Button>
					</router-link>
				</div>

				<div>
					<div class="text-lg text-gray-800 font-bold">{{ __("Recent Job Letters") }}</div>
					<RequestList
						:component="markRaw(HRRequestItem)"
						:items="myJobLetters.data"
						:emptyStateMessage="__('You have no job letter requests')"
					/>
				</div>

				<div>
					<div class="text-lg text-gray-800 font-bold">{{ __("Recent Requests") }}</div>
					<RequestList
						:component="markRaw(HRRequestItem)"
						:items="myHRRequests.data"
						:addListButton="true"
						listButtonRoute="HRRequestListView"
					/>
				</div>

				<div>
					<div class="text-lg text-gray-800 font-bold">{{ __("Other Requests") }}</div>
					<RequestPanel />
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { markRaw } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import HRRequestSummary from "@/components/HRRequestSummary.vue"
import RequestList from "@/components/RequestList.vue"
import RequestPanel from "@/components/RequestPanel.vue"
import HRRequestItem from "@/components/HRRequestItem.vue"

import { myJobLetters, myHRRequests } from "@/data/hr_requests"
</script>
