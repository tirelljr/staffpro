frappe.provide("hrms");

$.extend(hrms, {
	proceed_save_with_reminders_frequency_change: () => {
		frappe.ui.hide_open_dialog();
		frappe.call({
			method: "hrms.hr.doctype.hr_settings.hr_settings.set_proceed_with_frequency_change",
			callback: () => {
				// nosemgrep: frappe-semgrep-rules.rules.frappe-cur-frm-usage
				cur_frm.save();
			},
		});
	},

	set_payroll_frequency_to_null: (frm) => {
		if (cint(frm.doc.salary_slip_based_on_timesheet)) {
			frm.set_value("payroll_frequency", "");
		}
	},

	PAYROLL_FREQUENCY_LABELS: {
		Fortnightly: "2-weeks",
		Bimonthly: "Twice a Month",
	},

	payroll_frequency_label: (value) => {
		if (!value) return value || "";
		const mapped = hrms.PAYROLL_FREQUENCY_LABELS[value];
		return mapped ? __(mapped) : __(value);
	},

	relabel_payroll_frequency: (frm, fieldname = "payroll_frequency") => {
		const field = frm?.fields_dict?.[fieldname];
		const $input = field?.$input;
		if (!$input?.length) return;
		$input.find("option").each(function () {
			const $opt = $(this);
			const value = $opt.attr("value") || $opt.val();
			if (hrms.PAYROLL_FREQUENCY_LABELS[value]) {
				$opt.text(hrms.payroll_frequency_label(value));
			}
		});
	},

	get_current_employee: async (frm) => {
		const employee = (
			await frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name")
		)?.message?.name;

		return employee;
	},

	validate_mandatory_fields: (frm, selected_rows, items = "Employees") => {
		const missing_fields = [];
		for (d in frm.fields_dict) {
			if (frm.fields_dict[d].df.reqd && !frm.doc[d] && d !== "__newname")
				missing_fields.push(frm.fields_dict[d].df.label);
		}

		if (missing_fields.length) {
			let message = __("Mandatory fields required for this action:");
			message += "<br><br><ul><li>" + missing_fields.join("</li><li>") + "</ul>";
			frappe.throw({
				message: message,
				title: __("Missing Fields"),
			});
		}

		if (!selected_rows.length)
			frappe.throw({
				message: __("Please select at least one row to perform this action."),
				title: __("No {0} Selected", [__(items)]),
			});
	},

	setup_employee_filter_group: (frm) => {
		const filter_wrapper = frm.fields_dict.filter_list.$wrapper;
		filter_wrapper.empty();

		frappe.model.with_doctype("Employee", () => {
			frm.filter_list = new frappe.ui.FilterGroup({
				parent: filter_wrapper,
				doctype: "Employee",
				on_change: () => {
					frm.advanced_filters = frm.filter_list
						.get_filters()
						.reduce((filters, item) => {
							// item[3] is the value from the array [doctype, fieldname, condition, value]
							if (item[3]) {
								filters.push(item.slice(1, 4));
							}
							return filters;
						}, []);
					frm.trigger("get_employees");
				},
			});
		});
	},

	render_employees_datatable: (
		frm,
		columns,
		employees,
		no_data_message = __("No Data"),
		get_editor = null,
		events = {},
	) => {
		// section automatically collapses on applying a single filter
		frm.set_df_property("quick_filters_section", "collapsible", 0);
		frm.set_df_property("advanced_filters_section", "collapsible", 0);

		if (frm.employees_datatable) {
			frm.employees_datatable.rowmanager.checkMap = [];
			frm.employees_datatable.options.noDataMessage = no_data_message;
			frm.employees_datatable.refresh(employees, columns);
			return;
		}

		const $wrapper = frm.get_field("employees_html").$wrapper;
		const employee_wrapper = $(`<div class="employee_wrapper">`).appendTo($wrapper);
		const datatable_options = {
			columns: columns,
			data: employees,
			checkboxColumn: true,
			checkedRowStatus: false,
			serialNoColumn: false,
			dynamicRowHeight: true,
			inlineFilters: true,
			layout: "fluid",
			cellHeight: 35,
			noDataMessage: no_data_message,
			disableReorderColumn: true,
			getEditor: get_editor,
			events: events,
		};
		frm.employees_datatable = new frappe.DataTable(employee_wrapper.get(0), datatable_options);
	},

	handle_realtime_bulk_action_notification: (frm, event, doctype) => {
		frappe.realtime.off(event);
		frappe.realtime.on(event, (message) => {
			hrms.notify_bulk_action_status(
				doctype,
				message.failure,
				message.success,
				message.for_processing,
			);

			// refresh only on complete/partial success
			if (message.success) frm.refresh();
		});
	},

	notify_bulk_action_status: (doctype, failure, success, for_processing = false) => {
		let action = __("create/submit");
		let action_past = __("created");
		if (for_processing) {
			action = __("process");
			action_past = __("processed");
		}

		let message = "";
		let title = __("Success");
		let indicator = "green";

		if (failure.length) {
			message += __("Failed to {0} {1} for employees:", [action, doctype]);
			message += " " + frappe.utils.comma_and(failure) + "<hr>";
			message += __(
				"Check <a href='/app/List/Error Log?reference_doctype={0}'>{1}</a> for more details",
				[doctype, __("Error Log")],
			);
			title = __("Failure");
			indicator = "red";

			if (success.length) {
				message += "<hr>";
				title = __("Partial Success");
				indicator = "orange";
			}
		}

		if (success.length) {
			message += __("Successfully {0} {1} for the following employees:", [
				action_past,
				doctype,
			]);
			message += __(
				"<table class='table table-bordered'><tr><th>{0}</th><th>{1}</th></tr>",
				[__("Employee"), doctype],
			);
			for (const d of success) {
				message += `<tr><td>${d.employee}</td><td>${d.doc}</td></tr>`;
			}
			message += "</table>";
		}

		frappe.msgprint({
			message,
			title,
			indicator,
			is_minimizable: true,
		});
	},

	get_current_position: () => {
		return new Promise((resolve, reject) => {
			if (!navigator.geolocation) {
				reject({ unsupported: true });
				return;
			}

			navigator.geolocation.getCurrentPosition(
				(position) =>
					resolve({
						latitude: position.coords.latitude,
						longitude: position.coords.longitude,
					}),

				(error) => reject(error),
				{ timeout: 10000 },
			);
		});
	},

	get_geolocation_error_message: (error) => {
		if (error?.unsupported) {
			return __("Geolocation is not supported by your current browser");
		}

		if (error?.code === 1) {
			return __(
				"User denied location prompt. Please allow access to your location in your browser settings and try again.",
			);
		}

		if (error) {
			return __("ERROR({0}): {1}", [
				error.code,
				frappe.utils.escape_html(error.message || ""),
			]);
		}
		return __("An unknown error occurred while fetching your geolocation");
	},

	fetch_geolocation: async (frm) => {
		frappe.dom.freeze(__("Fetching your geolocation") + "...");

		try {
			const { latitude, longitude } = await hrms.get_current_position();
			await frappe.run_serially([
				() => frm.set_value("latitude", latitude),
				() => frm.set_value("longitude", longitude),
				() => frm.call("set_geolocation"),
			]);
		} catch (error) {
			if (error?.unsupported) hide_field(["geolocation"]);
			frappe.msgprint({
				message: hrms.get_geolocation_error_message(error),
				title: __("Geolocation Error"),
				indicator: "red",
			});
		} finally {
			frappe.dom.unfreeze();
		}
	},

	get_doctype_fields_for_autocompletion: (doctype) => {
		const fields = frappe.get_meta(doctype).fields;
		const autocompletions = [];

		fields
			.filter((df) => !frappe.model.no_value_type.includes(df.fieldtype))
			.map((df) => {
				autocompletions.push({
					value: df.fieldname,
					score: 8,
					meta: __("{0} Field", [doctype]),
				});
			});

		return autocompletions;
	},

	add_shift_tools_button_to_list: (list_view, action = "Assign Shift") => {
		list_view.page.add_inner_button(
			__("Shift Assignment Tool"),
			() => {
				const doc = frappe.model.get_new_doc("Shift Assignment Tool");
				doc.action = action;
				doc.company = frappe.defaults.get_default("company");
				doc.status = "Active";
				frappe.set_route("Form", "Shift Assignment Tool", doc.name);
			},
			__("Shift Tools"),
		);

		list_view.page.add_inner_button(
			__("Roster"),
			() => {
				window.location.href = "/hr/roster";
			},
			__("Shift Tools"),
		);
	},

	add_shift_tools_button_to_form: (frm, fields) => {
		frm.add_custom_button(
			__("Shift Assignment Tool"),
			() => {
				const doc = frappe.model.get_new_doc("Shift Assignment Tool");
				Object.assign(doc, fields);
				doc.company = frappe.defaults.get_default("company");
				doc.status = "Active";
				frappe.set_route("Form", "Shift Assignment Tool", doc.name);
			},
			__("Shift Tools"),
		);
		frm.add_custom_button(
			__("Roster"),
			() => {
				window.location.href = "/hr/roster";
			},
			__("Shift Tools"),
		);
	},
});

