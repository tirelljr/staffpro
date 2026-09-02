<template>
	<img :src="logoUrl" alt="Staff Pro BPO" />
</template>

<script setup lang="ts">
import { STAFF_PRO_LOGO_URL } from "../utils/branding";

const logoUrl = STAFF_PRO_LOGO_URL;
</script>
