frappe.provide("hrms");

const AFS_FOLDER_COLORS = ["#ddd6fe", "#bfdbfe", "#fde68a", "#e9d5ff", "#bbf7d0", "#fecdd3", "#fed7aa"];
const AFS_PAGE_SIZE = 8;

frappe.pages["agent-filesystem"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Filesystem"),
		single_column: true,
	});
	frappe.breadcrumbs.add("HR");
	hrms.agent_filesystem.make(page);
};

frappe.pages["agent-filesystem"].on_page_show = function () {
	hrms.agent_filesystem.refresh();
};

hrms.agent_filesystem = {
	page: null,
	$body: null,
	agents: [],
	categories: [],
	folder_categories: [],
	files: [],
	search: "",
	agent_filter: "",
	type_filter: "",
	layout: "list",
	page_index: 0,
	employee: "",
	employee_name: "",
	category: "",
	category_name: "",
	loading: false,
	_mounting: false,

	make(page) {
		this.page = page;
		const $existing = page.main.find(".sp-afs-page");
		if ($existing.length) {
			this.$body = $existing;
			this.refresh();
			return;
		}
		this.$body = $('<div class="sp-afs-page"></div>').appendTo(page.main);
		this.bind();
		this.watch_sidebar();
		this.refresh();
	},

	escape(value) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
	},

	initials(name) {
		return String(name || "")
			.trim()
			.split(/\s+/)
			.slice(0, 2)
			.map((part) => part[0] || "")
			.join("")
			.toUpperCase();
	},

	file_count_label(count) {
		const total = cint(count);
		return total === 1 ? __("{0} file", [total]) : __("{0} files", [total]);
	},

	folder_color(key) {
		const text = String(key || "");
		let hash = 0;
		for (let i = 0; i < text.length; i++) hash = (hash + text.charCodeAt(i) * (i + 1)) % AFS_FOLDER_COLORS.length;
		return AFS_FOLDER_COLORS[hash];
	},

	call(method, args) {
		return frappe.call({ method, args: args || {} }).then((response) => response.message || []);
	},

	bind() {
		const me = this;
		this.$body.on("input", ".sp-afs-search", (event) => {
			me.search = event.target.value || "";
			me.page_index = 0;
			me.paint_dynamic();
		});
		this.$body.on("change", ".sp-afs-agent-filter", (event) => {
			const value = event.target.value || "";
			me.page_index = 0;
			if (me.employee) {
				if (!value) {
					if (me.category) me.open_category(me.category, me.category_name);
					else me.open_root();
					return;
				}
				const agent = me.agents.find((row) => row.name === value);
				me.open_agent(value, agent?.employee_name || value, me.category, me.category_name);
				return;
			}
			me.agent_filter = value;
			me.paint_dynamic();
		});
		this.$body.on("change", ".sp-afs-type-filter", (event) => {
			me.type_filter = event.target.value || "";
			me.page_index = 0;
			me.paint_dynamic();
		});
		this.$body.on("click", "[data-layout]", function () {
			me.layout = $(this).attr("data-layout") || "list";
			me.paint_dynamic();
		});
		this.$body.on("click", "[data-crumb]", function () {
			const crumb = $(this).attr("data-crumb");
			if (crumb === "agents") me.open_root();
			else if (crumb === "agent") {
				me.category = "";
				me.category_name = "";
				me.page_index = 0;
				me.load();
			}
		});
		this.$body.on("click", "[data-agent]", function () {
			me.open_agent($(this).attr("data-agent"), $(this).attr("data-agent-name"), me.category, me.category_name);
		});
		this.$body.on("click", "[data-category]", function () {
			const name = $(this).attr("data-category");
			const label = $(this).attr("data-category-name");
			if (me.employee && me.category === name) {
				me.category = "";
				me.category_name = "";
			} else if (me.employee) {
				me.category = name;
				me.category_name = label || name;
			} else {
				me.open_category(name, label);
				return;
			}
			me.page_index = 0;
			me.load();
		});
		this.$body.on("click", ".sp-afs-create-btn", () => me.create_folder());
		this.$body.on("click", ".sp-afs-upload-btn", () => me.prompt_upload());
		this.$body.on("dragover dragenter", ".sp-afs-panel", (event) => {
			event.preventDefault();
			$(event.currentTarget).addClass("is-dragover");
		});
		this.$body.on("dragleave drop", ".sp-afs-panel", (event) => {
			event.preventDefault();
			$(event.currentTarget).removeClass("is-dragover");
		});
		this.$body.on("drop", ".sp-afs-panel", (event) => {
			const files = event.originalEvent?.dataTransfer?.files
				? Array.from(event.originalEvent.dataTransfer.files)
				: [];
			me.prompt_upload(files);
		});
		this.$body.on("click", "[data-preview]", function () {
			const file = me.files.find((row) => row.name === $(this).attr("data-preview"));
			if (file) me.open_viewer(file);
		});
		this.$body.on("click", "[data-delete-file]", function () {
			const name = $(this).attr("data-delete-file");
			const label = $(this).attr("data-file-name") || name;
			frappe.confirm(__("Delete {0}?", [label]), () => me.delete_file(name));
		});
		this.$body.on("click", "[data-page]", function () {
			const next = cint($(this).attr("data-page"));
			const pages = Math.max(1, Math.ceil(me.visible_files().length / AFS_PAGE_SIZE));
			me.page_index = Math.min(Math.max(0, next), pages - 1);
			me.paint_dynamic();
		});

		if (!this._docClick) {
			this._docClick = true;
			document.addEventListener(
				"click",
				(event) => {
					const nav = event.target.closest?.(".sp-afs-nav");
					if (nav) {
						event.preventDefault();
						event.stopPropagation();
						const name = nav.getAttribute("data-afs-category") || "";
						const label = nav.getAttribute("data-afs-label") || name;
						if (!name) hrms.agent_filesystem.open_root();
						else hrms.agent_filesystem.open_category(name, label);
						return;
					}
					const anchor = event.target.closest?.(".body-sidebar a.item-anchor");
					if (!anchor || anchor.closest(".sp-afs-nav")) return;
					const href = anchor.getAttribute("href") || "";
					if (!href.includes("agent-filesystem")) return;
					const route = frappe.get_route?.() || [];
					if (route[0] !== "agent-filesystem") return;
					event.preventDefault();
					event.stopPropagation();
					hrms.agent_filesystem.open_root();
				},
				true,
			);
		}
	},

	watch_sidebar() {
		if (this._sidebarObserver) return;
		const root = document.querySelector(".body-sidebar");
		if (!root) return;
		this._sidebarObserver = new MutationObserver(() => {
			if (this._mounting || !this.categories.length) return;
			const route = frappe.get_route?.() || [];
			if (route[0] !== "agent-filesystem") return;
			if (!document.querySelector(".sidebar-items .sp-afs-nav")) this.mount_sidebar();
		});
		this._sidebarObserver.observe(root, { childList: true, subtree: true });
	},

	refresh() {
		if (!this.$body) return;
		this.load();
	},

	open_root() {
		this.employee = "";
		this.employee_name = "";
		this.category = "";
		this.category_name = "";
		this.agent_filter = "";
		this.page_index = 0;
		this.load();
	},

	open_category(category, categoryName) {
		this.category = category;
		this.category_name = categoryName || category;
		this.employee = "";
		this.employee_name = "";
		this.agent_filter = "";
		this.page_index = 0;
		this.load();
	},

	open_agent(employee, employeeName, category, categoryName) {
		this.employee = employee;
		this.employee_name = employeeName || employee;
		this.agent_filter = employee || "";
		if (category) {
			this.category = category;
			this.category_name = categoryName || category;
		}
		this.page_index = 0;
		this.load();
	},

	load() {
		this.loading = true;
		this.ensure_shell();
		this.paint_dynamic();
		const employee = this.employee;
		const category = this.category;
		Promise.all([
			this.call("hrms.hr.agent_filesystem.list_categories"),
			employee
				? this.call("hrms.hr.agent_filesystem.list_categories", { employee })
				: Promise.resolve(null),
			this.call("hrms.hr.agent_filesystem.list_agents", { category: employee ? "" : category }),
			this.call("hrms.hr.agent_filesystem.list_files", {
				employee: employee || "",
				category: employee ? "" : category || "",
			}),
		])
			.then(([categories, folderCategories, agents, files]) => {
				if (employee !== this.employee || category !== this.category) return;
				this.categories = categories;
				this.folder_categories = folderCategories || categories;
				this.agents = agents;
				this.files = files;
				this.loading = false;
				this.paint_dynamic();
				this.mount_sidebar();
			})
			.catch(() => {
				this.loading = false;
				this.paint_dynamic();
			});
	},

	create_folder() {
		const dialog = new frappe.ui.Dialog({
			title: __("Create Folder"),
			fields: [
				{
					fieldname: "folder_name",
					fieldtype: "Data",
					label: __("Folder Name"),
					reqd: 1,
				},
			],
			primary_action_label: __("Create"),
			primary_action: (values) => {
				frappe.call({
					method: "hrms.hr.agent_filesystem.create_folder",
					args: { folder_name: values.folder_name },
					callback: (response) => {
						dialog.hide();
						const created = response.message || {};
						if (this.employee && created.name) {
							this.category = created.name;
							this.category_name = created.category_name || created.name;
						}
						this.load();
					},
				});
			},
		});
		dialog.show();
	},

	prompt_upload(presetFiles) {
		const inAgent = Boolean(this.employee);
		const agentByLabel = {};
		const agentOptions = [""];
		this.agents.forEach((agent) => {
			let label = agent.employee_name || agent.name;
			if (agentByLabel[label]) label = `${label} (${agent.name})`;
			agentByLabel[label] = agent.name;
			agentOptions.push(label);
		});
		const typeOptions = [""].concat(
			(this.categories || []).map((category) => category.category_name || category.name),
		);
		let chosen = Array.from(presetFiles || []);
		const fields = [];
		if (inAgent) {
			fields.push({
				fieldname: "agent_label",
				fieldtype: "Data",
				label: __("Agent"),
				read_only: 1,
				default: this.employee_name || this.employee,
			});
		} else {
			fields.push({
				fieldname: "agent",
				fieldtype: "Select",
				label: __("Agent"),
				options: agentOptions.join("\n"),
				reqd: 1,
			});
		}
		fields.push({
			fieldname: "file_type",
			fieldtype: "Select",
			label: __("File Type"),
			options: typeOptions.join("\n"),
			reqd: 1,
			default: this.category_name || this.category || "",
		});
		fields.push({ fieldname: "picker", fieldtype: "HTML" });

		const dialog = new frappe.ui.Dialog({
			title: __("Upload Files"),
			fields,
			primary_action_label: __("Upload"),
			primary_action: (values) => {
				const employee = inAgent ? this.employee : agentByLabel[values.agent];
				const category = values.file_type;
				if (!employee || !category) return;
				if (!chosen.length) {
					frappe.show_alert({ message: __("Choose at least one file."), indicator: "orange" });
					return;
				}
				const $status = dialog.$wrapper.find(".sp-afs-upload-status");
				const $text = dialog.$wrapper.find(".sp-afs-upload-status-text");
				$status.prop("hidden", false);
				dialog.get_primary_btn().prop("disabled", true).text(__("Uploading..."));
				dialog.$wrapper.find(".sp-afs-picker button, .sp-afs-picker input").prop("disabled", true);
				this.upload_files(chosen, employee, category, {
					onProgress: (current, total, filename) => {
						$text.text(__("Uploading {0} of {1}: {2}", [current, total, filename]));
						frappe.show_progress(__("Uploading"), current - 1, total, filename);
					},
					onDone: () => {
						frappe.hide_progress();
						dialog.hide();
					},
				});
			},
		});
		dialog.show();

		const $picker = $(`
			<div class="sp-afs-picker">
				<button type="button" class="btn btn-default btn-sm">${this.escape(__("Choose Files"))}</button>
				<input type="file" multiple />
				<ul class="sp-afs-picker-list"></ul>
				<div class="sp-afs-upload-status" hidden>
					<span class="sp-afs-spinner" aria-hidden="true"></span>
					<span class="sp-afs-upload-status-text"></span>
				</div>
			</div>
		`);
		dialog.fields_dict.picker.$wrapper.html($picker);
		const paintChosen = () => {
			$picker.find(".sp-afs-picker-list").html(
				chosen.map((file) => `<li>${this.escape(file.name)}</li>`).join(""),
			);
		};
		$picker.find("button").on("click", () => $picker.find("input").trigger("click"));
		$picker.find("input").on("change", function () {
			chosen = this.files ? Array.from(this.files) : [];
			paintChosen();
		});
		paintChosen();
	},

	upload_files(fileList, employee, category, hooks) {
		const files = Array.from(fileList || []);
		const me = this;
		if (!files.length || !employee || !category) {
			hooks?.onDone?.();
			return;
		}
		let index = 0;
		const next = () => {
			if (index >= files.length) {
				hooks?.onDone?.();
				me.load();
				return;
			}
			const file = files[index];
			hooks?.onProgress?.(index + 1, files.length, file.name);
			const reader = new FileReader();
			reader.onload = () => {
				const content = String(reader.result || "").split(",")[1] || "";
				frappe.call({
					method: "hrms.hr.agent_filesystem.upload_file",
					args: {
						employee,
						category,
						filename: file.name,
						content,
					},
					callback: () => {
						index += 1;
						next();
					},
					error: () => {
						index += 1;
						next();
					},
				});
			};
			reader.onerror = () => {
				index += 1;
				next();
			};
			reader.readAsDataURL(file);
		};
		next();
	},

	open_viewer(file) {
		const url = file.file_url || "";
		const format = String(file.file_format || "").toUpperCase();
		const title = file.file_name || __("File");
		let preview = "";
		if (!url) {
			preview = `<p class="sp-afs-empty">${this.escape(__("This file has no preview."))}</p>`;
		} else if (["PNG", "JPG", "JPEG", "GIF", "WEBP"].includes(format)) {
			preview = `<img class="sp-afs-viewer-img" src="${this.escape(url)}" alt="${this.escape(title)}" />`;
		} else {
			preview = `<iframe class="sp-afs-viewer" title="${this.escape(title)}" src="${this.escape(url)}"></iframe>`;
		}
		const dialog = new frappe.ui.Dialog({
			title,
			size: "extra-large",
		});
		dialog.$body.html(`
			<div class="sp-afs-viewer-wrap">
				${preview}
			</div>
			<div class="sp-afs-viewer-foot">
				${url ? `<a class="sp-afs-link" href="${this.escape(url)}" target="_blank" rel="noopener">${this.escape(__("Download"))}</a>` : ""}
			</div>
		`);
		dialog.show();
	},

	file_icon(format) {
		const kind = String(format || "").toUpperCase();
		if (kind === "PDF") {
			return `<span class="sp-afs-pdf-icon" title="PDF" aria-label="PDF"><span class="sp-afs-pdf-icon__label">PDF</span></span>`;
		}
		return `<span class="sp-afs-badge">${this.escape((kind || "FILE").slice(0, 4))}</span>`;
	},

	delete_file(name) {
		frappe.call({
			method: "hrms.hr.agent_filesystem.delete_file",
			args: { name },
			callback: () => this.load(),
		});
	},

	ensure_shell() {
		if (!this.$body || this.$body.find(".sp-afs-panel").length) return;
		this.$body.html(`
			<section class="sp-afs-panel">
				<header class="sp-afs-top">
					<div>
						<div class="sp-afs-crumbs-slot"></div>
						<h2 class="sp-afs-title">${this.escape(__("Files"))}</h2>
					</div>
					<div class="sp-afs-top-actions">
						<button type="button" class="sp-afs-create-btn">${this.escape(__("Create Folder"))}</button>
						<button type="button" class="sp-afs-upload-btn">${this.escape(__("Upload Files"))}</button>
						<input class="sp-afs-file-input" type="file" multiple hidden />
					</div>
				</header>
				<div class="sp-afs-folders"></div>
				<div class="sp-afs-controls">
					<div class="sp-afs-layouts" role="group" aria-label="${this.escape(__("Layout"))}">
						<button type="button" data-layout="list">${this.escape(__("List"))}</button>
						<button type="button" data-layout="grid">${this.escape(__("Grid"))}</button>
					</div>
					<input class="sp-afs-search" type="search" placeholder="${this.escape(__("Search agents or files"))}" aria-label="${this.escape(__("Search agents or files"))}" />
					<select class="sp-afs-agent-filter" aria-label="${this.escape(__("Agent"))}"></select>
					<select class="sp-afs-type-filter" aria-label="${this.escape(__("File type"))}"></select>
				</div>
				<div class="sp-afs-results"></div>
			</section>
		`);
	},

	title() {
		if (this.employee && this.category) return this.category_name;
		if (this.employee) return this.employee_name;
		if (this.category) return this.category_name;
		return __("Files");
	},

	crumbs_html() {
		const parts = [
			`<button type="button" class="sp-afs-crumb" data-crumb="agents">${this.escape(__("All Agents"))}</button>`,
		];
		if (this.category && !this.employee) {
			parts.push(`<span class="sp-afs-crumb-sep">/</span>`);
			parts.push(`<span class="sp-afs-crumb is-current">${this.escape(this.category_name)}</span>`);
		}
		if (this.employee) {
			parts.push(`<span class="sp-afs-crumb-sep">/</span>`);
			if (this.category) {
				parts.push(
					`<button type="button" class="sp-afs-crumb" data-crumb="agent">${this.escape(this.employee_name)}</button>`,
				);
				parts.push(`<span class="sp-afs-crumb-sep">/</span>`);
				parts.push(`<span class="sp-afs-crumb is-current">${this.escape(this.category_name)}</span>`);
			} else {
				parts.push(`<span class="sp-afs-crumb is-current">${this.escape(this.employee_name)}</span>`);
			}
		}
		return `<nav class="sp-afs-crumbs" aria-label="${this.escape(__("Filesystem"))}">${parts.join("")}</nav>`;
	},

	visible_agents() {
		const query = (this.search || "").trim().toLowerCase();
		return this.agents.filter((agent) => {
			if (this.agent_filter && agent.name !== this.agent_filter) return false;
			if (!query) return true;
			const haystack = `${agent.employee_name || ""} ${agent.name || ""} ${agent.designation || ""}`.toLowerCase();
			return haystack.includes(query);
		});
	},

	visible_files() {
		const query = (this.search || "").trim().toLowerCase();
		return this.files.filter((file) => {
			if (this.category && file.category !== this.category) return false;
			if (this.agent_filter && file.employee !== this.agent_filter) return false;
			if (this.type_filter && (file.file_format || "") !== this.type_filter) return false;
			if (!query) return true;
			const haystack = `${file.file_name || ""} ${file.employee_name || ""} ${file.uploaded_by_name || ""}`.toLowerCase();
			return haystack.includes(query);
		});
	},

	paint_dynamic() {
		this.ensure_shell();
		const $panel = this.$body.find(".sp-afs-panel");
		$panel.find(".sp-afs-crumbs-slot").html(this.crumbs_html());
		$panel.find(".sp-afs-title").text(this.title());
		$panel.find(".sp-afs-upload-btn").addClass("is-ready");
		$panel.find("[data-layout]").removeClass("is-active");
		$panel.find(`[data-layout="${this.layout}"]`).addClass("is-active");
		this.paint_filters();
		$panel.find(".sp-afs-folders").html(this.loading ? "" : this.folders_html());
		$panel.find(".sp-afs-results").html(
			this.loading
				? `<p class="sp-afs-empty">${this.escape(__("Loading..."))}</p>`
				: this.results_html(),
		);
		this.mark_sidebar_active();
	},

	paint_filters() {
		const $agent = this.$body.find(".sp-afs-agent-filter");
		const $type = this.$body.find(".sp-afs-type-filter");
		const agentValue = this.agent_filter;
		const typeValue = this.type_filter;
		const agentOptions = [`<option value="">${this.escape(__("All agents"))}</option>`]
			.concat(
				this.agents.map(
					(agent) =>
						`<option value="${this.escape(agent.name)}">${this.escape(agent.employee_name || agent.name)}</option>`,
				),
			)
			.join("");
		if ($agent.attr("data-options") !== agentOptions) {
			$agent.html(agentOptions);
			$agent.attr("data-options", agentOptions);
		}
		if ($agent.val() !== agentValue) $agent.val(agentValue);

		const types = Array.from(new Set(this.files.map((file) => file.file_format).filter(Boolean))).sort();
		const typeOptions = [`<option value="">${this.escape(__("File type"))}</option>`]
			.concat(types.map((type) => `<option value="${this.escape(type)}">${this.escape(type)}</option>`))
			.join("");
		if ($type.attr("data-options") !== typeOptions) {
			$type.html(typeOptions);
			$type.attr("data-options", typeOptions);
		}
		if (typeValue && types.includes(typeValue)) $type.val(typeValue);
		else {
			this.type_filter = "";
			$type.val("");
		}
	},

	folder_html(attrs, color, title, meta, count, selected) {
		return `
			<button type="button" class="sp-afs-folder${selected ? " is-selected" : ""}" style="--folder:${color}" ${attrs}>
				<span class="sp-afs-folder__tab"></span>
				<span class="sp-afs-folder__body">
					<span class="sp-afs-folder__name">${this.escape(title)}</span>
					<span class="sp-afs-folder__count">${this.escape(this.file_count_label(count))}</span>
					${meta ? `<span class="sp-afs-folder__meta">${this.escape(meta)}</span>` : ""}
				</span>
			</button>`;
	},

	folders_html() {
		if (this.employee) {
			const folders = this.folder_categories || [];
			if (!folders.length) {
				return `<p class="sp-afs-empty">${this.escape(__("No document categories yet."))}</p>`;
			}
			return `<div class="sp-afs-folder-row">${folders
				.map((category) =>
					this.folder_html(
						`data-category="${this.escape(category.name)}" data-category-name="${this.escape(category.category_name || category.name)}"`,
						this.folder_color(category.name),
						category.category_name || category.name,
						"",
						category.file_count,
						this.category === category.name,
					),
				)
				.join("")}</div>`;
		}

		const agents = this.visible_agents();
		if (!agents.length) {
			return `<p class="sp-afs-empty">${this.escape(__("No agents found."))}</p>`;
		}
		return `<div class="sp-afs-folder-row">${agents
			.map((agent) =>
				this.folder_html(
					`data-agent="${this.escape(agent.name)}" data-agent-name="${this.escape(agent.employee_name || agent.name)}"`,
					this.folder_color(agent.name),
					agent.employee_name || agent.name,
					agent.designation || agent.status || "",
					agent.file_count,
					false,
				),
			)
			.join("")}</div>`;
	},

	results_html() {
		const files = this.visible_files();
		const pages = Math.max(1, Math.ceil(files.length / AFS_PAGE_SIZE));
		if (this.page_index > pages - 1) this.page_index = 0;
		const start = this.page_index * AFS_PAGE_SIZE;
		const pageRows = files.slice(start, start + AFS_PAGE_SIZE);
		const body = !files.length
			? `<p class="sp-afs-empty">${this.escape(this.category || this.employee ? __("This folder is empty.") : __("No files yet. Open an agent folder to upload."))}</p>`
			: this.layout === "grid"
				? this.grid_html(pageRows)
				: this.table_html(pageRows);
		return `${body}${this.pager_html(files.length, pages)}`;
	},

	table_html(files) {
		const showAgent = !this.employee;
		const rows = files
			.map((file) => {
				const when = file.uploaded_on ? frappe.datetime.str_to_user(file.uploaded_on) : "";
				const format = file.file_format || "FILE";
				const download = file.file_url
					? `<button type="button" class="sp-afs-link" data-preview="${this.escape(file.name)}">${this.escape(__("Open"))}</button>`
					: "";
				const remove = file.can_delete
					? `<button type="button" class="sp-afs-link sp-afs-link--danger" data-delete-file="${this.escape(file.name)}" data-file-name="${this.escape(file.file_name)}">${this.escape(__("Delete"))}</button>`
					: "";
				return `
					<tr>
						<td>
							<div class="sp-afs-file-name">
								${this.file_icon(format)}
								<span>
									<span class="sp-afs-file-title">${this.escape(file.file_name || file.name)}</span>
									<span class="sp-afs-file-sub">${this.escape(when)}</span>
								</span>
							</div>
						</td>
						${showAgent ? `<td>${this.escape(file.employee_name || "")}</td>` : ""}
						<td>
							<span class="sp-afs-person">
								<span class="sp-afs-person__avatar">${this.escape(this.initials(file.uploaded_by_name))}</span>
								${this.escape(file.uploaded_by_name || "")}
							</span>
						</td>
						<td>${this.escape(format)}</td>
						<td class="sp-afs-row-actions">${download}${remove}</td>
					</tr>`;
			})
			.join("");
		return `
			<div class="sp-afs-table-wrap">
				<table class="sp-afs-table">
					<thead>
						<tr>
							<th>${this.escape(__("Files"))}</th>
							${showAgent ? `<th>${this.escape(__("Agent"))}</th>` : ""}
							<th>${this.escape(__("Uploader"))}</th>
							<th>${this.escape(__("Format"))}</th>
							<th></th>
						</tr>
					</thead>
					<tbody>${rows}</tbody>
				</table>
			</div>`;
	},

	grid_html(files) {
		return `<div class="sp-afs-file-grid">${files
			.map((file) => {
				const format = file.file_format || "FILE";
				const download = file.file_url
					? `<button type="button" class="sp-afs-link" data-preview="${this.escape(file.name)}">${this.escape(__("Open"))}</button>`
					: "";
				const remove = file.can_delete
					? `<button type="button" class="sp-afs-link sp-afs-link--danger" data-delete-file="${this.escape(file.name)}" data-file-name="${this.escape(file.file_name)}">${this.escape(__("Delete"))}</button>`
					: "";
				return `
					<article class="sp-afs-file-card">
						${this.file_icon(format)}
						<strong>${this.escape(file.file_name || file.name)}</strong>
						<span>${this.escape(file.employee_name || "")}</span>
						<div class="sp-afs-row-actions">${download}${remove}</div>
					</article>`;
			})
			.join("")}</div>`;
	},

	pager_html(total, pages) {
		if (total <= AFS_PAGE_SIZE) {
			return `<div class="sp-afs-pager"><span>${this.escape(__("{0} files", [total]))}</span></div>`;
		}
		const buttons = [];
		buttons.push(`<button type="button" data-page="${this.page_index - 1}" ${this.page_index === 0 ? "disabled" : ""}>&lsaquo;</button>`);
		for (let i = 0; i < pages; i++) {
			buttons.push(`<button type="button" data-page="${i}" class="${i === this.page_index ? "is-current" : ""}">${i + 1}</button>`);
		}
		buttons.push(`<button type="button" data-page="${this.page_index + 1}" ${this.page_index >= pages - 1 ? "disabled" : ""}>&rsaquo;</button>`);
		return `<div class="sp-afs-pager"><span>${this.escape(__("Page {0} of {1}", [this.page_index + 1, pages]))}</span><div>${buttons.join("")}</div></div>`;
	},

	mount_sidebar() {
		const route = frappe.get_route?.() || [];
		if (route[0] !== "agent-filesystem") return;
		const sidebar = frappe.app?.sidebar;
		if (sidebar && (sidebar.current_module || "") !== "Filesystem" && typeof sidebar.select_module === "function") {
			sidebar.select_module("Filesystem");
			setTimeout(() => this.mount_sidebar(), 60);
			return;
		}
		const $items = $(".body-sidebar .sidebar-items").first();
		if (!$items.length || !this.categories.length) return;
		const signature = this.categories.map((category) => category.name).join("|");
		if ($items.attr("data-sp-afs-nav") === signature && $items.find(".sp-afs-nav").length) {
			this.ensure_td4_link($items);
			this.mark_sidebar_active();
			return;
		}
		this._mounting = true;
		$items.find(".sp-afs-nav").remove();
		const html = this.categories
			.map((category) => {
				const label = category.category_name || category.name;
				return `
					<div class="sidebar-item-container sp-afs-nav" data-afs-category="${this.escape(category.name)}" data-afs-label="${this.escape(label)}">
						<div class="standard-sidebar-item">
							<a href="#" class="item-anchor">
								<span class="sidebar-item-icon" aria-hidden="true"></span>
								<span class="sidebar-item-label">${this.escape(label)}</span>
							</a>
						</div>
					</div>`;
			})
			.join("");
		$items.append(html);
		$items.attr("data-sp-afs-nav", signature);
		this.ensure_td4_link($items);
		this._mounting = false;
		this.mark_sidebar_active();
	},

	ensure_td4_link($items) {
		if (!$items?.length) return;
		const access = frappe.boot?.staff_pro_access;
		const allowed = !access || !("see_td4_forms" in access) || !!access.see_td4_forms;
		if (!allowed) {
			$items.find(".sp-afs-td4").remove();
			$items.find('a.item-anchor[href*="td4-form"]').closest(".sidebar-item-container").remove();
			return;
		}
		if ($items.find('a.item-anchor[href*="td4-form"]').length) return;
		const label = this.escape(__("TD4 Forms"));
		const html = `
			<div class="sidebar-item-container sp-afs-td4">
				<div class="standard-sidebar-item">
					<a href="/desk/td4-form" class="item-anchor">
						<span class="sidebar-item-icon" aria-hidden="true"></span>
						<span class="sidebar-item-label">${label}</span>
					</a>
				</div>
			</div>`;
		const $first = $items.children(".sidebar-item-container").first();
		if ($first.length) $first.after(html);
		else $items.prepend(html);
	},

	mark_sidebar_active() {
		const $items = $(".body-sidebar .sidebar-items").first();
		if (!$items.length) return;
		$items.find(".sp-afs-nav .standard-sidebar-item").removeClass("active-sidebar selected");
		$items.find(".standard-sidebar-item").each(function () {
			const href = ($(this).find(".item-anchor").attr("href") || "");
			if (href.includes("agent-filesystem") && !$(this).closest(".sp-afs-nav").length) {
				$(this).toggleClass("active-sidebar", !hrms.agent_filesystem.category);
			}
		});
		if (!this.category) return;
		$items
			.find(`.sp-afs-nav[data-afs-category="${CSS.escape(this.category)}"] .standard-sidebar-item`)
			.addClass("active-sidebar");
	},
};

function cint(value) {
	const number = parseInt(value, 10);
	return Number.isNaN(number) ? 0 : number;
}
