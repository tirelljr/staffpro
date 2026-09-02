<template>
	<div
		class="sp-empty-list"
		:class="props.isTableField ? 'sp-empty-list--table' : ''"
	>
		<div v-if="!props.isTableField" class="sp-empty-illus" aria-hidden="true">
			<div class="sp-empty-illus__rings"><i></i><i></i><i></i></div>
			<span class="sp-empty-illus__face sp-empty-illus__face--tl">
				<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="20" fill="#e8a598"/><path d="M6.5 40c2.2-11.5 7.2-15.5 13.5-15.5S31.3 28.5 33.5 40" fill="#e8a598"/><ellipse cx="20" cy="17.2" rx="7.1" ry="8" fill="#e8b896"/><path d="M10.2 19c.5-9.2 19.1-9.2 19.6 0-.6-6.8-4.6-11.8-9.8-11.8S10.8 12.2 10.2 19z" fill="#2c1a12"/></svg>
			</span>
			<span class="sp-empty-illus__face sp-empty-illus__face--tr">
				<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="20" fill="#1f3a5f"/><path d="M6.5 40c2.2-11.5 7.2-15.5 13.5-15.5S31.3 28.5 33.5 40" fill="#1f3a5f"/><ellipse cx="20" cy="17.2" rx="7.1" ry="8" fill="#c68642"/><path d="M12 17.8c.2-7.4 15.8-7.4 16 0-.4-5.2-15.6-5.2-16 0z" fill="#1a120c"/></svg>
			</span>
			<span class="sp-empty-illus__face sp-empty-illus__face--l is-fade">
				<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="20" fill="#90ba93"/><path d="M6.5 40c2.2-11.5 7.2-15.5 13.5-15.5S31.3 28.5 33.5 40" fill="#90ba93"/><ellipse cx="20" cy="17.2" rx="7.1" ry="8" fill="#f1c27d"/><path d="M11.4 18.4c.4-8 16.8-8 17.2 0-.6-5.6-16.6-5.6-17.2 0z" fill="#4a2c14"/><circle cx="20" cy="6.4" r="3.1" fill="#4a2c14"/></svg>
			</span>
			<span class="sp-empty-illus__face sp-empty-illus__face--r">
				<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="20" fill="#11a5dd"/><path d="M6.5 40c2.2-11.5 7.2-15.5 13.5-15.5S31.3 28.5 33.5 40" fill="#11a5dd"/><ellipse cx="20" cy="17.2" rx="7.1" ry="8" fill="#ffdbac"/><path d="M12.4 17.2c0-7.2 15.2-7.2 15.2 0C27 12.2 13 12.2 12.4 17.2z" fill="#3b2314"/></svg>
			</span>
			<span class="sp-empty-illus__face sp-empty-illus__face--bl is-fade">
				<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="20" fill="#d9a5b3"/><path d="M6.5 40c2.2-11.5 7.2-15.5 13.5-15.5S31.3 28.5 33.5 40" fill="#d9a5b3"/><ellipse cx="20" cy="17.2" rx="7.1" ry="8" fill="#8d5524"/><path d="M9.6 20c.2-10.4 20.6-10.4 20.8 0-1.2-8-19.6-8-20.8 0z" fill="#1b0f0a"/></svg>
			</span>
			<span class="sp-empty-illus__face sp-empty-illus__face--br">
				<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="20" fill="#a7c8cc"/><path d="M6.5 40c2.2-11.5 7.2-15.5 13.5-15.5S31.3 28.5 33.5 40" fill="#a7c8cc"/><ellipse cx="20" cy="17.2" rx="7.1" ry="8" fill="#e0ac69"/><path d="M12.2 17.6c.3-7 15.3-7 15.6 0-.5-4.8-15.1-4.8-15.6 0z" fill="#2a1b10"/><g fill="none" stroke="#2a2a2a" stroke-width="1.1"><circle cx="16.6" cy="18.2" r="2.3"/><circle cx="23.4" cy="18.2" r="2.3"/><path d="M18.9 18.2h2.2"/></g></svg>
			</span>
			<span class="sp-empty-illus__face sp-empty-illus__face--tc is-fade">
				<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="20" fill="#c4b5a5"/><path d="M6.5 40c2.2-11.5 7.2-15.5 13.5-15.5S31.3 28.5 33.5 40" fill="#c4b5a5"/><ellipse cx="20" cy="17.2" rx="7.1" ry="8" fill="#f3d1b3"/><path d="M11.8 18c.5-8.2 15.9-8.2 16.4 0-.6-6-15.8-6-16.4 0z" fill="#5c4033"/></svg>
			</span>
			<div class="sp-empty-illus__stack">
				<div class="sp-empty-illus__card"><i></i><span><b></b><b></b></span></div>
				<div class="sp-empty-illus__card is-accent"><i></i><span><b></b><b></b></span></div>
				<div class="sp-empty-illus__card"><i></i><span><b></b><b></b></span></div>
			</div>
		</div>
		<h2 v-if="!props.isTableField" class="sp-empty-list__title">{{ __(heading) }}</h2>
		<p class="sp-empty-list__text">{{ __(props.message) }}</p>
	</div>
