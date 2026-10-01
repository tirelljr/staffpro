/**
 * Frappe /api/method/login expects form-urlencoded bodies on this site.
 * frappe-ui call() sends JSON, which returns 417 Invalid request body.
 */
export async function frappeFormLogin(params) {
	const body = new URLSearchParams()
	for (const [key, value] of Object.entries(params || {})) {
		if (value !== undefined && value !== null && value !== "") {
			body.set(key, String(value))
		}
	}

	const headers = {
		Accept: "application/json",
		"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
		"X-Frappe-Site-Name": window.location.hostname,
	}
	if (window.csrf_token && window.csrf_token !== "{{ csrf_token }}") {
		headers["X-Frappe-CSRF-Token"] = window.csrf_token
	}

	const res = await fetch("/api/method/login", {
		method: "POST",
		headers,
		body,
		credentials: "include",
	})

	if (res.ok) {
		return res.json()
	}

	let error
	try {
		error = JSON.parse(await res.text())
	} catch {
		error = {}
	}

	const e = new Error(
		[error.exc_type, error._error_message].filter(Boolean).join(" ") ||
			"Login failed",
	)
	e.exc_type = error.exc_type
	e.status = res.status
	e.messages = error._server_messages ? JSON.parse(error._server_messages) : []
	e.messages = e.messages.concat(error.message || [])
	e.messages = e.messages
		.map((m) => {
			try {
				return JSON.parse(m).message
			} catch {
				return m
			}
		})
		.filter(Boolean)
	if (!e.messages.length && error._error_message) {
		e.messages = [error._error_message]
	}
	throw e
}
