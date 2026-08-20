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
	},
	get_css_class: function (data) {
		if (data.doctype === "Holiday") return "default";
		else if (data.doctype === "Attendance") {
			if (data.status === "Absent" || data.status === "On Leave") {
				return "danger";
			}
			if (data.status === "Half Day") return "warning";
			return "success";
		}
	},
	options: {
		header: {
			left: "prev,next today",
			center: "title",
			right: "month,agendaWeek",
		},
		select: function (info) {
			const start = info?.start;
			const end = info?.end;
			const opts = {
				attendance_date: start
					? moment(start).format("YYYY-MM-DD")
					: frappe.datetime.get_today(),
			};
			const seconds = start && end ? end - start : 0;
			if (start && seconds !== 86400000) {
				opts.in_time = moment(start).format("HH:mm:ss");
				if (end) {
					opts.out_time = moment(end).format("HH:mm:ss");
				}
			}
			hrms.time.show_add_entry_dialog?.(cur_list, opts);
			cur_list?.calendar?.fullCalendar?.unselect?.();
		},
	},
	get_events_method: "hrms.hr.doctype.attendance.attendance.get_events",
};
