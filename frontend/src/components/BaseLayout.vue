<template>
	<ion-page>
		<ion-content class="ion-no-padding">
			<div class="flex flex-col h-full w-full">
				<h1 v-if="pageTitle" class="sr-only">{{ pageTitle }}</h1>
				<slot name="body"></slot>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonContent, IonPage } from "@ionic/vue"

defineProps({
	pageTitle: {
		type: String,
		required: false,
		default: "",
	},
})
</script>