(function applyDesignationUiLabels() {
	const messagesToApply = {
		Designation: "Role",
		Designations: "Roles",
		"Add Designation": "Add Role",
		"New Designation": "New Role",
	};

	const applyMessages = () => {
		const messages = frappe._messages || frappe.boot?.__messages || {};
		Object.assign(messages, messagesToApply);
		frappe._messages = messages;
		if (frappe.boot) {
			frappe.boot.__messages = messages;
		}
	};

	const setListTitle = (list_view) => {
		if (!list_view?.page) return;
		const title = __("Roles");
		list_view.page_title = title;
		list_view.page.set_title(title);
	};

	const setListPrimaryAction = (list_view) => {
		if (!list_view?.page) return;
		const make_new = list_view.make_new_doc?.bind(list_view);
		list_view.set_primary_action = () => {
			const can_add =
				!frappe.boot?.read_only &&
				(frappe.model.can_create?.("Designation") || list_view.can_create);
			if (can_add && make_new) {
				list_view.page.set_primary_action(__("Add Role"), () => make_new());
			} else {
				list_view.page.clear_primary_action();
			}
		};
		list_view.set_primary_action();
	};

	const relabelDesignationForm = (frm) => {
		if (!frm?.page) return;
		if (frm.is_new()) {
			frm.page.set_title(__("New Role"));
		}
		if (frm.fields_dict?.designation_name) {
			frm.set_df_property("designation_name", "label", __("Role"));
		}
	};

	const relabelDesignationModal = ($modal) => {
		const $title = $modal.find(".title-section, .modal-title").first();
		const title = ($title.text() || "").replace(/\s+/g, " ").trim();
		if (!/designation/i.test(title) && title !== __("New Role")) return;

		$modal.find(".title-section, .modal-title").each(function () {
			const text = ($(this).text() || "").replace(/\s+/g, " ").trim();
			if (/designation/i.test(text)) {
				$(this).text(text.replace(/Designation/gi, __("Role")));
			}
		});
		$modal.find("label.control-label").each(function () {
			const $label = $(this);
			if (($label.text() || "").replace(/\s+/g, " ").trim() === "Designation") {
				$label.text(__("Role"));
			}
		});
	};

	applyMessages();

	frappe.ui.form.on("Designation", {
		onload(frm) {
			relabelDesignationForm(frm);
		},
		refresh(frm) {
			relabelDesignationForm(frm);
		},
	});

	$(document).on("shown.bs.modal", ".modal", function () {
		relabelDesignationModal($(this));
	});

	const installList = () => {
		applyMessages();
		const existing = frappe.listview_settings.Designation || {};
		const existing_onload = existing.onload;
		const existing_refresh = existing.refresh;
		frappe.listview_settings.Designation = Object.assign({}, existing, {
			onload(list_view) {
				existing_onload?.(list_view);
				setListTitle(list_view);
				setListPrimaryAction(list_view);
			},
			refresh(list_view) {
				existing_refresh?.(list_view);
				setListTitle(list_view);
				list_view.set_primary_action?.();
			},
		});
	};

	if (typeof frappe.ready === "function") {
		frappe.ready(installList);
	} else {
		installList();
	}
})();

