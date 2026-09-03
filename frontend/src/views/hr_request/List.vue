<template>
	<ion-page>
		<ListView
			doctype="HR Request"
			:pageTitle="__('Requests')"
			:fields="HR_REQUEST_LIST_FIELDS"
			:filterConfig="FILTER_CONFIG"
		/>
	</ion-page>
</template>

<script setup>
import { IonPage } from "@ionic/vue"
import ListView from "@/components/ListView.vue"
import { inject } from "vue"

const __ = inject("$translate")
const HR_REQUEST_LIST_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"request_type",
	"subject",
	"status",
	"priority",
	"creation",
]
const FILTER_CONFIG = [
	{
		fieldname: "status",
		fieldtype: "Select",
		label: __("Status"),
		options: ["Open", "In Progress", "Waiting on Employee", "Resolved", "Rejected", "Cancelled"],
	},
	{
		fieldname: "request_type",
		fieldtype: "Link",
		label: __("Request Type"),
		options: "HR Request Type",
	},
	{
		fieldname: "priority",
		fieldtype: "Select",
		label: __("Priority"),
		options: ["Low", "Medium", "High"],
	},
]
</script>
