<template>
	<ion-app :class="{ 'app-has-topbar': showTopBar }">
		<TopBar v-if="showTopBar" />
		<ion-router-outlet id="main-content" />
		<Toasts />

		<InstallPrompt />
	</ion-app>
</template>

<script setup>
import { computed, inject, onMounted } from "vue"
import { useRoute } from "vue-router"
import { IonApp, IonRouterOutlet } from "@ionic/vue"

import { Toasts } from "frappe-ui"

import TopBar from "@/components/TopBar.vue"
import InstallPrompt from "@/components/InstallPrompt.vue"
import { showNotification } from "@/utils/pushNotifications"

const route = useRoute()
const session = inject("$session")

const AUTH_HIDDEN_ROUTES = ["Login", "ForgotPassword", "InvalidEmployee"]

const showTopBar = computed(() => {
	return Boolean(session?.isLoggedIn) && !AUTH_HIDDEN_ROUTES.includes(route.name)
})

onMounted(() => {
	window?.frappePushNotification?.onMessage((payload) => {
		showNotification(payload)
	})
})
</script>
