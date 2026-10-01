function sanitize_attached_image_names(names) {
	if (typeof names === "string") {
		const text = names.trim();
		if (!text || text === "null" || text === "undefined") return [];
		if (text.startsWith("[") || text.startsWith('"')) {
			try {
				names = JSON.parse(text);
			} catch (e) {
				return [text];
			}
		} else {
			return [text];
		}
	}
	if (names == null) return [];
	if (!Array.isArray(names)) return [String(names)];
	return names.filter((name) => typeof name === "string" && name.trim());
}

function empty_attached_images_response(opts) {
	const res = { message: {} };
	if (typeof opts?.callback === "function") opts.callback(res);
	return Promise.resolve(res);
}

function patch_attached_images_call() {
	if (typeof frappe.call !== "function" || frappe.call._staff_pro_attached_images) return;

	const original = frappe.call;
	function wrapped(opts) {
		if (opts && typeof opts === "object" && opts.method === "frappe.core.api.file.get_attached_images") {
			const names = sanitize_attached_image_names(opts.args && opts.args.names);
			if (!names.length) {
				return empty_attached_images_response(opts);
			}
			opts = Object.assign({}, opts, {
				method: "hrms.overrides.attached_images.get_attached_images",
				args: Object.assign({}, opts.args, { names }),
			});
			return original.call(this, opts);
		}
		return original.apply(this, arguments);
	}

	Object.keys(original).forEach((key) => {
		wrapped[key] = original[key];
	});
	wrapped._staff_pro_attached_images = true;
	frappe.call = wrapped;
}

function patch_image_view_attached_images() {
	const ImageView = frappe.views?.ImageView;
	if (!ImageView?.prototype || ImageView.prototype._staff_pro_attached_images) return;
	ImageView.prototype._staff_pro_attached_images = true;

	ImageView.prototype.get_attached_images = function () {
		const names = sanitize_attached_image_names((this.items || []).map((item) => item && item.name));
		if (!names.length) {
			this.images_map = this.images_map || {};
			return Promise.resolve();
		}
		return frappe
			.call({
				method: "hrms.overrides.attached_images.get_attached_images",
				args: { doctype: this.doctype, names },
			})
			.then((r) => {
				this.images_map = Object.assign(this.images_map || {}, r.message);
			});
	};
}

function install_attached_images_guard() {
	patch_attached_images_call();
	patch_image_view_attached_images();
}

$(document).on("app_ready", install_attached_images_guard);
if (typeof frappe.ready === "function") {
	frappe.ready(install_attached_images_guard);
}
install_attached_images_guard();
