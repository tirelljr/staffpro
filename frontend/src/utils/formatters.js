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

export const formatTimestamp = (timestamp) => {
	const formattedTime = dayjs(timestamp).format("hh:mm a")

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

export const formatClock = (value) => {
	if (!value) return ""
	const parsed = dayjs(value)
	return parsed.isValid() ? parsed.format("hh:mm a") : ""
}

export const formatHoursNote = (comment) => {
	if (!comment) return ""
	const when = dayjs(comment.creation)
	const time = when.isValid() ? when.format("hh:mm A") : ""
	const date = when.isValid() ? when.format("MM/DD/YYYY") : ""
	const author = comment.comment_by || "Admin"
	const text = comment.content || ""
	if (time && date) return `Note (${author}, ${time}, ${date}): ${text}`
	return text ? `Note (${author}): ${text}` : ""
}
