<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex flex-col h-full w-full">
				<header
					class="flex flex-row bg-white shadow-sm py-4 px-3 items-center justify-between border-b sticky top-0 z-10"
				>
					<div class="flex flex-row items-center">
						<Button variant="ghost" class="!pl-0 hover:bg-white" @click="goBack">
							<FeatherIcon name="chevron-left" class="h-5 w-5" />
						</Button>
						<h2 class="text-xl font-semibold text-gray-900">
							{{ active ? active.category_name : __("My Documents") }}
						</h2>
					</div>
				</header>

				<div v-if="filesystem.loading && !filesystem.data" class="p-4 text-sm text-gray-500">
					{{ __("Loading...") }}
				</div>

				<div v-else-if="filesystem.error" class="p-4 text-sm text-red-600">
					{{ __("Your document folder could not be opened.") }}
				</div>

				<div v-else-if="!active" class="flex flex-col gap-3 p-4">
					<p class="text-sm text-gray-500">
						{{
							__(
								"Upload social security, tax forms, job letters, bank declarations, IDs, writeups, and other documents."
							)
						}}
					</p>
					<button
						v-for="category in categories"
						:key="category.name"
						type="button"
						class="flex flex-row items-center justify-between bg-white rounded p-4 text-left border"
						@click="selected = category.name"
					>
						<div class="flex flex-row items-center gap-3">
							<FeatherIcon name="folder" class="h-5 w-5 text-gray-500" />
							<div>
								<div class="text-base font-medium text-gray-800">
									{{ category.category_name }}
								</div>
								<div v-if="category.description" class="text-sm text-gray-500">
									{{ category.description }}
								</div>
							</div>
						</div>
						<div class="text-sm text-gray-500 shrink-0 pl-3">
							{{ fileCountLabel(category.file_count) }}
						</div>
					</button>
				</div>

				<div v-else class="p-4">
					<p v-if="active.description" class="text-sm text-gray-500">
						{{ active.description }}
					</p>
					<FileUploaderView
						:model-value="files"
						:allow-print="selected === 'Job Letter'"
						@handle-file-select="onSelect"
						@handle-file-delete="onDelete"
						@request-print="onPrint"
					/>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { Button, FeatherIcon, createResource, toast } from "frappe-ui"
import { computed, inject, onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import FileUploaderView from "@/components/FileUploaderView.vue"
import { FileAttachment } from "@/composables"

const __ = inject("$translate")
const employee = inject("$employee")
const router = useRouter()
const selected = ref("")

const filesystem = createResource({
	url: "hrms.hr.agent_filesystem.get_my_filesystem",
})

onMounted(() => {
	filesystem.reload()
})

const categories = computed(() => filesystem.data?.categories || [])
const active = computed(
	() => categories.value.find((category) => category.name === selected.value) || null
)
const files = computed(() =>
	(active.value?.files || []).map((file) => ({
		...file,
		file_url: file.file_url || file.file,
	}))
)

function fileCountLabel(count) {
	const total = Number(count) || 0
	return total === 1 ? `${total} ${__("file")}` : `${total} ${__("files")}`
}

function goBack() {
	if (selected.value) {
		selected.value = ""
		return
	}
	router.back()
}

async function onSelect(event) {
	const picked = Array.from(event.target.files || [])
	event.target.value = ""
	const owner = employee?.data?.name || filesystem.data?.employee
	for (const file of picked) {
		try {
			const attachment = new FileAttachment(file, {
				url: "hrms.hr.agent_filesystem.upload_file",
				fields: {
					employee: owner,
					category: selected.value,
				},
			})
			await attachment.upload()
		} catch (error) {
			// FileAttachment already shows the upload error.
		}
	}
	await filesystem.reload()
}

async function onPrint(file) {
	if (!file?.hr_request) return
	try {
		await createResource({
			url: "hrms.hr.job_letter.request_office_print",
		}).submit({ name: file.hr_request })
		toast({
			title: __("Print requested"),
			text: __("Staff can print this letter from Employee Requests."),
		})
	} catch (error) {
		toast({
			title: __("Error"),
			text: error?.messages?.[0] || __("The print request could not be sent."),
		})
	}
}

async function onDelete(file) {
	if (!file?.can_delete) return
	try {
		await createResource({
			url: "hrms.hr.agent_filesystem.delete_file",
		}).submit({ name: file.name })
		await filesystem.reload()
	} catch (error) {
		toast({
			title: __("Error"),
			text: error?.messages?.[0] || __("Could not delete the file."),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
	}
}
</script>
