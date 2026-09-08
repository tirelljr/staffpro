<template>
	<svg
		viewBox="0 0 120 78"
		class="w-[132px] h-[86px] overflow-visible"
		aria-hidden="true"
	>
		<path
			d="M18 58 A42 42 0 0 1 102 58"
			fill="none"
			stroke="#eef1f6"
			stroke-width="10"
			stroke-linecap="round"
		/>
		<path
			d="M18 58 A42 42 0 0 1 102 58"
			fill="none"
			:stroke="strokeColor"
			stroke-width="10"
			stroke-linecap="round"
			:stroke-dasharray="dashArray"
		/>
		<circle
			:cx="handle.x"
			:cy="handle.y"
			r="6"
			fill="#fff"
			:stroke="strokeColor"
			stroke-width="3"
		/>
	</svg>
</template>

<script setup>
import { computed } from "vue"

const props = defineProps({
	percentage: {
		type: Number,
		default: 0,
	},
	color: {
		type: String,
		default: "#3ddc97",
	},
	colorClass: {
		type: String,
		default: "",
	},
})

const palette = {
	"text-[#fb7185]": "#ff6b8a",
	"text-[#f472b6]": "#ff6b8a",
	"text-[#918ef5]": "#7c5cfc",
	"text-[#3ddc97]": "#3ddc97",
	"text-orange-500": "#ff9f43",
}

const strokeColor = computed(() => palette[props.colorClass] || props.color)

const clamped = computed(() => {
	if (isNaN(props.percentage)) return 0
	return Math.max(0, Math.min(100, props.percentage))
})

const radius = 42
const halfCircumference = Math.PI * radius

const dashArray = computed(() => {
	const dash = (clamped.value / 100) * halfCircumference
	return `${dash} ${halfCircumference}`
})

const handle = computed(() => {
	const angle = Math.PI - (clamped.value / 100) * Math.PI
	return {
		x: 60 + radius * Math.cos(angle),
		y: 58 - radius * Math.sin(angle),
	}
})
</script>
