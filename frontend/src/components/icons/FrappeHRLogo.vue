<template>
	<img :src="logoUrl" alt="Staff Pro BPO" />
</template>

<script setup>
import { STAFF_PRO_LOGO_URL } from "@/utils/branding"

const logoUrl = STAFF_PRO_LOGO_URL
</script>
