// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.views.calendar["Attendance"] = {
	field_map: {
		start: "attendance_date",
		end: "attendance_date",
		id: "name",
		title: "title",
		allDay: "allDay",
		color: "color",
		employee: "employee",
		employee_name: "employee_name",
		image: "image",
		department: "department",
		status: "status",
		in_time: "in_time",
		out_time: "out_time",
		doctype: "doctype",
		late_entry: "late_entry",
	},
	get_css_class: function (data) {
		if (data.doctype === "Holiday") return "default";
		return "green";
	},
	options: {
		displayEventTime: false,
		dayMaxEvents: false,
		dateClick(info) {
			hrms.attendance_calendar?.show_day_roster?.(
				info.dateStr || moment(info.date).format("YYYY-MM-DD"),
			);
		},
		eventClick(info) {
			info.jsEvent?.preventDefault?.();
			info.jsEvent?.stopPropagation?.();
			const start = info.event.start || info.event.startStr;
			hrms.attendance_calendar?.show_day_roster?.(moment(start).format("YYYY-MM-DD"));
		},
		select(info) {
			if (hrms.attendance_calendar?.is_day_select?.(info)) {
				hrms.attendance_calendar.show_day_roster(moment(info.start).format("YYYY-MM-DD"));
				cur_list?.calendar?.fullCalendar?.unselect?.();
				return;
			}
			hrms.attendance_calendar?.open_add_entry?.(info);
		},
	},
	get_events_method: "hrms.hr.doctype.attendance.attendance.get_events",
};
