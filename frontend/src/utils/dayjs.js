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

function staffProDayjs(...args) {
	if (!args.length) {
		return dayjs.tz()
	}
	const value = args[0]
	if (typeof value === "number" || value instanceof Date) {
		return dayjs.tz(value, STAFF_PRO_TIMEZONE)
	}
	if (typeof value === "string" && value && !hasExplicitOffset(value)) {
		return dayjs.tz(value, STAFF_PRO_TIMEZONE)
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