(function applyPayrollFrequencyUiLabels() {
	const applyMessages = () => {
		const label = "2-weeks";
		const messages = frappe._messages || frappe.boot?.__messages || {};
		messages.Fortnightly = label;
		messages["2 Weeks"] = label;
		frappe._messages = messages;
		if (frappe.boot) {
			frappe.boot.__messages = messages;
		}
	};
	applyMessages();

	const forms = [
		["Payroll Entry", "payroll_frequency"],
		["Salary Structure", "payroll_frequency"],
		["Salary Slip", "payroll_frequency"],
		["Salary Withholding", "payroll_frequency"],
		["Payroll Settings", "automatic_payroll_frequency"],
	];
	forms.forEach(([doctype, fieldname]) => {
		frappe.ui.form.on(doctype, {
			onload(frm) {
				hrms.relabel_payroll_frequency(frm, fieldname);
			},
			refresh(frm) {
				hrms.relabel_payroll_frequency(frm, fieldname);
			},
		});
	});

	const installListFormatters = () => {
		applyMessages();
		["Payroll Entry", "Salary Slip", "Salary Structure", "Salary Withholding"].forEach((doctype) => {
			const existing = frappe.listview_settings[doctype] || {};
			existing.formatters = Object.assign({}, existing.formatters, {
				payroll_frequency(value) {
					return hrms.payroll_frequency_label(value);
				},
			});
			frappe.listview_settings[doctype] = existing;
		});
	};
	if (typeof frappe.ready === "function") {
		frappe.ready(installListFormatters);
	} else {
		installListFormatters();
	}
})();

