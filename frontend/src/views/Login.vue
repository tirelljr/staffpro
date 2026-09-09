<template>
	<ion-page>
		<ion-content :fullscreen="true" class="ion-no-padding" style="--background: #ffffff">
			<div
				v-if="resetPassword.showDialog"
				class="flex h-screen w-screen flex-col bg-white"
			>
				<header class="flex items-center justify-between px-6 py-4">
					<div class="text-lg font-semibold text-gray-900">
						{{ __("Reset Password") }}
					</div>
					<button
						type="button"
						class="text-sm text-gray-600 hover:text-gray-900 underline"
						@click="resetPassword.showDialog = false"
					>
						{{ __("Back to Login") }}
					</button>
				</header>
				<div class="flex flex-1 flex-col items-center justify-center px-8 text-center">
					<p class="text-gray-700">
						{{ __("Your password has expired. Please reset your password to continue") }}
					</p>
					<a
						class="mt-6 inline-flex items-center justify-center gap-2 transition-colors focus:outline-none text-white bg-brand-navy hover:bg-[#125a7a] active:bg-[#0f4d68] focus-visible:ring focus-visible:ring-brand-navy h-9 text-base px-4 rounded-full"
						:href="resetPassword.link"
						target="_blank"
					>
						{{ __("Go to Reset Password page") }}
					</a>
				</div>
			</div>

			<div v-else class="min-h-screen w-full bg-white flex flex-col items-center px-4 py-6">
				<img :src="logoUrl" alt="Staff Pro BPO" class="h-16 w-auto mb-4" />

				<div class="w-full max-w-xl flex flex-col items-center">
					<div class="text-2xl text-gray-400 font-medium min-h-8 text-center">
						{{ displayName }}
					</div>

					<form
						v-if="!user_pass_login_disabled.data"
						class="w-full mt-4 flex flex-col gap-3"
						@submit.prevent="submitClock"
					>
						<div class="relative">
							<input
								v-model="username"
								type="text"
								autocomplete="username"
								:placeholder="__('Username')"
								list="remembered-usernames"
								class="w-full border border-gray-400 bg-white px-3 py-2 text-base text-gray-900"
								@focus="showRemembered = true"
								@blur="hideRememberedSoon"
								@input="onUsernameInput"
							/>
							<datalist id="remembered-usernames">
								<option v-for="user in rememberedUsers" :key="user.username" :value="user.username" />
							</datalist>
							<div
								v-if="showRemembered && rememberedUsers.length"
								class="absolute z-10 mt-1 w-full border border-gray-200 bg-white shadow-sm"
							>
								<button
									v-for="user in rememberedUsers"
									:key="user.username"
									type="button"
									class="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-gray-50"
									@mousedown.prevent="selectRemembered(user)"
								>
									<span class="font-medium text-gray-800">{{ user.username }}</span>
									<span class="text-xs text-gray-500">{{ user.employee_name }}</span>
								</button>
							</div>
						</div>

						<input
							v-model="password"
							type="password"
							autocomplete="current-password"
							:placeholder="__('Password')"
							class="w-full border border-gray-400 bg-white px-3 py-2 text-base text-gray-900"
						/>

						<ErrorMessage :message="errorMessage" />
						<div v-if="successMessage" class="text-sm text-green-700 text-center">{{ successMessage }}</div>

						<div class="flex flex-col sm:flex-row sm:items-center gap-3 my-2">
							<div class="text-4xl sm:text-5xl font-semibold text-gray-400 tracking-wide text-center sm:text-left tabular-nums shrink-0">
								{{ clockLabel }}
							</div>
							<div class="flex-1 min-w-0">
								<button
									type="submit"
									class="w-full py-3 text-white text-lg font-semibold disabled:opacity-60"
									:class="clockAction === 'OUT' ? 'bg-red-600 hover:bg-red-700' : 'bg-emerald-600 hover:bg-emerald-700'"
									:disabled="clocking || session.login.loading"
								>
									{{ clocking ? __("Saving...") : clockAction === "OUT" ? __("CLOCK OUT") : __("CLOCK IN") }}
								</button>
								<div v-if="activityLabels.length" class="mt-2 text-sm text-[#11a5dd] text-center sm:text-left">
									<div v-for="(label, idx) in activityLabels" :key="idx">{{ label }}</div>
								</div>
							</div>
						</div>

						<button
							type="button"
							class="w-full py-3 text-white text-lg font-semibold bg-[#2f6fdb] hover:bg-[#2558b0] disabled:opacity-60"
							:disabled="clocking || session.login.loading"
							@click="submitLogin"
						>
							{{ session.login.loading ? __("Signing in...") : __("Login") }}
						</button>

						<div class="flex items-center justify-between text-sm mt-1">
							<label class="inline-flex items-center gap-2 text-gray-700">
								<input v-model="rememberPassword" type="checkbox" class="rounded border-gray-400" />
								{{ __("remember password") }}
							</label>
							<router-link
								:to="{ name: 'ForgotPassword', query: username ? { username } : {} }"
								class="text-[#2f6fdb] hover:underline"
							>
								{{ __("forgot password") }}
							</router-link>
						</div>
					</form>

					<template v-if="authProviders.data?.length">
						<div v-if="!user_pass_login_disabled.data" class="text-center text-sm text-gray-600 my-4">or</div>
						<div class="space-y-4 w-full">
							<a
								v-for="provider in authProviders.data"
								:key="provider.name"
								class="flex items-center justify-center gap-2 transition-colors focus:outline-none text-gray-800 bg-gray-100 hover:bg-gray-200 active:bg-gray-300 focus-visible:ring focus-visible:ring-gray-400 h-7 text-base p-2 rounded"
								:href="provider.auth_url"
							>
								<img class="h-4 w-4" :src="provider.icon" :alt="provider.provider_name" />
								<span>Login with {{ provider.provider_name }}</span>
							</a>
						</div>
					</template>

					<div v-else-if="user_pass_login_disabled.data" class="text-center text-gray-600 py-8">
						{{ __("No login methods are available. Please contact your administrator.") }}
					</div>

					<div class="w-full mt-8 bg-gray-200 text-gray-700 text-xs leading-5 px-3 py-2">
						<div>{{ __("IP:") }} {{ displayIp }}</div>
						<div>{{ __("Device ID:") }} {{ displayDeviceId }}</div>
						<div>{{ __("WIFI:") }} {{ wifiLabel }}</div>
						<div>{{ __("GPS:") }} {{ gpsLabel }}</div>
						<div>{{ __("Company ID:") }} {{ kioskContext.data?.company_id || "na" }}</div>
						<div>{{ __("Company name:") }} {{ kioskContext.data?.company_name || "Staff Pro" }}</div>
					</div>

					<button type="button" class="mt-6 text-[#2f6fdb] text-sm hover:underline" @click="refreshKiosk">
						{{ __("refresh") }}
					</button>
				</div>
			</div>

			<Dialog v-model="otp.showDialog">
				<template #body-title>
					<h2 class="text-lg font-bold">{{ __("OTP Verification") }}</h2>
				</template>
				<template #body-content>
					<p class="mb-4" v-if="otp.verification.prompt">
						{{ otp.verification.prompt }}
					</p>

					<form class="flex flex-col space-y-4" @submit.prevent="submitLogin">
						<Input
							:label="__('OTP Code')"
							type="text"
							placeholder="000000"
							v-model="otp.code"
							autocomplete="one-time-code"
						/>
						<ErrorMessage :message="errorMessage" />
						<Button
							:loading="session.otp.loading"
							variant="solid"
							class="btn-brand disabled:bg-gray-700 disabled:text-white !mt-6"
						>
							{{ __("Verify") }}
						</Button>
					</form>
				</template>
			</Dialog>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { computed, inject, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import { Input, Button, ErrorMessage, Dialog, createResource, call, debounce } from "frappe-ui"
import { STAFF_PRO_LOGO_URL } from "@/utils/branding"
import { scanClientIpv4, isPlaceholderPeerIpv4 } from "@/utils/clientIp"
import {
	forgetPassword,
	getDeviceId,
	getLastUsername,
	getRememberedUser,
	getRememberedUsers,
	rememberUser,
} from "@/utils/rememberedUsers"

const logoUrl = STAFF_PRO_LOGO_URL

const username = ref(getLastUsername())
const password = ref("")
const rememberPassword = ref(false)
const errorMessage = ref("")
const successMessage = ref("")
const clocking = ref(false)
const showRemembered = ref(false)
const rememberedUsers = ref(getRememberedUsers())
const localDeviceId = getDeviceId()
const clockLabel = ref("")
const scannedIp = ref("")
const ipScanDone = ref(false)
const latitude = ref(null)
const longitude = ref(null)
let clockTimer = null
let rememberedTimer = null

const resetPassword = reactive({
	showDialog: false,
	link: "",
})
const otp = reactive({
	showDialog: false,
	tmp_id: "",
	code: "",
	verification: {},
})

const session = inject("$session")
const __ = inject("$translate")
const dayjs = inject("$dayjs")

const liveProfile = ref(null)
const selectedRemembered = computed(() => getRememberedUser(username.value))
const activeProfile = computed(() => liveProfile.value || selectedRemembered.value)
const displayName = computed(() => activeProfile.value?.employee_name || "")
const clockAction = computed(() => activeProfile.value?.next_action || "IN")
const activityLabels = computed(() => {
	const user = activeProfile.value
	if (!user) return []
	if (Array.isArray(user.today_labels) && user.today_labels.length) {
		return user.today_labels.filter(Boolean)
	}
	return [user.last_in_label, user.last_pair_label].filter(Boolean)
})
const wifiLabel = computed(() => navigator.onLine ? "online" : "na")
const gpsLabel = computed(() => {
	if (latitude.value == null || longitude.value == null) return "na"
	return `${Number(latitude.value).toFixed(4)}, ${Number(longitude.value).toFixed(4)}`
})

const user_pass_login_disabled = createResource({
	url: "hrms.api.system_settings.get_user_pass_login_disabled",
	method: "GET",
	initialData: 1,
	auto: true,
})

const authProviders = createResource({
	url: "hrms.api.oauth.oauth_providers",
	auto: true,
})

const kioskContext = createResource({
	url: "hrms.api.kiosk.get_kiosk_context",
	auto: true,
})

const displayDeviceId = computed(() => {
	return (
		activeProfile.value?.device_id ||
		kioskContext.data?.device_id ||
		localDeviceId ||
		"na"
	)
})

const displayIp = computed(() => {
	if (scannedIp.value) return scannedIp.value
	const serverIp = kioskContext.data?.ip || ""
	if (serverIp && !isPlaceholderPeerIpv4(serverIp)) return serverIp
	if (!ipScanDone.value) return __("scanning...")
	return serverIp || "na"
})

function tickClock() {
	clockLabel.value = dayjs().format("hh:mm:ss A")
}

function applyRememberedUser() {
	const user = getRememberedUser(username.value)
	if (!user) return
	rememberPassword.value = Boolean(user.password)
	if (user.password) password.value = user.password
}

function applyLiveProfile(profile) {
	if (!profile?.username) {
		liveProfile.value = null
		return
	}
	liveProfile.value = profile
	const existing = getRememberedUser(profile.username)
	if (!existing) return
	rememberUser(profile, {
		password: existing.password,
		rememberPassword: Boolean(existing.password),
	})
	rememberedUsers.value = getRememberedUsers()
}

const fetchKioskProfile = debounce(async (login) => {
	const value = (login || "").trim()
	if (!value) {
		liveProfile.value = null
		return
	}
	try {
		const profile = await call("hrms.api.kiosk.get_kiosk_profile", {
			username: value,
			client_ip: scannedIp.value || undefined,
		})
		if ((username.value || "").trim().toLowerCase() !== value.toLowerCase()) return
		applyLiveProfile(profile)
	} catch {
		if ((username.value || "").trim().toLowerCase() === value.toLowerCase()) {
			liveProfile.value = null
		}
	}
}, 350)

function onUsernameInput() {
	applyRememberedUser()
	fetchKioskProfile(username.value)
}

function selectRemembered(user) {
	username.value = user.username
	showRemembered.value = false
	applyRememberedUser()
	fetchKioskProfile(user.username)
}

function hideRememberedSoon() {
	clearTimeout(rememberedTimer)
	rememberedTimer = setTimeout(() => {
		showRemembered.value = false
	}, 150)
}

function persistProfile(profile) {
	rememberUser(profile, {
		password: password.value,
		rememberPassword: rememberPassword.value,
	})
	if (!rememberPassword.value) {
		forgetPassword(profile.username)
	}
	rememberedUsers.value = getRememberedUsers()
}

function readFieldValue(selector) {
	const el = document.querySelector(selector)
	return (el?.value || "").trim()
}

function requireCredentials() {
	const login = (username.value || "").trim() || readFieldValue('input[autocomplete="username"]')
	const pass = password.value || readFieldValue('input[autocomplete="current-password"]')
	if (login && login !== username.value) username.value = login
	if (pass && pass !== password.value) password.value = pass
	if (!login || !pass) {
		errorMessage.value = __("Enter your username and password")
		return null
	}
	return login
}

async function submitClock() {
	const login = requireCredentials()
	if (!login) return

	errorMessage.value = ""
	successMessage.value = ""
	clocking.value = true
	try {
		const profile = await call("hrms.api.kiosk.clock", {
			username: login,
			password: password.value,
			log_type: clockAction.value,
			latitude: latitude.value,
			longitude: longitude.value,
			device_id: localDeviceId,
			client_ip: scannedIp.value || undefined,
		})
		persistProfile(profile)
		applyLiveProfile(profile)
		const actionLabel = profile.log_type === "OUT" ? __("Clocked out") : __("Clocked in")
		successMessage.value = __("{0} at {1}", [actionLabel, profile.time_label || clockLabel.value])
	} catch (error) {
		errorMessage.value = error.messages?.join("\n") || __("Clock-in failed")
	} finally {
		clocking.value = false
	}
}

async function submitLogin(e) {
	try {
		let response
		if (otp.showDialog) {
			response = await session.otp(otp.tmp_id, otp.code)
		} else {
			const login = requireCredentials()
			if (!login) return
			response = await session.login(login, password.value)
			persistProfile({
				username: login,
				employee_name: activeProfile.value?.employee_name || "",
				last_in_label: activeProfile.value?.last_in_label || "",
				last_pair_label: activeProfile.value?.last_pair_label || "",
				today_labels: activeProfile.value?.today_labels || [],
				next_action: activeProfile.value?.next_action || "IN",
			})
		}

		if (response.message === "Password Reset") {
			resetPassword.showDialog = true
			resetPassword.link = response.redirect_to
		} else {
			resetPassword.showDialog = false
			resetPassword.link = ""
		}

		if (response.verification) {
			if (response.verification.setup) {
				otp.showDialog = true
				otp.tmp_id = response.tmp_id
				otp.verification = response.verification
			} else {
				window.open("/login?redirect-to=" + encodeURIComponent(window.location.pathname), "_blank")
			}
		}
	} catch (error) {
		errorMessage.value =
			error.messages?.join("\n") || error.message || __("Invalid login credentials")
	}
}

function refreshKiosk() {
	window.location.reload()
}

function fetchLocation() {
	if (!navigator.geolocation) return
	navigator.geolocation.getCurrentPosition(
		(position) => {
			latitude.value = position.coords.latitude
			longitude.value = position.coords.longitude
		},
		() => {},
	)
}

async function scanKioskIp() {
	try {
		const ip = await scanClientIpv4()
		if (ip) {
			scannedIp.value = ip
			kioskContext.submit?.({ client_ip: ip })
		}
	} catch {
		/* keep the server-reported IP */
	} finally {
		ipScanDone.value = true
	}
}

onMounted(() => {
	tickClock()
	clockTimer = setInterval(tickClock, 1000)
	applyRememberedUser()
	if (username.value) fetchKioskProfile(username.value)
	scanKioskIp()
	if (kioskContext.data?.allow_geolocation_tracking) {
		fetchLocation()
	} else {
		kioskContext.reload?.()
		setTimeout(() => {
			if (kioskContext.data?.allow_geolocation_tracking) fetchLocation()
		}, 800)
	}
})

onBeforeUnmount(() => {
	clearInterval(clockTimer)
	clearTimeout(rememberedTimer)
})
</script>
