function makeTranslationFunction() {
	let messages = {};
	return {
		translate,
		load: () => Promise.allSettled([
			setup(),
			// TODO: load dayjs locales
		]),
	}

	async function setup() {
		if (window.frappe?.boot?.__messages) {
			messages = window.frappe?.boot?.__messages;
		} else {
			const url = new URL("/api/method/frappe.translate.load_all_translations", location.origin);
			url.searchParams.append("lang", window.frappe?.boot?.lang ?? navigator.language);
			url.searchParams.append("hash", window.frappe?.boot?.translations_hash || window._version_number || Math.random()); // for cache busting

			try {
				const response = await fetch(url);
				const contentType = response.headers.get("content-type") || ""
				if (!response.ok || !contentType.includes("json")) {
					messages = messages || {};
				} else {
					messages = await response.json() || {}
				}
			} catch (error) {
				console.error("Failed to fetch translations:", error)
			}
		}

		messages = messages || {};
		messages.Fortnightly = "2-weeks";
		messages["2 Weeks"] = "2-weeks";
		messages["Cost to Company (CTC)"] = "Agent Hourly";
		messages["PAN Number"] = "Tax Number";
		messages["Total Cost To Company (CTC)"] = "Agent Hourly";
		messages.CTC = "Agent Hourly";
		messages["Current CTC"] = "Current Agent Hourly";
		messages["Revised CTC"] = "Revised Agent Hourly";
		if (window.frappe?.boot) {
			window.frappe.boot.__messages = messages;
		}
	}

	function translate(txt, replace, context = null) {
		if (!txt || typeof txt != "string") return txt;

		let translated_text = "";
		let key = txt;
		if (context) {
			translated_text = messages[`${key}:${context}`];
		}
		if (!translated_text) {
			translated_text = messages[key] || txt;
		}
		if (replace && typeof replace === "object") {
			translated_text = format(translated_text, replace);
		}

		return translated_text;
	}

	function format(str, args) {
		if (str == undefined) return str;

		let unkeyed_index = 0;
		return str.replace(
			/\{(\w*)\}/g,
			(match, key) => {
				if (key === "") {
					key = unkeyed_index;
					unkeyed_index++;
				}
				if (key == +key) {
					return args[key] !== undefined ? args[key] : match;
				}
			}
		);
	}
}

const { translate, load } = makeTranslationFunction();

export const translationsPlugin = {
	async isReady() {
		await load();
	},
	install(/** @type {import('vue').App} */ app, options) {
		const __ = translate;
		// app.mixin({ methods: { __ } })
		app.config.globalProperties.__ = __;
		app.provide("$translate", __);
	},
}
