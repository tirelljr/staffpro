import dayjs, { type ConfigType, type Dayjs } from "dayjs";
import updateLocale from "dayjs/plugin/updateLocale";
import localizedFormat from "dayjs/plugin/localizedFormat";
import isSameOrBefore from "dayjs/plugin/isSameOrBefore";
import isSameOrAfter from "dayjs/plugin/isSameOrAfter";
import customParseFormat from "dayjs/plugin/customParseFormat";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

export const STAFF_PRO_TIMEZONE = "America/Belize";

dayjs.extend(updateLocale);
dayjs.extend(localizedFormat);
dayjs.extend(isSameOrBefore);
dayjs.extend(isSameOrAfter);
dayjs.extend(customParseFormat);
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault(STAFF_PRO_TIMEZONE);

function hasExplicitOffset(value: string) {
	return /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value.trim());
}

function staffProDayjs(date?: ConfigType, format?: string, strict?: boolean): Dayjs {
	if (date === undefined) {
		return dayjs.tz();
	}
	if (typeof date === "number" || date instanceof Date) {
		return dayjs.tz(date, STAFF_PRO_TIMEZONE);
	}
	if (typeof date === "string" && date && !hasExplicitOffset(date)) {
		return format ? dayjs.tz(date, format, STAFF_PRO_TIMEZONE) : dayjs.tz(date, STAFF_PRO_TIMEZONE);
	}
	return dayjs(date, format, strict);
}

const wrapped = Object.assign(staffProDayjs, dayjs) as typeof dayjs;
export default wrapped;
