import { io } from "socket.io-client"

import { getCachedListResource } from "frappe-ui/src/resources/listResource"
import { getCachedResource } from "frappe-ui/src/resources/resources"

function resolveSocketioPort() {
	const socketioPort = Number(window.frappe?.boot?.socketio_port || 9000)
	const webserverPort = Number(window.frappe?.boot?.webserver_port || 8000)
	const pagePort = Number(window.location.port)
	if (!pagePort) return socketioPort
	// Host publish offset, e.g. container 8000/9000 mapped to host 8001/9001
	return socketioPort + (pagePort - webserverPort)
}

export function initSocket() {
	let host = window.location.hostname
	let siteName = window.site_name || window.frappe?.boot?.site_name || ""
	let socketio_port = resolveSocketioPort()
	let port = window.location.port ? `:${socketio_port}` : ""
	let protocol = window.location.protocol === "https:" ? "https" : port ? "http" : "https"
	let url = `${protocol}://${host}${port}/${siteName}`
	let socket = io(url, {
		withCredentials: true,
		reconnectionAttempts: 3,
	})

	socket.on("hrms:refetch_resource", (data) => {
		if (data.cache_key) {
			let resource =
				getCachedResource(data.cache_key) ||
				getCachedListResource(data.cache_key)

			if (resource) {
				resource.reload()
			}
		}
	})

	return socket
}
