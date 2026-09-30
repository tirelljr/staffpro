<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<div class="flex flex-col h-full w-full">
				<div class="w-full h-full bg-white sm:w-96 flex flex-col">
					<header
						class="flex flex-row bg-white shadow-sm py-4 px-3 items-center sticky top-0 z-[1000]"
					>
						<Button
							variant="ghost"
							class="!pl-0 hover:bg-white"
							@click="goBack"
						>
							<FeatherIcon name="chevron-left" class="h-5 w-5" />
						</Button>
						<h2 class="text-xl font-semibold text-gray-900">{{ __("Reset Password") }}</h2>
					</header>

					<div class="bg-white grow overflow-y-auto">
						<form class="flex flex-col space-y-4 p-4" @submit.prevent="submitPassword">
							<p class="text-sm leading-5 text-gray-600">
								{{ __("Enter your username and a new password. It updates your Staff Pro login immediately.") }}
							</p>
							<Input
								:label="__('Username') + ' *'"
								type="text"
								placeholder="TArzu"
								v-model="username"
								autocomplete="username"
								required
							/>
							<Input
								:label="__('New Password') + ' *'"
								type="password"
								v-model="newPassword"
								autocomplete="new-password"
								required
							/>
							<Input
								:label="__('Confirm Password') + ' *'"
								type="password"
								v-model="confirmPassword"
								autocomplete="new-password"
								required
							/>
						</form>
					</div>

					<div
						class="px-4 pt-4 pb-4 standalone:pb-safe-bottom sm:w-96 bg-white sticky bottom-0 w-full drop-shadow-xl z-40 border-t rounded-t-lg"
					>
						<ErrorMessage class="mb-2" :message="errorMessage" />
						<Button
							class="w-full rounded py-5 text-base disabled:bg-gray-700 disabled:text-white"
							:loading="setPasswordResource.loading"
							variant="solid"
							@click="submitPassword"
						>
							{{ __("Update Password") }}
						</Button>
					</div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { useRoute, useRouter } from "vue-router"
import { FeatherIcon, toast, createResource, Input, ErrorMessage, Button } from "frappe-ui"

import { inject, ref } from "vue"

const __ = inject("$translate")
const route = useRoute()
const router = useRouter()

const username = ref(
	Array.isArray(route.query.username)
		? route.query.username[0]
		: route.query.username || route.query.email || "",
)
const newPassword = ref("")
const confirmPassword = ref("")
const errorMessage = ref("")

const setPasswordResource = createResource({
	url: "hrms.api.kiosk.set_password",
	method: "POST",
	onSuccess() {
		toast({
			title: __("Success"),
			text: __("Your password has been updated."),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
		errorMessage.value = ""
		router.replace({ name: "Login" })
	},
	onError(error) {
		errorMessage.value = error.messages?.[0] || __("Failed to update password")
	},
})

function goBack() {
	if (window.history.state?.back) {
		router.back()
		return
	}

	router.replace({ name: "Login" })
}

function submitPassword() {
	const usernameValue = (username.value || "").trim()
	const passwordValue = newPassword.value || ""

	if (!usernameValue) {
		errorMessage.value = __("Please enter your username")
		return
	}
	if (passwordValue.length < 8) {
		errorMessage.value = __("Password must be at least 8 characters.")
		return
	}
	if (passwordValue !== confirmPassword.value) {
		errorMessage.value = __("Passwords do not match.")
		return
	}

	errorMessage.value = ""
	setPasswordResource.submit({
		username: usernameValue,
		new_password: passwordValue,
	})
}
</script>