</template>

<script setup>
import { computed, inject } from "vue"

const __ = inject("$translate") || ((text) => text)

const props = defineProps({
	message: { type: String },
	title: { type: String, default: "" },
	isTableField: { type: Boolean, default: false },
})

const heading = computed(() => props.title || "Nothing here yet")
</script>

<style scoped>
.sp-empty-list {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	width: 100%;
	margin: 8px auto;
	padding: 28px 16px;
	text-align: center;
}

.sp-empty-list--table {
	margin-top: 1.25rem;
	padding: 1.25rem;
	border: 2px dashed #d1d5db;
	border-radius: 0.5rem;
}

.sp-empty-illus {
	position: relative;
	width: 260px;
	height: 200px;
	margin: 0 auto 22px;
}

.sp-empty-illus__rings {
	position: absolute;
	inset: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	pointer-events: none;
}

.sp-empty-illus__rings i {
	position: absolute;
	border: 1px solid rgba(17, 17, 17, 0.07);
	border-radius: 50%;
}

.sp-empty-illus__rings i:nth-child(1) {
	width: 118px;
	height: 118px;
}

.sp-empty-illus__rings i:nth-child(2) {
	width: 168px;
	height: 168px;
}

.sp-empty-illus__rings i:nth-child(3) {
	width: 220px;
	height: 220px;
}

.sp-empty-illus__stack {
	position: absolute;
	left: 50%;
	top: 50%;
	z-index: 2;
	display: flex;
	flex-direction: column;
	gap: 7px;
	width: 128px;
	transform: translate(-50%, -50%);
}

.sp-empty-illus__card {
	display: flex;
	align-items: center;
	gap: 8px;
	height: 38px;
	padding: 0 10px;
	border: 1.5px solid #e5e7eb;
	border-radius: 12px;
	background: #fff;
	box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
}

.sp-empty-illus__card i {
	flex-shrink: 0;
	width: 16px;
	height: 16px;
	border-radius: 50%;
	background: #e5e7eb;
}

.sp-empty-illus__card span {
	display: flex;
	flex: 1;
	flex-direction: column;
	gap: 4px;
}

.sp-empty-illus__card b {
	display: block;
	height: 4px;
	border-radius: 99px;
	background: #e5e7eb;
}

.sp-empty-illus__card b:first-child {
	width: 72%;
}

.sp-empty-illus__card b:last-child {
	width: 44%;
}

.sp-empty-illus__card.is-accent {
	border-color: #8b5cf6;
}

.sp-empty-illus__face {
	position: absolute;
	z-index: 3;
	width: 32px;
	height: 32px;
	overflow: hidden;
	border-radius: 50%;
	background: #ddd;
	box-shadow: 0 1px 3px rgba(16, 24, 40, 0.14);
}

.sp-empty-illus__face svg {
	display: block;
	width: 100%;
	height: 100%;
}

.sp-empty-illus__face.is-fade {
	opacity: 0.55;
	filter: grayscale(0.3);
}

.sp-empty-illus__face--tl {
	top: 18px;
	left: 18px;
}

.sp-empty-illus__face--tr {
	top: 12px;
	right: 16px;
	width: 36px;
	height: 36px;
}

.sp-empty-illus__face--l {
	top: 84px;
	left: 4px;
}

.sp-empty-illus__face--r {
	top: 78px;
	right: 2px;
	width: 34px;
	height: 34px;
}

.sp-empty-illus__face--bl {
	bottom: 16px;
	left: 28px;
	width: 30px;
	height: 30px;
}

.sp-empty-illus__face--br {
	right: 22px;
	bottom: 14px;
}

.sp-empty-illus__face--tc {
	top: 2px;
	left: calc(50% + 28px);
	width: 28px;
	height: 28px;
}

.sp-empty-list__title {
	margin: 0 0 8px;
	font-size: 1.25rem;
	font-weight: 750;
	letter-spacing: -0.02em;
	color: #111111;
}

.sp-empty-list__text {
	margin: 0;
	max-width: 22rem;
	font-size: 0.875rem;
	line-height: 1.5;
	color: #6b7280;
}

.sp-empty-list--table .sp-empty-list__text {
	max-width: none;
}

@media (max-width: 420px) {
	.sp-empty-illus {
		margin-bottom: 8px;
		transform: scale(0.86);
		transform-origin: center center;
	}
}
</style>
