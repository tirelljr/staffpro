<template>
	<div
		v-if="visible"
		class="fixed inset-0 z-[80] flex items-end justify-center bg-black/40 p-4 sm:items-center"
	>
		<div class="w-full max-w-md rounded-lg bg-white p-5 shadow-lg">
			<p class="text-xs font-semibold uppercase tracking-widest text-gray-500">{{ __("Belize") }}</p>
			<h2 class="mt-1 text-xl font-semibold text-gray-900">{{ __("Fill out your TD4") }}</h2>
			<p class="mt-2 text-sm text-gray-600">
				{{ __("Your TD4 Supplementary tax form still needs to be completed and signed.") }}
			</p>
			<p v-if="locked" class="mt-2 text-sm text-gray-800">
				{{ __("This stays open until the form is filled out.") }}
			</p>
			<p v-else class="mt-2 text-sm text-gray-500">
				{{ __("You can close this {0} more time(s).", [closesLeft]) }}
			</p>
			<div class="mt-4 flex flex-col gap-2">
				<Button variant="solid" class="w-full" @click="fillOut">{{ __("Fill out form") }}</Button>
				<Button v-if="!locked" variant="outline" class="w-full" @click="closePrompt">{{ __("Close") }}</Button>
				<Button variant="ghost" class="w-full" @click="signOut">{{ __("Sign out") }}</Button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { createResource } from "frappe-ui"
import { computed, inject, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

const __ = inject("$translate")
const session = inject("$session")
const route = useRoute()
const router = useRouter()

const DISMISS_LIMIT = 3
const AUTH_ROUTES = new Set(["Login", "ForgotPassword", "InvalidEmployee"])

const prompt = ref(null)
const visible = ref(false)
const closedThisVisit = ref(false)
const dismissedOnProfile = ref(false)
let requestId = 0

const dismissCount = computed(() => Number(prompt.value?.dismiss_count || 0))
const locked = computed(() => dismissCount.value >= DISMISS_LIMIT)
const closesLeft = computed(() => Math.max(DISMISS_LIMIT - dismissCount.value, 0))

const gate = createResource({
	url: "hrms.hr.doctype.td4_form.td4_form.ensure_initial_td4",
})

const dismiss = createResource({
	url: "hrms.hr.doctype.td4_form.td4_form.dismiss_td4_prompt",
})

watch(
	() => [session?.isLoggedIn, route.name],
	() => {
		if (route.name !== "Profile") dismissedOnProfile.value = false
		syncPrompt()
	},
	{ immediate: true }
)

async function syncPrompt() {
	if (!session?.isLoggedIn || AUTH_ROUTES.has(route.name)) {
		visible.value = false
		return
	}
	const current = ++requestId
	try {
		const next = await gate.submit()
		if (current !== requestId) return
		prompt.value = next
	} catch (error) {
		if (current !== requestId) return
		visible.value = false
		return
	}
	if (!prompt.value?.name || route.name === "TD4FormDetailView") {
		visible.value = false
		return
	}
	if (locked.value) {
		visible.value = true
		return
	}
	if (route.name === "Profile") {
		visible.value = !dismissedOnProfile.value
		return
	}
	visible.value = !closedThisVisit.value
}

async function closePrompt() {
	if (!prompt.value?.name || locked.value) return
	try {
		const next = await dismiss.submit({ name: prompt.value.name })
		prompt.value = { ...prompt.value, ...next }
	} catch (error) {
		return
	}
	closedThisVisit.value = true
	if (route.name === "Profile") dismissedOnProfile.value = true
	visible.value = false
}

function fillOut() {
	if (!prompt.value?.name) return
	visible.value = false
	router.push({ name: "TD4FormDetailView", params: { id: prompt.value.name } })
}

function signOut() {
	session.logout.submit()
}
</script>
