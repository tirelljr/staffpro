const KEEP_LIST_ACTIONS = /^(delete|cancel|submit|export)(\b|$)/i;

function keep_list_action_label(label) {
	const text = String(label || "")
		.replace(/\s+/g, " ")
		.trim();
	if (!text) return false;
	if (/^delete selected/i.test(text)) return true;
	return KEEP_LIST_ACTIONS.test(text);
}

function strip_list_action_menu(root) {
	const $root = root ? $(root) : $(document);
	$root.find(".es-menu__item, .actions-btn-group .dropdown-item, .page-actions .dropdown-item").each(
		function () {
			const label = (
				this.querySelector?.(".es-menu__label")?.textContent ||
				this.textContent ||
				""
			)
				.replace(/\s+/g, " ")
				.trim();
			if (label && !keep_list_action_label(label)) {
				this.remove();
			}
		},
	);
}

function bulk_delete_selected(listview) {
	const doctype = listview?.doctype;
	const names = listview?.get_checked_items?.(true) || [];
	if (!doctype) return;
	if (!names.length) {
		frappe.msgprint(__("Select one or more rows first."));
		return;
	}

	const label = __(doctype);
	frappe.confirm(
		names.length === 1
			? __("Delete this {0}? Linked records are removed too.", [label])
			: __("Delete {0} {1} records? Linked records are removed too.", [names.length, label]),
		() => {
			frappe.call({
				method: "hrms.hr.force_delete.bulk_delete_documents",
				args: { doctype, names },
				freeze: true,
				freeze_message: __("Deleting..."),
				callback(r) {
					if (r.exc) return;
					const count = r.message?.count || 0;
					const failed = r.message?.errors?.length || 0;
					frappe.show_alert({
						message: failed
							? __("Deleted {0}. {1} failed.", [count, failed])
							: __("Deleted {0}", [count]),
						indicator: failed ? "orange" : "green",
					});
					listview.refresh();
				},
			});
		},
	);
}

function patch_list_delete() {
	const ListView = frappe.views?.ListView;
	if (!ListView?.prototype || ListView.prototype._staff_pro_bulk_delete) return;
	ListView.prototype._staff_pro_bulk_delete = true;

	ListView.prototype.delete_items = function () {
		bulk_delete_selected(this);
	};

	if (typeof ListView.prototype.setup_filterable === "function") {
		const original_filterable = ListView.prototype.setup_filterable;
		ListView.prototype.setup_filterable = function () {
			const result = original_filterable.apply(this, arguments);
			this.page && (this.page._staff_pro_list_actions = true);
			return result;
		};
	}

	["setup", "onload", "refresh", "toggle_actions_menu_button"].forEach((method) => {
		if (typeof ListView.prototype[method] !== "function") return;
		const original = ListView.prototype[method];
		ListView.prototype[method] = function () {
			const result = original.apply(this, arguments);
			if (this.page) this.page._staff_pro_list_actions = true;
			strip_list_action_menu(this.page?.wrapper || document);
			return result;
		};
	});
}

function patch_page_action_items() {
	const Page = frappe.ui?.Page;
	if (!Page?.prototype || Page.prototype._staff_pro_action_filter) return;
	Page.prototype._staff_pro_action_filter = true;

	if (typeof Page.prototype.add_action_item === "function") {
		const original = Page.prototype.add_action_item;
		Page.prototype.add_action_item = function (label) {
			if (this._staff_pro_list_actions && !keep_list_action_label(label)) {
				return;
			}
			return original.apply(this, arguments);
		};
	}
}

function watch_action_menus() {
	if (document.body._staff_pro_action_observer) return;
	const observer = new MutationObserver((mutations) => {
		for (const mutation of mutations) {
			for (const node of mutation.addedNodes) {
				if (!(node instanceof HTMLElement)) continue;
				if (
					node.matches?.(".es-menu, .es-menu__group, .actions-btn-group") ||
					node.querySelector?.(".es-menu, .es-menu__item")
				) {
					strip_list_action_menu(node);
				}
			}
		}
	});
	observer.observe(document.body, { childList: true, subtree: true });
	document.body._staff_pro_action_observer = observer;
}

function patch_leave_ledger_cancel() {
	const ListView = frappe.views?.ListView;
	if (ListView?.prototype && !ListView.prototype._staff_pro_lle_cancel) {
		ListView.prototype._staff_pro_lle_cancel = true;
		if (typeof ListView.prototype.cancel_items === "function") {
			const original = ListView.prototype.cancel_items;
			ListView.prototype.cancel_items = function () {
				if (this.doctype === "Leave Ledger Entry") {
					frappe.msgprint(__("Cancel the source Leave Allocation or Leave Application instead."));
					return;
				}
				return original.apply(this, arguments);
			};
		}
	}

	if (typeof frappe.call !== "function" || frappe.call._staff_pro_lle_cancel) return;
	const original_call = frappe.call;
	function wrapped(opts) {
		if (opts && typeof opts === "object" && opts.method === "frappe.desk.form.save.cancel") {
			let doc = opts.args?.doc;
			if (typeof doc === "string") {
				try {
					doc = JSON.parse(doc);
				} catch (e) {
					doc = null;
				}
			}
			const doctype = opts.args?.doctype || doc?.doctype;
			if (doctype === "Leave Ledger Entry") {
				frappe.msgprint(__("Cancel the source Leave Allocation or Leave Application instead."));
				const res = { message: null };
				if (typeof opts.error === "function") opts.error(res);
				return Promise.resolve(res);
			}
		}
		return original_call.apply(this, arguments);
	}
	Object.keys(original_call).forEach((key) => {
		wrapped[key] = original_call[key];
	});
	wrapped._staff_pro_lle_cancel = true;
	if (original_call._staff_pro_attached_images) {
		wrapped._staff_pro_attached_images = true;
	}
	frappe.call = wrapped;
}

function install_list_actions() {
	patch_page_action_items();
	patch_list_delete();
	patch_leave_ledger_cancel();
	watch_action_menus();
	if (cur_list?.page) {
		cur_list.page._staff_pro_list_actions = true;
		if (typeof cur_list.delete_items === "function") {
			cur_list.delete_items = function () {
				bulk_delete_selected(cur_list);
			};
		}
	}
	strip_list_action_menu(document);
}

$(document).on("app_ready", install_list_actions);
$(document).on("page-change", install_list_actions);
if (typeof frappe.ready === "function") {
	frappe.ready(install_list_actions);
}
