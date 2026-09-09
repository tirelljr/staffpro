const IPV4 = /\b(\d{1,3}(?:\.\d{1,3}){3})\b/

function normalizeIpv4(value) {
	const text = String(value || "").trim()
	const match = text.match(IPV4)
	if (!match) return ""
	const parts = match[1].split(".").map((part) => Number(part))
	if (parts.length !== 4 || parts.some((part) => Number.isNaN(part) || part < 0 || part > 255)) {
		return ""
	}
	return parts.join(".")
}

function isLoopbackOrLinkLocal(ip) {
	return ip.startsWith("127.") || ip.startsWith("169.254.") || ip === "0.0.0.0"
}

function isPublicIpv4(ip) {
	if (!ip || isLoopbackOrLinkLocal(ip)) return false
	const [a, b] = ip.split(".").map(Number)
	if (a === 10) return false
	if (a === 192 && b === 168) return false
	if (a === 172 && b >= 16 && b <= 31) return false
	return true
}

export function isPlaceholderPeerIpv4(ip) {
	if (!ip) return true
	if (isLoopbackOrLinkLocal(ip)) return true
	const [a, b] = String(ip).split(".").map(Number)
	return a === 172 && b >= 17 && b <= 31
}

function pickBestIpv4(ips) {
	const unique = []
	for (const raw of ips) {
		const ip = normalizeIpv4(raw)
		if (!ip || isLoopbackOrLinkLocal(ip) || unique.includes(ip)) continue
		unique.push(ip)
	}
	return unique.find(isPublicIpv4) || unique[0] || ""
}

function ipv4FromCandidate(candidate) {
	if (!candidate) return ""
	if (candidate.address) {
		const fromAddress = normalizeIpv4(candidate.address)
		if (fromAddress) return fromAddress
	}
	return normalizeIpv4(candidate.candidate)
}

function scanIceIpv4s(timeoutMs = 2500) {
	if (typeof RTCPeerConnection === "undefined") {
		return Promise.resolve([])
	}

	return new Promise((resolve) => {
		const ips = []
		let settled = false
		const finish = () => {
			if (settled) return
			settled = true
			try {
				pc.close()
			} catch {
				/* ignore */
			}
			resolve(ips)
		}

		const pc = new RTCPeerConnection({
			iceServers: [{ urls: ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"] }],
		})
		pc.createDataChannel("kiosk-ip")
		pc.onicecandidate = (event) => {
			if (!event.candidate) {
				finish()
				return
			}
			const ip = ipv4FromCandidate(event.candidate)
			if (ip && !ips.includes(ip)) ips.push(ip)
		}

		pc.createOffer()
			.then((offer) => pc.setLocalDescription(offer))
			.catch(finish)

		setTimeout(finish, timeoutMs)
	})
}

async function lookupPublicIpv4() {
	const urls = ["https://api.ipify.org?format=json", "https://api64.ipify.org?format=json"]
	for (const url of urls) {
		try {
			const response = await fetch(url, { cache: "no-store" })
			if (!response.ok) continue
			const data = await response.json()
			const ip = normalizeIpv4(data?.ip)
			if (ip) return ip
		} catch {
			/* try next */
		}
	}

	try {
		const response = await fetch("https://icanhazip.com", { cache: "no-store" })
		if (!response.ok) return ""
		return normalizeIpv4(await response.text())
	} catch {
		return ""
	}
}

export async function scanClientIpv4() {
	const iceIps = await scanIceIpv4s()
	const bestIce = pickBestIpv4(iceIps)
	if (isPublicIpv4(bestIce)) return bestIce

	const publicIp = await lookupPublicIpv4()
	return publicIp || bestIce
}
