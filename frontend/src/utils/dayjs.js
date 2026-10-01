import dayjs from "dayjs"
import updateLocale from "dayjs/plugin/updateLocale"
import localizedFormat from "dayjs/plugin/localizedFormat"
import relativeTime from "dayjs/plugin/relativeTime"
import isToday from "dayjs/plugin/isToday"
import isYesterday from "dayjs/plugin/isYesterday"
import isBetween from "dayjs/plugin/isBetween"
import utc from "dayjs/plugin/utc"
import timezone from "dayjs/plugin/timezone"

export const STAFF_PRO_TIMEZONE = "America/Belize"

dayjs.extend(updateLocale)
dayjs.extend(localizedFormat)
dayjs.extend(relativeTime)
dayjs.extend(isToday)
dayjs.extend(isYesterday)
dayjs.extend(isBetween)
dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.tz.setDefault(STAFF_PRO_TIMEZONE)

function hasExplicitOffset(value) {
	return /(?:Z|[+-]\d{2}:?\d{2})$/i.test(String(value).trim())
}

function safeTz(value) {
	try {
		const zoned = dayjs.tz(value, STAFF_PRO_TIMEZONE)
		return zoned?.isValid?.() ? zoned : dayjs(NaN)
	} catch {
		return dayjs(NaN)
	}
}

const originalFormat = dayjs.prototype.format
dayjs.prototype.format = function formatWithoutThrow(...args) {
	try {
		const formatted = originalFormat.apply(this, args)
		return formatted == null ? "" : String(formatted)
	} catch {
		return ""
	}
}

function staffProDayjs(...args) {
	if (!args.length) {
		return dayjs.tz()
	}
	const value = args[0]
	if (typeof value === "number") {
		return Number.isFinite(value) ? safeTz(value) : dayjs(NaN)
	}
	if (value instanceof Date) {
		return Number.isNaN(value.getTime()) ? dayjs(value) : safeTz(value)
	}
	if (typeof value === "string") {
		const trimmed = value.trim()
		if (!trimmed || hasExplicitOffset(trimmed)) {
			try {
				return dayjs(...args)
			} catch {
				return dayjs(NaN)
			}
		}
		let probe
		try {
			probe = dayjs(trimmed)
		} catch {
			return dayjs(NaN)
		}
		if (!probe?.isValid?.()) return probe || dayjs(NaN)
		return safeTz(trimmed)
	}
	return dayjs(...args)
}

Object.assign(staffProDayjs, dayjs)
staffProDayjs.tz = dayjs.tz
staffProDayjs.utc = dayjs.utc
staffProDayjs.extend = dayjs.extend
staffProDayjs.locale = dayjs.locale
staffProDayjs.isDayjs = dayjs.isDayjs
staffProDayjs.unix = dayjs.unix

export default staffProDayjs
