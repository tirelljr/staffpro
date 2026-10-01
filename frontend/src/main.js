import { createApp } from "vue"
import App from "./App.vue"
import router from "./router"
import { initSocket } from "./socket"

import {
	Button,
	Input,
	setConfig,
	frappeRequest,
	resourcesPlugin,
	FormControl,
} from "frappe-ui"
import { translationsPlugin } from "./plugins/translationsPlugin.js"
import EmptyState from "@/components/EmptyState.vue"

import { IonicVue } from "@ionic/vue"

import { adoptBootSession, session, sessionUser } from "@/data/session"
import { userResource } from "@/data/user"
import { employeeResource } from "@/data/employee"
import { syncNotificationResources } from "@/data/notifications"
import { canOpenDesk, canUseMyWorkPortal } from "@/utils/deskAccess"
import { consumeKioskPortalLoginIntent } from "@/utils/kioskPortal"
import { consumeMyWorkHandoff } from "@/utils/myWorkHandoff"

import dayjs from "@/utils/dayjs"
import getIonicConfig from "@/utils/ionicConfig"

import FrappePushNotification from "../public/frappe-push-notification"

/* Core CSS required for Ionic components to work properly */
import "@ionic/vue/css/core.css"

/* Theme variables */
import "./theme/variables.css"

import "./main.css"

const app = createApp(App)
const socket = initSocket()

setConfig("resourceFetcher", frappeRequest)
app.use(resourcesPlugin)
app.use(translationsPlugin)

app.component("Button", Button)
app.component("Input", Input)
app.component("FormControl", FormControl)
app.component("EmptyState", EmptyState)

app.use(router)
app.use(IonicVue, getIonicConfig())

if (session?.isLoggedIn && !employeeResource?.data) {
	employeeResource.reload()
}

app.provide("$session", session)
app.provide("$user", userResource)
app.provide("$employee", employeeResource)
app.provide("$socket", socket)
app.provide("$dayjs", dayjs)

const registerServiceWorker = async () => {
	window.frappePushNotification = new FrappePushNotification("hrms")

	if ("serviceWorker" in navigator) {
		let serviceWorkerURL = "/assets/hrms/frontend/sw.js"
		let config = ""

		if (window.frappe?.boot?.push_relay_server_url) {
			try {
				config = await window.frappePushNotification.fetchWebConfig()
				serviceWorkerURL = `${serviceWorkerURL}?config=${encodeURIComponent(
					JSON.stringify(config)
				)}`
			} catch (err) {
				console.error("Failed to fetch FCM config", err)
			}
		}

		navigator.serviceWorker
			.register(serviceWorkerURL, {
				type: "classic",
			})
			.then((registration) => {
				if (config) {
					window.frappePushNotification.initialize(registration).then(() => {
						console.log("Frappe Push Notification initialized")
					})
				}
			})
			.catch((err) => {
				console.error("Failed to register service worker", err)
			})
	} else {
		console.error("Service worker not enabled/supported by the browser")
	}
}

router.isReady().then(async () => {
	await translationsPlugin.isReady();
	registerServiceWorker()
	app.mount("#app")
})

let devBootLoaded = !import.meta.env.DEV

async function ensureBoot() {
	if (devBootLoaded) return
	devBootLoaded = true
	try {
		const values = await frappeRequest({
			url: "/api/method/hrms.www.hrms.get_context_for_dev",
		})
		if (!window.frappe) window.frappe = {}
		window.frappe.boot = values
	} catch (error) {
		console.error("Failed to load HRMS boot context", error)
	}
}

const KIOSK_ROUTES = new Set(["Login", "ForgotPassword"])
const KIOSK_HOME_ROUTES = new Set(["AttendanceDashboard"])

router.beforeEach(async (to, _, next) => {
	await ensureBoot()
	await consumeMyWorkHandoff()
	adoptBootSession()

	let isLoggedIn = session.isLoggedIn

	try {
		if (isLoggedIn) {
			await userResource.reload()
			syncNotificationResources()
		}
	} catch (error) {
		// Keep kiosk portal entry working when reload races the new session cookie.
		isLoggedIn = Boolean(session.user || sessionUser())
	}

	const myWork =
		isLoggedIn &&
		(Boolean(window.frappe?.boot?.staff_pro_my_work) || canUseMyWorkPortal(userResource.data))

	if (!isLoggedIn) {
		// password reset page is outside the PWA scope
		if (to.path === "/update-password") {
			return next(false)
		}
		if (!KIOSK_ROUTES.has(to.name)) {
			return next({ name: "Login" })
		}
		return next()
	}

	// Already signed in on the desk: My Work opens the portal, not the password form.
	if (myWork && to.name === "Login") {
		return next({ name: "AttendanceDashboard" })
	}

	// Kiosk and password reset stay on-screen even if a desk session cookie exists.
	if (KIOSK_ROUTES.has(to.name) || to.name === "InvalidEmployee") {
		return next()
	}

	// Desk admins opening /agents land on the kiosk, except HR Assistants using My Work
	// or a kiosk that just signed an agent into the portal.
	if (canOpenDesk(userResource.data) && KIOSK_HOME_ROUTES.has(to.name)) {
		if (consumeKioskPortalLoginIntent() || myWork) {
			return next()
		}
		return next({ name: "Login" })
	}

	await employeeResource.promise
	// Portal views are employee-specific; the session user must match an Employee.
	if (
		!employeeResource?.data ||
		employeeResource?.data?.user_id !== userResource.data?.name
	) {
		return next({ name: "InvalidEmployee" })
	}

	next()
})