hrms.relabel_form_dashboard_links = function (frm) {
	const $page = frm?.page?.wrapper || frm?.$wrapper;
	if (!$page?.length) {
		return;
	}

	const doctype_labels = {
		"Employee Grade": __("Campaign"),
		Designation: __("Role"),
	};

	$page.find(".document-link").each(function () {
		const doctype = $(this).attr("data-doctype");
		const label = doctype_labels[doctype];
		if (label) {
			$(this).text(label);
		}
	});
};

(function applyEmployeeGradeUiLabels() {
	const messagesToApply = {
		"Employee Grade": "Campaign",
		"Employee Grades": "Campaigns",
		"Add Employee Grade": "Add Campaign",
		"New Employee Grade": "New Campaign",
	};

	const applyMessages = () => {
		const messages = frappe._messages || frappe.boot?.__messages || {};
		Object.assign(messages, messagesToApply);
		frappe._messages = messages;
		if (frappe.boot) {
			frappe.boot.__messages = messages;
		}
	};

	const setListTitle = (list_view) => {
		if (!list_view?.page) return;
		const title = __("Campaigns");
		list_view.page_title = title;
		list_view.page.set_title(title);
	};

	const setListPrimaryAction = (list_view) => {
		if (!list_view?.page) return;
		const make_new = list_view.make_new_doc?.bind(list_view);
		list_view.set_primary_action = () => {
			const can_add =
				!frappe.boot?.read_only &&
				(frappe.model.can_create?.("Employee Grade") || list_view.can_create);
			if (can_add && make_new) {
				list_view.page.set_primary_action(__("Add Campaign"), () => make_new());
			} else {
				list_view.page.clear_primary_action();
			}
		};
		list_view.set_primary_action();
	};

	const relabelEmployeeGradeForm = (frm) => {
		if (!frm?.page) return;
		if (frm.is_new()) {
			frm.page.set_title(__("New Campaign"));
		}
	};

	applyMessages();

	frappe.ui.form.on("Employee Grade", {
		onload(frm) {
			relabelEmployeeGradeForm(frm);
		},
		refresh(frm) {
			relabelEmployeeGradeForm(frm);
			hrms.relabel_form_dashboard_links(frm);
		},
	});

	frappe.ui.form.on("Salary Structure", {
		refresh(frm) {
			hrms.relabel_form_dashboard_links(frm);
		},
	});

	const installList = () => {
		applyMessages();
		const existing = frappe.listview_settings["Employee Grade"] || {};
		const existing_onload = existing.onload;
		const existing_refresh = existing.refresh;
		frappe.listview_settings["Employee Grade"] = Object.assign({}, existing, {
			onload(list_view) {
				existing_onload?.(list_view);
				setListTitle(list_view);
				setListPrimaryAction(list_view);
			},
			refresh(list_view) {
				existing_refresh?.(list_view);
				setListTitle(list_view);
				list_view.set_primary_action?.();
			},
		});
	};

	if (typeof frappe.ready === "function") {
		frappe.ready(installList);
	} else {
		installList();
	}
})();
