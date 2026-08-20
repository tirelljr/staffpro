frappe.listview_settings["Attendance"] = {
	add_fields: [
		"status",
		"attendance_date",
		"employee_name",
		"in_time",
		"out_time",
		"working_hours",
		"daily_pay",
		"shift",
	],
	hide_name_column: true,

	primary_action: function () {
		if (hrms.time?.open_add_attendance) {
			hrms.time.open_add_attendance();
		}
	},

	get_indicator: function (doc) {
		if (["Present", "Work From Home"].includes(doc.status)) {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (["Absent", "On Leave"].includes(doc.status)) {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (doc.status == "Half Day") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		}
	},

	formatters: {
		in_time(value) {
			return hrms.time?.format_clock ? hrms.time.format_clock(value) : value;
		},
		out_time(value) {
			return hrms.time?.format_clock ? hrms.time.format_clock(value) : value;
		},
		working_hours(value) {
			return hrms.time?.format_hours ? hrms.time.format_hours(value) : value;
		},
	},

	onload: function (list_view) {
		if (hrms.time?.setup_range_filters) {
			hrms.time.setup_range_filters(list_view, {
				date_field: "attendance_date",
				department_field: "department",
			});
		}

		if (frappe.perm.has_perm("Attendance", 0, "create")) {
			const open_entry = () => hrms.time.show_add_entry_dialog(list_view);
			list_view.make_new_doc = open_entry;
			list_view.set_primary_action = () => {
				if (list_view.can_create && !frappe.boot.read_only) {
					list_view.page.set_primary_action(__("Add Attendance"), open_entry);
				} else {
					list_view.page.clear_primary_action();
				}
			};
			list_view.set_primary_action();
			list_view.page.add_inner_button(__("Add Absence"), () =>
				hrms.time.show_add_absence_dialog(list_view),
			);
			list_view.page.add_inner_button(__("Mark Attendance"), function () {
				let first_day_of_month = moment().startOf("month");

				if (moment().toDate().getDate() === 1) {
					first_day_of_month = first_day_of_month.subtract(1, "month");
				}

				let dialog = new frappe.ui.Dialog({
					title: __("Mark Attendance"),
					fields: [
						{
							fieldname: "employee",
							label: __("For Employee"),
							fieldtype: "Link",
							options: "Employee",
							get_query: () => {
								return {
									query: "erpnext.controllers.queries.employee_query",
								};
							},
							reqd: 1,
							onchange: () => frappe.listview_settings["Attendance"].reset_dialog(dialog),
						},
						{
							fieldtype: "Section Break",
							fieldname: "time_period_section",
							hidden: 1,
						},
						{
							label: __("Start"),
							fieldtype: "Date",
							fieldname: "from_date",
							reqd: 1,
							default: frappe.datetime.obj_to_str(first_day_of_month),
							onchange: () => frappe.listview_settings["Attendance"].get_unmarked_days(dialog),
						},
						{
							label: __("Status"),
							fieldtype: "Select",
							fieldname: "status",
							options: ["Present", "Absent", "Half Day", "Work From Home"],
							reqd: 1,
						},
						{
							fieldtype: "Column Break",
							fieldname: "time_period_column",
						},
						{
							label: __("End"),
							fieldtype: "Date",
							fieldname: "to_date",
							reqd: 1,
							default: frappe.datetime.obj_to_str(moment()),
							onchange: () => frappe.listview_settings["Attendance"].get_unmarked_days(dialog),
						},
						{
							label: __("Shift"),
							fieldtype: "Link",
							fieldname: "shift",
							options: "Shift Type",
						},
						{
							fieldtype: "Section Break",
							fieldname: "days_section",
							hidden: 1,
						},
						{
							label: __("Exclude Holidays"),
							fieldtype: "Check",
							fieldname: "exclude_holidays",
							onchange: () => frappe.listview_settings["Attendance"].get_unmarked_days(dialog),
						},
						{
							label: __("Unmarked Attendance for days"),
							fieldname: "unmarked_days",
							fieldtype: "MultiCheck",
							options: [],
							columns: 2,
							select_all: true,
						},
					],
					primary_action(data) {
						if (cur_dialog.no_unmarked_days_left) {
							frappe.msgprint(
								__(
									"Attendance from {0} to {1} has already been marked for the Employee {2}",
									[data.from_date, data.to_date, data.employee],
								),
							);
						} else {
							frappe.confirm(
								__("Mark attendance as {0} for {1} on selected dates?", [
									data.status,
									data.employee,
								]),
								() => {
									frappe.call({
										method: "hrms.hr.doctype.attendance.attendance.mark_bulk_attendance",
										args: {
											data: data,
										},
									});
								},
							);
						}
						dialog.hide();
						list_view.refresh();
					},
					primary_action_label: __("Mark Attendance"),
				});
				dialog.show();
			});
		}
	},

	refresh: function (list_view) {
		if (hrms.time?.refresh_hours_totals) {
			hrms.time.refresh_hours_totals(list_view);
		}
	},

	reset_dialog: function (dialog) {
		let fields = dialog.fields_dict;

		dialog.set_df_property("time_period_section", "hidden", fields.employee.value ? 0 : 1);
		dialog.set_df_property("days_section", "hidden", 1);
		dialog.set_df_property("unmarked_days", "options", []);
		dialog.no_unmarked_days_left = false;
		fields.exclude_holidays.value = false;

		fields.to_date.datepicker.update({
			maxDate: moment().toDate(),
		});

		this.get_unmarked_days(dialog);
	},

	get_unmarked_days: function (dialog) {
		let fields = dialog.fields_dict;
		if (fields.employee.value && fields.from_date.value && fields.to_date.value) {
			dialog.set_df_property("days_section", "hidden", 0);
			dialog.set_df_property("status", "hidden", 0);
			dialog.set_df_property("exclude_holidays", "hidden", 0);
			dialog.no_unmarked_days_left = false;

			frappe
				.call({
					method: "hrms.hr.doctype.attendance.attendance.get_unmarked_days",
					async: false,
					args: {
						employee: fields.employee.value,
						from_date: fields.from_date.value,
						to_date: fields.to_date.value,
						exclude_holidays: fields.exclude_holidays.value,
					},
				})
				.then((r) => {
					var options = [];

					for (var d in r.message) {
						var momentObj = moment(r.message[d], "YYYY-MM-DD");
						var date = momentObj.format("DD-MM-YYYY");
						options.push({
							label: date,
							value: r.message[d],
							checked: 1,
						});
					}

					dialog.set_df_property(
						"unmarked_days",
						"options",
						options.length > 0 ? options : [],
					);
					dialog.no_unmarked_days_left = options.length === 0;
				});
		}
	},
};
