frappe.provide("hrms.ui");

frappe.pages["floor-map"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Floor"),
		single_column: true,
	});

	frappe.breadcrumbs.add("HR");
	frappe.floor_map.make(page);
};

frappe.pages["floor-map"].on_page_show = function () {
	frappe.floor_map.refresh();
};

frappe.floor_map = {
	page: null,
	$body: null,
	payload: null,
	office_floor: "",
	query: "",
	dragging: null,
	suppress_click: false,

	make(page) {
		this.page = page;
		const $existing = page.main.find(".sp-floor-page");
		if ($existing.length && $existing.find(".sp-floor-grid").length) {
			this.$body = $existing;
			this.refresh();
			return;
		}
		$existing.remove();
		this.$body = $('<div class="sp-floor-page"></div>').appendTo(page.main);
		this.render_shell();
		this.bind();
		this.refresh();
	},

	escape(value) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
	},

	short_name(name) {
		const parts = String(name || "")
			.trim()
			.split(/\s+/)
			.filter(Boolean);
		if (!parts.length) {
			return "";
		}
		if (parts.length === 1) {
			return parts[0];
		}
		return `${parts[0][0]}. ${parts[parts.length - 1]}`;
	},

	avatar(row) {
		if (row.image) {
			return `<img class="sp-celebrations__avatar-img" src="${this.escape(row.image)}" alt="">`;
		}
		const initials = String(row.employee_name || row.employee || "")
			.trim()
			.split(/\s+/)
			.slice(0, 2)
			.map((part) => part[0] || "")
			.join("")
			.toUpperCase();
		return `<span class="sp-celebrations__avatar-fallback">${this.escape(initials || "+")}</span>`;
	},

	select_html(className, variant, label, options, value) {
		if (hrms.ui && typeof hrms.ui.dash_select_html === "function") {
			return hrms.ui.dash_select_html({ className, variant, label, options, value });
		}
		const selected = options.find((opt) => opt.value === value) || options[0];
		return `
			<select class="${this.escape(className)} sp-dash-panel__select sp-dash-panel__select--${this.escape(variant)}" aria-label="${this.escape(label)}">
				${options
					.map(
						(opt) =>
							`<option value="${this.escape(opt.value)}"${opt.value === selected.value ? " selected" : ""}>${this.escape(opt.label)}</option>`,
					)
					.join("")}
			</select>`;
	},

	render_shell() {
		this.$body.html(`
			<section class="sp-floor" aria-label="${this.escape(__("Floor"))}">
				<header class="sp-floor__toolbar">
					<h1 class="sp-floor__title">${this.escape(__("Floor"))}</h1>
					<div class="sp-floor__controls">
						<label class="sp-floor__search">
							<span class="sr-only">${this.escape(__("Search"))}</span>
							<input type="search" class="sp-floor__search-input" placeholder="${this.escape(__("Search people, devices, IP"))}" />
						</label>
						<div class="sp-floor__filter">
							${this.select_html("sp-floor__floor-select", "outline", __("Floor"), [{ value: "", label: __("Select floor") }], "")}
						</div>
						<button type="button" class="sp-floor__btn sp-floor__generate">${this.escape(__("Generate rows"))}</button>
						<button type="button" class="sp-floor__btn sp-floor__btn--solid sp-floor__refresh">${this.escape(__("Refresh"))}</button>
					</div>
				</header>
				<div class="sp-floor__totals" aria-live="polite"></div>
				<div class="sp-floor-grid"></div>
			</section>
		`);
		if (hrms.ui && typeof hrms.ui.bind_dash_selects === "function") {
			hrms.ui.bind_dash_selects(this.$body);
		}
	},

	bind() {
		const me = this;
		this.$body.on("click", ".sp-floor__refresh", () => me.refresh());
		this.$body.on("input", ".sp-floor__search-input", function () {
			me.query = String($(this).val() || "").trim().toLowerCase();
			me.render_grid();
		});
		this.$body.on("change", ".sp-floor__floor-select", function () {
			me.office_floor = $(this).val() || "";
			me.refresh();
		});
		this.$body.on("click", ".sp-floor__generate", () => me.open_generate());
		this.$body.on("click", ".sp-floor-seat", function (e) {
			if (me.suppress_click || $(e.target).closest(".sp-floor-seat__remove").length) {
				return;
			}
			const name = $(this).data("cubicle");
			if (name) {
				me.open_assign(name);
			}
		});
		this.$body.on("click", ".sp-floor-seat__remove", function (e) {
			e.preventDefault();
			e.stopPropagation();
			me.delete_seat($(this).closest(".sp-floor-seat").data("cubicle"));
		});
		this.$body.on("mousedown dragstart", ".sp-floor-seat__remove", function (e) {
			e.stopPropagation();
		});
		this.$body.on("keydown", ".sp-floor-seat", function (e) {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				$(this).trigger("click");
			}
		});
		this.$body.on("click", ".sp-floor-row__add", function (e) {
			e.preventDefault();
			e.stopPropagation();
			me.add_seat($(this).data("row"));
		});
		this.bind_drag();
		this.bind_scroll_sync();
	},

	bind_scroll_sync() {
		const me = this;
		this.$body.on("scroll.floor", ".sp-floor-scroll", function () {
			const source = this;
			const left = source.scrollLeft;
			me.$body.find(".sp-floor-scroll").each(function () {
				if (this !== source && this.scrollLeft !== left) {
					this.scrollLeft = left;
				}
			});
		});
		this.$body.on("wheel.floor", ".sp-floor-scroll", function (e) {
			const original = e.originalEvent;
			if (!original || Math.abs(original.deltaY) < Math.abs(original.deltaX)) {
				return;
			}
			if (this.scrollWidth <= this.clientWidth) {
				return;
			}
			this.scrollLeft += original.deltaY;
			e.preventDefault();
			$(this).trigger("scroll");
		});
	},

	bind_drag() {
		const me = this;
		this.$body.on("dragstart", ".sp-floor-seat.is-occupied", function (e) {
			const name = $(this).data("cubicle");
			if (!name) {
				return;
			}
			me.dragging = name;
			me.suppress_click = false;
			$(this).addClass("is-dragging");
			const transfer = e.originalEvent?.dataTransfer;
			if (transfer) {
				transfer.effectAllowed = "move";
				transfer.setData("text/plain", name);
			}
		});
		this.$body.on("dragend", ".sp-floor-seat", function () {
			$(this).removeClass("is-dragging");
			me.$body.find(".sp-floor-seat").removeClass("is-drop-target");
			if (me.dragging) {
				me.suppress_click = true;
				setTimeout(() => {
					me.suppress_click = false;
				}, 150);
			}
			me.dragging = null;
		});
		this.$body.on("dragover", ".sp-floor-seat:not(.is-missing)", function (e) {
			if (!me.dragging || $(this).data("cubicle") === me.dragging) {
				return;
			}
			e.preventDefault();
			const transfer = e.originalEvent?.dataTransfer;
			if (transfer) {
				transfer.dropEffect = "move";
			}
			me.$body.find(".sp-floor-seat").removeClass("is-drop-target");
			$(this).addClass("is-drop-target");
		});
		this.$body.on("dragleave", ".sp-floor-seat", function () {
			$(this).removeClass("is-drop-target");
		});
		this.$body.on("drop", ".sp-floor-seat:not(.is-missing)", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const target = $(this).data("cubicle");
			const source = me.dragging || e.originalEvent?.dataTransfer?.getData("text/plain");
			me.$body.find(".sp-floor-seat").removeClass("is-drop-target is-dragging");
			me.dragging = null;
			me.suppress_click = true;
			setTimeout(() => {
				me.suppress_click = false;
			}, 150);
			if (source && target && source !== target) {
				me.move_assignment(source, target);
			}
		});
	},

	floor_options(payload) {
		const options = (payload.floors || []).map((row) => ({
			value: row.name,
			label: row.floor_name || row.name,
		}));
		if (!options.length) {
			options.push({ value: "", label: __("No floors yet") });
		}
		return options;
	},

	set_floor_options(payload) {
		const $select = this.$body.find(".sp-floor__floor-select");
		const options = this.floor_options(payload);
		if (hrms.ui && typeof hrms.ui.set_dash_select_options === "function") {
			this.office_floor = hrms.ui.set_dash_select_options($select, options) || payload.office_floor || "";
			if (payload.office_floor) {
				$select.val(payload.office_floor);
				this.office_floor = payload.office_floor;
			}
			return;
		}
		const selected = payload.office_floor || options[0]?.value || "";
		$select.html(
			options
				.map(
					(opt) =>
						`<option value="${this.escape(opt.value)}"${opt.value === selected ? " selected" : ""}>${this.escape(opt.label)}</option>`,
				)
				.join(""),
		);
		$select.val(selected);
		this.office_floor = selected;
	},

	refresh() {
		const me = this;
		if (!this.$body) {
			return;
		}
		const $grid = this.$body.find(".sp-floor-grid");
		$grid.addClass("is-loading");
		frappe.call({
			method: "hrms.hr.page.floor_map.floor_map.get_floor_map",
			args: { office_floor: this.office_floor || undefined },
			callback(r) {
				$grid.removeClass("is-loading");
				me.payload = r.message || { floors: [], seats: [], rows: [], totals: {} };
				me.set_floor_options(me.payload);
				me.render_totals();
				me.render_grid();
			},
			error() {
				$grid.removeClass("is-loading");
				me.payload = { floors: [], seats: [], rows: [], totals: {} };
				me.$body.find(".sp-floor__totals").empty();
				$grid.html(me.empty_html(__("Could not load the floor map.")));
			},
		});
	},

	to_int(value) {
		const n = parseInt(value, 10);
		return Number.isFinite(n) ? n : 0;
	},

	render_totals() {
		const totals = this.payload?.totals || {};
		this.$body.find(".sp-floor__totals").html(`
			<span><strong>${this.escape(__("Seats"))}:</strong> ${this.to_int(totals.total)}</span>
			<span><strong>${this.escape(__("Occupied"))}:</strong> ${this.to_int(totals.occupied)}</span>
			<span><strong>${this.escape(__("Vacant"))}:</strong> ${this.to_int(totals.vacant)}</span>
		`);
	},

	matches_query(cubicle) {
		if (!this.query) {
			return true;
		}
		const haystack = [
			cubicle.employee_name,
			cubicle.employee,
			cubicle.device_id,
			cubicle.ip_address,
			cubicle.row,
			cubicle.seat_number,
			cubicle.name,
		]
			.map((value) => String(value || "").toLowerCase())
			.join(" ");
		return haystack.includes(this.query);
	},

	empty_html(message) {
		return `
			<div class="sp-floor__empty">
				<p>${this.escape(message)}</p>
			</div>
		`;
	},

	cubicle_for_seat(row, seat) {
		return (row.cubicles || []).find((item) => this.to_int(item.seat_number) === this.to_int(seat)) || null;
	},

	seat_html(cubicle) {
		if (!cubicle) {
			return `<div class="sp-floor-seat is-missing" aria-hidden="true"></div>`;
		}
		const occupied = Boolean(cubicle.employee);
		const visible = this.matches_query(cubicle);
		const device = cubicle.device_id || cubicle.ip_address;
		const remove = `
			<button type="button" class="sp-floor-seat__remove" draggable="false" title="${this.escape(__("Delete seat"))}" aria-label="${this.escape(__("Delete seat {0}", [cubicle.seat_number]))}">×</button>
		`;
		if (!occupied) {
			return `
				<div class="sp-floor-seat is-vacant${visible ? "" : " is-dimmed"}" data-cubicle="${this.escape(cubicle.name)}" role="button" tabindex="0" aria-label="${this.escape(__("Assign seat {0}", [cubicle.seat_number]))}">
					<span class="sp-floor-seat__num">${this.escape(String(cubicle.seat_number).padStart(2, "0"))}</span>
					<span class="sp-floor-seat__plus">+</span>
					${remove}
				</div>
			`;
		}
		const meta = [cubicle.device_id, cubicle.ip_address].filter(Boolean).join(" · ");
		return `
			<div class="sp-floor-seat is-occupied${visible ? "" : " is-dimmed"}" data-cubicle="${this.escape(cubicle.name)}" draggable="true" role="button" tabindex="0" aria-label="${this.escape(cubicle.employee_name || cubicle.employee)}">
				<span class="sp-floor-seat__num">${this.escape(String(cubicle.seat_number).padStart(2, "0"))}</span>
				<span class="sp-floor-seat__pill">
					<span class="sp-floor-seat__avatar">${this.avatar(cubicle)}</span>
					<span class="sp-floor-seat__meta">
						<span class="sp-floor-seat__name">${this.escape(this.short_name(cubicle.employee_name || cubicle.employee))}</span>
						${device ? `<span class="sp-floor-seat__device">${this.escape(meta)}</span>` : ""}
					</span>
				</span>
				${remove}
			</div>
		`;
	},

	render_grid() {
		const $grid = this.$body.find(".sp-floor-grid");
		const payload = this.payload || {};
		if (!(payload.floors || []).length) {
			$grid.html(
				this.empty_html(__("Add an Office Floor, then generate cubicle rows to see who sits where.")),
			);
			return;
		}
		if (!(payload.rows || []).length) {
			$grid.html(this.empty_html(__("No cubicles on this floor yet. Use Generate rows to add seats.")));
			return;
		}

		const seats = payload.seats || [];
		const header = `
			<div class="sp-floor-grid__head">
				<span class="sp-floor-grid__row-label">${this.escape(__("Row"))}</span>
				<div class="sp-floor-scroll">
					<div class="sp-floor-row__seats">
						${seats.map((seat) => `<span class="sp-floor-grid__col">${this.escape(String(seat).padStart(2, "0"))}</span>`).join("")}
						<span class="sp-floor-grid__col is-action"></span>
					</div>
				</div>
			</div>
		`;
		const groups = (payload.rows || [])
			.map((row) => {
				const cells = seats.map((seat) => this.seat_html(this.cubicle_for_seat(row, seat))).join("");
				return `
					<article class="sp-floor-row" data-row="${this.escape(row.row)}" aria-label="${this.escape(__("Row {0}", [row.row]))}">
						<div class="sp-floor-row__label">
							<span class="sp-floor-row__dot"></span>
							<strong>${this.escape(__("Row {0}", [row.row]))}</strong>
						</div>
						<div class="sp-floor-scroll">
							<div class="sp-floor-row__seats">
								${cells}
								<button type="button" class="sp-floor-row__add" data-row="${this.escape(row.row)}" title="${this.escape(__("Add seat"))}">
									${this.escape(__("Add seat"))}
								</button>
							</div>
						</div>
					</article>
				`;
			})
			.join("");

		$grid.html(`${header}<div class="sp-floor-grid__body">${groups}</div>`);
	},

	find_cubicle(name) {
		for (const row of this.payload?.rows || []) {
			const match = (row.cubicles || []).find((item) => item.name === name);
			if (match) {
				return match;
			}
		}
		return null;
	},

	open_generate() {
		if (!this.office_floor) {
			frappe.msgprint(__("Create an Office Floor first."));
			return;
		}
		const me = this;
		const dialog = new frappe.ui.Dialog({
			title: __("Generate Cubicle Rows"),
			fields: [
				{ fieldname: "row_count", fieldtype: "Int", label: __("Number of Rows"), reqd: 1, default: 4 },
				{ fieldname: "seats_per_row", fieldtype: "Int", label: __("Seats per Row"), reqd: 1, default: 8 },
			],
			primary_action_label: __("Generate"),
			primary_action(values) {
				frappe.call({
					method: "hrms.hr.doctype.office_floor.office_floor.generate_layout",
					args: {
						office_floor: me.office_floor,
						row_count: values.row_count,
						seats_per_row: values.seats_per_row,
					},
					freeze: true,
					callback(r) {
						frappe.show_alert({
							message: __("Added {0} cubicle(s)", [r.message?.created || 0]),
							indicator: "green",
						});
						dialog.hide();
						me.refresh();
					},
				});
			},
		});
		dialog.show();
	},

	open_assign(name) {
		const cubicle = this.find_cubicle(name);
		if (!cubicle) {
			return;
		}
		const me = this;
		const dialog = new frappe.ui.Dialog({
			title: cubicle.employee
				? __("Seat {0}{1}", [cubicle.row, String(cubicle.seat_number).padStart(2, "0")])
				: __("Assign seat {0}{1}", [cubicle.row, String(cubicle.seat_number).padStart(2, "0")]),
			fields: [
				{
					fieldname: "employee",
					fieldtype: "Link",
					label: __("Employee"),
					options: "Employee",
					default: cubicle.employee || "",
					get_query() {
						return { filters: { status: "Active" } };
					},
					onchange() {
						me.fill_workstation_defaults(dialog, cubicle);
					},
				},
				{
					fieldname: "device_id",
					fieldtype: "Data",
					label: __("Device ID"),
					default: cubicle.device_id || "",
				},
				{
					fieldname: "ip_address",
					fieldtype: "Data",
					label: __("IP Address"),
					default: cubicle.ip_address || "",
				},
			],
			primary_action_label: __("Save"),
			primary_action(values) {
				frappe.call({
					method: "hrms.hr.page.floor_map.floor_map.assign_cubicle",
					args: {
						cubicle: cubicle.name,
						employee: values.employee || "",
						device_id: values.device_id || "",
						ip_address: values.ip_address || "",
						clear: values.employee ? 0 : 1,
					},
					freeze: true,
					callback() {
						dialog.hide();
						me.refresh();
					},
				});
			},
		});
		if (cubicle.employee) {
			dialog.set_secondary_action_label(__("Clear seat"));
			dialog.set_secondary_action(() => {
				frappe.call({
					method: "hrms.hr.page.floor_map.floor_map.assign_cubicle",
					args: { cubicle: cubicle.name, clear: 1 },
					freeze: true,
					callback() {
						dialog.hide();
						me.refresh();
					},
				});
			});
		}
		dialog.show();
		this.fill_workstation_defaults(dialog, cubicle);
		dialog.$wrapper.find(".modal-footer").prepend(
			$(`<button type="button" class="btn btn-danger btn-sm">${__("Delete seat")}</button>`).on("click", () => {
				dialog.hide();
				me.delete_seat(cubicle.name);
			}),
		);
	},

	fill_workstation_defaults(dialog, cubicle) {
		const employee = dialog.get_value("employee");
		if (!employee) {
			return;
		}
		frappe.call({
			method: "hrms.hr.page.floor_map.floor_map.get_employee_workstation",
			args: { employee },
			callback(r) {
				const data = r.message || {};
				if (data.device_id && !(dialog.get_value("device_id") || cubicle.device_id)) {
					dialog.set_value("device_id", data.device_id);
				}
				if (data.ip_address && !(dialog.get_value("ip_address") || cubicle.ip_address)) {
					dialog.set_value("ip_address", data.ip_address);
				}
			},
		});
	},

	add_seat(row) {
		if (!this.office_floor || !row) {
			return;
		}
		const me = this;
		frappe.call({
			method: "hrms.hr.page.floor_map.floor_map.add_seat",
			args: { office_floor: this.office_floor, row },
			freeze: true,
			callback() {
				frappe.show_alert({ message: __("Seat added to row {0}", [row]), indicator: "green" });
				me.refresh();
			},
		});
	},

	delete_seat(name) {
		const cubicle = this.find_cubicle(name);
		if (!cubicle) {
			return;
		}
		const me = this;
		const label = `${cubicle.row}${String(cubicle.seat_number).padStart(2, "0")}`;
		const message = cubicle.employee
			? __("Delete seat {0} and unassign {1}?", [label, cubicle.employee_name || cubicle.employee])
			: __("Delete seat {0}?", [label]);
		frappe.confirm(message, () => {
			frappe.call({
				method: "hrms.hr.page.floor_map.floor_map.delete_seat",
				args: { cubicle: cubicle.name },
				freeze: true,
				callback() {
					frappe.show_alert({ message: __("Seat deleted"), indicator: "green" });
					me.refresh();
				},
			});
		});
	},

	move_assignment(source, target) {
		const me = this;
		frappe.call({
			method: "hrms.hr.page.floor_map.floor_map.move_assignment",
			args: { source, target },
			freeze: true,
			callback() {
				me.refresh();
			},
		});
	},
};
