const STORAGE_KEY = "sp_kiosk_users"
const DEVICE_KEY = "sp_kiosk_device_id"

function readStore() {
	try {
		const raw = localStorage.getItem(STORAGE_KEY)
		const data = raw ? JSON.parse(raw) : {}
		return {
			lastUsername: data.lastUsername || "",
			users: Array.isArray(data.users) ? data.users : [],
		}
	} catch {
		return { lastUsername: "", users: [] }
	}
}

function writeStore(store) {
	localStorage.setItem(STORAGE_KEY, JSON.stringify(store))
}

export function getDeviceId() {
	let id = localStorage.getItem(DEVICE_KEY)
	if (!id) {
		id = String(1000 + Math.floor(Math.random() * 9000))
		localStorage.setItem(DEVICE_KEY, id)
	}
	return id
}

export function getRememberedUsers() {
	return readStore().users
}

export function getLastUsername() {
	return readStore().lastUsername
}

export function getRememberedUser(username) {
	if (!username) return null
	const key = username.trim().toLowerCase()
	return readStore().users.find((user) => user.username.toLowerCase() === key) || null
}

export function rememberUser(profile, { password, rememberPassword } = {}) {
	const username = (profile?.username || "").trim()
	if (!username) return

	const store = readStore()
	const next = {
		username,
		employee_name: profile.employee_name || "",
		last_in_label: profile.last_in_label || "",
		last_pair_label: profile.last_pair_label || "",
		today_labels: Array.isArray(profile.today_labels) ? profile.today_labels : [],
		next_action: profile.next_action || "IN",
		password: rememberPassword ? password || "" : "",
	}
	store.users = [next, ...store.users.filter((user) => user.username.toLowerCase() !== username.toLowerCase())].slice(
		0,
		8,
	)
	store.lastUsername = username
	writeStore(store)
}

export function forgetPassword(username) {
	const store = readStore()
	store.users = store.users.map((user) =>
		user.username.toLowerCase() === String(username || "").toLowerCase() ? { ...user, password: "" } : user,
	)
	writeStore(store)
}
