const KIOSK_PORTAL_LOGIN_KEY = "staff_pro_kiosk_portal_login"

/** Set when the agent explicitly taps "Open my portal" on the kiosk login screen. */
export function markKioskPortalLoginIntent() {
	try {
		sessionStorage.setItem(KIOSK_PORTAL_LOGIN_KEY, "1")
	} catch {
		/* private mode / blocked storage */
	}
}

export function consumeKioskPortalLoginIntent() {
	try {
		const value = sessionStorage.getItem(KIOSK_PORTAL_LOGIN_KEY)
		if (value) sessionStorage.removeItem(KIOSK_PORTAL_LOGIN_KEY)
		return Boolean(value)
	} catch {
		return false
	}
}

/**
 * Device id sent to Frappe login (registered-device lock).
 * Prefer the workstation/cubicle id shown on the kiosk over a browser UUID.
 */
export function getKioskLoginDeviceId({ profileDeviceId, contextDeviceId, fallbackDeviceId }) {
	const candidates = [profileDeviceId, contextDeviceId, fallbackDeviceId]
	for (const raw of candidates) {
		const id = String(raw || "").trim()
		if (id) return id
	}
	return fallbackDeviceId
}
