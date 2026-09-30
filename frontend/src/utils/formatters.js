import { createDocumentResource } from "frappe-ui"

import dayjs from "@/utils/dayjs"

const settings = createDocumentResource({
	doctype: "System Settings",
	name: "System Settings",
	auto: false,
})

export const formatCurrency = (value, currency) => {
	if (!currency) return value

	// hack: if value contains a space, it is already formatted
	if (value?.toString().trim().includes(" ")) return value

	const locale = settings.doc?.country == "India" ? "en-IN" : settings.doc?.language

	const formatter = Intl.NumberFormat(locale, {
		style: "currency",
		currency: currency,
		trailingZeroDisplay: "stripIfInteger",
		currencyDisplay: "narrowSymbol",
	})
	return (
		formatter
			.format(value)
			// add space between the digits and symbol
			.replace(/^(\D+)/, "$1 ")
			// remove extra spaces if any (added by some browsers)
			.replace(/\s+/, " ")
	)
}

export const CLOCK_FORMAT = "h:mm A"

export const formatTimestamp = (timestamp) => {
	const formattedTime = dayjs(timestamp).format(CLOCK_FORMAT)

	if (dayjs(timestamp).isToday()) return formattedTime
	else if (dayjs(timestamp).isYesterday()) return `${formattedTime} yesterday`
	else if (dayjs(timestamp).isSame(dayjs(), "year"))
		return `${formattedTime} on ${dayjs(timestamp).format("D MMM")}`

	return `${formattedTime} on ${dayjs(timestamp).format("D MMM, YYYY")}`
}

export const formatHours = (value, keepZero = false) => {
	if (value === null || value === undefined || value === "") {
		return keepZero ? "0h 0m" : ""
	}
	const totalMinutes = Math.round(Number(value) * 60)
	if (!keepZero && !totalMinutes) return ""
	const sign = totalMinutes < 0 ? "-" : ""
	const abs = Math.abs(totalMinutes)
	const hours = Math.floor(abs / 60)
	const minutes = abs % 60
	return `${sign}${hours}h ${minutes}m`
}

const TIME_PART = /(\d{1,2}):(\d{2})(?::(\d{2}))?/

function formatWallClock(hours, minutes) {
	const hour = Number(hours)
	const minute = Number(minutes)
	if (!Number.isFinite(hour) || !Number.isFinite(minute)) return ""
	if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return ""
	const suffix = hour >= 12 ? "PM" : "AM"
	const hour12 = hour % 12 || 12
	return `${hour12}:${String(minute).padStart(2, "0")} ${suffix}`
}

export const formatClock = (value) => {
	try {
		if (value === null || value === undefined || value === "") return ""
		const raw = String(value).trim()
		if (!raw) return ""
		const match = raw.match(TIME_PART)
		if (!match) return ""
		return formatWallClock(match[1], match[2])
	} catch {
		return ""
	}
}

export const formatHoursNote = (comment) => {
	try {
		if (!comment) return ""
		if (typeof comment === "string") return comment
		const when = dayjs(comment.creation)
		let time = ""
		let date = ""
		if (when?.isValid?.()) {
			time = when.format(CLOCK_FORMAT)
			date = when.format("MM/DD/YYYY")
		}
		const author = comment.comment_by || "Admin"
		const text = comment.content || ""
		if (time && date) return `Note (${author}, ${time}, ${date}): ${text}`
		return text ? `Note (${author}): ${text}` : ""
	} catch {
		return comment?.content || ""
	}
}
