frappe.provide("hrms.ai");

frappe.pages["ask-ai"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Ask AI"),
		single_column: true,
	});
	frappe.breadcrumbs.add("HR");
	hrms.ai.ask_ai.make(page);
};

frappe.pages["ask-ai"].on_page_show = function () {
	hrms.ai.ask_ai.refresh();
};

hrms.ai.ask_ai = {
	page: null,
	$body: null,
	conversation: null,
	conversations: [],
	messages: [],
	busy: false,
	user: null,

	storage_key() {
		return `staff-pro-ask-ai:${frappe.session.user}`;
	},

	read_saved_conversation() {
		try {
			return localStorage.getItem(this.storage_key()) || "";
		} catch {
			return "";
		}
	},

	save_conversation(name) {
		try {
			if (name) localStorage.setItem(this.storage_key(), name);
			else localStorage.removeItem(this.storage_key());
		} catch {
			/* ignore quota / private mode */
		}
	},

	conversation_rows(payload) {
		if (Array.isArray(payload)) return payload;
		if (Array.isArray(payload?.conversations)) return payload.conversations;
		if (payload && payload !== this && payload.message !== payload) {
			return this.conversation_rows(payload.message);
		}
		return [];
	},

	make(page) {
		this.page = page;
		const $existing = page.main.find(".sp-ai");
		if ($existing.length) {
			this.$body = $existing;
			this.refresh();
			return;
		}
		this.$body = $('<div class="sp-ai"></div>').appendTo(page.main);
		this.render_shell();
		this.bind();
		this.refresh();
	},

	close() {
		const prev = frappe.get_prev_route?.() || [];
		if (prev.length && prev[0] !== "ask-ai") {
			frappe.set_route(prev);
			return;
		}
		frappe.set_route("");
	},

	escape(value) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
	},

	render_shell() {
		this.$body.html(`
			<aside class="sp-ai__rail" aria-label="${this.escape(__("Conversations"))}">
				<div class="sp-ai__rail-head">
					<button type="button" class="sp-ai__new" data-ai-action="new-chat">
						<span aria-hidden="true">＋</span>${this.escape(__("New chat"))}
					</button>
					<button type="button" class="sp-ai__rail-toggle" data-ai-action="toggle-rail" aria-label="${this.escape(__("Close conversation history"))}">‹</button>
				</div>
				<div class="sp-ai__history"></div>
			</aside>
			<main class="sp-ai__main">
				<button type="button" class="sp-ai__open-rail" data-ai-action="toggle-rail" aria-label="${this.escape(__("Open conversation history"))}">☰</button>
				<button type="button" class="sp-ai__close" data-ai-action="close" title="${this.escape(__("Close"))}" aria-label="${this.escape(__("Close Ask AI"))}">
					<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
						<path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path>
					</svg>
				</button>
				<div class="sp-ai__thread" aria-live="polite"></div>
				<div class="sp-ai__composer-wrap">
					<form class="sp-ai__composer">
						<textarea rows="1" maxlength="4000" placeholder="${this.escape(__("Ask me anything about Staff Pro…"))}" aria-label="${this.escape(__("Message Ask AI"))}"></textarea>
						<div class="sp-ai__composer-actions">
							<div class="sp-ai__composer-tools">
								<button type="button" class="sp-ai__tool" disabled title="${this.escape(__("Attachments are coming soon"))}">⌕ ${this.escape(__("Attach"))}</button>
								<button type="button" class="sp-ai__tool" disabled title="${this.escape(__("Voice is coming soon"))}">◉ ${this.escape(__("Voice"))}</button>
							</div>
							<button type="submit" class="sp-ai__send" aria-label="${this.escape(__("Send message"))}">➤</button>
						</div>
					</form>
					<p class="sp-ai__notice">${this.escape(__("Ask AI can make mistakes. Confirm important HR and payroll details."))}</p>
				</div>
			</main>
		`);
	},

	bind() {
		this.$body.on("click", "[data-ai-action='new-chat']", () => this.new_chat());
		this.$body.on("click", "[data-ai-action='toggle-rail']", () => this.$body.toggleClass("sp-ai--rail-hidden"));
		this.$body.on("click", "[data-ai-action='close']", () => this.close());
		this.$body.on("click", ".sp-ai__history-item", (event) => {
			this.open_conversation($(event.currentTarget).attr("data-name"));
		});
		this.$body.on("click", ".sp-ai__history-delete", (event) => {
			event.preventDefault();
			event.stopPropagation();
			this.confirm_delete($(event.currentTarget).attr("data-name"));
		});
		this.$body.on("click", "[data-prompt]", (event) => {
			const prompt = $(event.currentTarget).attr("data-prompt");
			this.$body.find(".sp-ai__composer textarea").val(prompt);
			this.send(prompt);
		});
		this.$body.on("click", "[data-route]", (event) => {
			const route = JSON.parse($(event.currentTarget).attr("data-route") || "[]");
			if (route.length) frappe.set_route(...route);
		});
		this.$body.on("click", "[data-action-id]", (event) => {
			const $button = $(event.currentTarget);
			this.confirm_action($button.attr("data-action-id"), $button.attr("data-approved") === "1");
		});
		this.$body.find(".sp-ai__composer").on("submit", (event) => {
			event.preventDefault();
			const $input = this.$body.find(".sp-ai__composer textarea");
			const message = $input.val().trim();
			if (!message || this.busy) return;
			$input.val("").trigger("input");
			this.send(message);
		});
		this.$body.find(".sp-ai__composer textarea")
			.on("input", (event) => {
				event.currentTarget.style.height = "auto";
				event.currentTarget.style.height = `${Math.min(event.currentTarget.scrollHeight, 144)}px`;
			})
			.on("keydown", (event) => {
				if (event.key === "Enter" && !event.shiftKey) {
					event.preventDefault();
					this.$body.find(".sp-ai__composer").trigger("submit");
				}
			});
	},

	async call(method, args = {}) {
		const response = await frappe.call({ method: `hrms.api.assistant.${method}`, args });
		return response && response.message !== undefined ? response.message : response;
	},

	async refresh() {
		if (this.user && this.user !== frappe.session.user) {
			this.conversation = null;
			this.messages = [];
		}
		this.user = frappe.session.user;
		try {
			const payload = await this.call("list_conversations");
			this.conversations = this.conversation_rows(payload);
			this.render_history();
			const saved = this.conversation || payload?.last_conversation || this.read_saved_conversation();
			const mine = saved && this.conversations.some((item) => item.name === saved);
			if (mine) {
				await this.open_conversation(saved, false);
			} else {
				this.conversation = null;
				this.messages = [];
				this.save_conversation("");
				this.render_thread();
			}
		} catch (error) {
			this.conversations = [];
			this.render_history();
			this.$body.find(".sp-ai__history").html(
				`<p class="sp-ai__history-empty">${this.escape(error?.message || __("Could not load your conversations."))}</p>`
			);
			this.render_error(error);
		}
	},

	confirm_delete(name) {
		if (!name || this.busy) return;
		frappe.confirm(__("Delete this conversation? This cannot be undone."), () => {
			this.delete_conversation(name);
		});
	},

	async delete_conversation(name) {
		if (!name || this.busy) return;
		this.busy = true;
		this.set_busy(true);
		try {
			const payload = await this.call("delete_conversation", { name });
			this.conversations = this.conversation_rows(payload);
			if (this.conversation === name) {
				this.conversation = null;
				this.messages = [];
				this.save_conversation("");
				this.render_thread();
			}
			this.render_history();
		} catch (error) {
			this.render_error(error);
		} finally {
			this.busy = false;
			this.set_busy(false);
		}
	},

	async new_chat() {
		if (this.busy) return;
		this.conversation = null;
		this.messages = [];
		this.save_conversation("");
		this.render_history();
		this.render_thread();
		this.$body.find("textarea").trigger("focus");
	},

	async open_conversation(name, refresh_history = true) {
		if (!name || this.busy) return;
		try {
			const data = await this.call("get_conversation", { name });
			this.conversation = data.name;
			this.messages = data.messages || [];
			this.save_conversation(data.name);
			this.render_thread();
			if (refresh_history) {
				const payload = await this.call("list_conversations");
				this.conversations = this.conversation_rows(payload);
				this.render_history();
			}
		} catch (error) {
			this.render_error(error);
		}
	},

	async send(message) {
		const action_id = this.pending_action_id();
		if (action_id && this.is_affirmative(message)) {
			await this.confirm_action(action_id, true);
			return;
		}
		if (action_id && this.is_negative(message)) {
			await this.confirm_action(action_id, false);
			return;
		}
		this.busy = true;
		this.messages.push({ role: "user", content: message, blocks: [] });
		this.render_thread(true);
		this.set_busy(true);
		try {
			const data = await this.call("chat", {
				conversation: this.conversation,
				message,
			});
			this.conversation = data.conversation;
			this.messages = data.messages || this.messages;
			this.save_conversation(this.conversation);
			const payload = await this.call("list_conversations");
			this.conversations = this.conversation_rows(payload);
			this.render_history();
		} catch (error) {
			this.messages.pop();
			this.render_error(error);
		} finally {
			this.busy = false;
			this.set_busy(false);
			this.render_thread(true);
		}
	},

	async confirm_action(action_id, approved) {
		if (this.busy || !this.conversation) return;
		this.busy = true;
		this.set_busy(true);
		try {
			const data = await this.call("confirm_action", {
				conversation: this.conversation,
				action_id,
				approved: approved ? 1 : 0,
			});
			this.messages = data.messages || this.messages;
			if (approved) {
				if (hrms.time?.refresh_hours_views) {
					hrms.time.refresh_hours_views();
				} else {
					$(document).trigger("sp:hours-refresh");
				}
			}
		} catch (error) {
			this.render_error(error);
		} finally {
			this.busy = false;
			this.set_busy(false);
			this.render_thread(true);
		}
	},

	pending_action_id() {
		const messages = Array.isArray(this.messages) ? this.messages : [];
		for (let i = messages.length - 1; i >= 0; i -= 1) {
			const blocks = messages[i].blocks || [];
			for (const block of blocks) {
				if (block.type === "action" && block.action_id && (!block.status || block.status === "pending")) {
					return block.action_id;
				}
			}
		}
		return "";
	},

	normalized_reply(message) {
		return String(message || "")
			.trim()
			.toLowerCase()
			.replace(/[.!?]+$/, "")
			.trim();
	},

	is_affirmative(message) {
		return [
			"yes",
			"y",
			"ok",
			"okay",
			"k",
			"confirm",
			"confirmed",
			"do it",
			"proceed",
			"go ahead",
			"sure",
			"please",
			"yes please",
			"yes confirm",
			"confirm please",
			"looks good",
			"do that",
			"apply",
			"apply it",
			"approve",
		].includes(this.normalized_reply(message));
	},

	is_negative(message) {
		return [
			"no",
			"n",
			"cancel",
			"cancelled",
			"canceled",
			"don't",
			"dont",
			"stop",
			"never mind",
			"nevermind",
			"reject",
		].includes(this.normalized_reply(message));
	},

	set_busy(busy) {
		this.$body.find(".sp-ai__send").prop("disabled", busy).toggleClass("is-loading", busy);
		this.$body.find("[data-action-id], .sp-ai__history-delete").prop("disabled", busy);
		if (!busy) this.$body.find(".sp-ai__typing").closest(".sp-ai__message").remove();
	},

	render_history() {
		const groups = { Today: [], Yesterday: [], Older: [] };
		this.conversations = this.conversation_rows(this.conversations);
		this.conversations.forEach((item) => {
			(groups[item.group] || groups.Older).push(item);
		});
		const html = Object.entries(groups)
			.filter(([, items]) => items.length)
			.map(([group, items]) => `
				<section class="sp-ai__history-group">
					<h3>${this.escape(__(group))}</h3>
					${items.map((item) => `
						<div class="sp-ai__history-row ${item.name === this.conversation ? "is-active" : ""}">
							<button type="button" class="sp-ai__history-item" data-name="${this.escape(item.name)}">
								<span>${this.escape(item.title || __("New conversation"))}</span>
							</button>
							<button type="button" class="sp-ai__history-delete" data-name="${this.escape(item.name)}" title="${this.escape(__("Delete conversation"))}" aria-label="${this.escape(__("Delete conversation"))}">
								<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
									<path d="M9 4h6M5 7h14M8 7l.8 12.2h6.4L16 7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path>
								</svg>
							</button>
						</div>`).join("")}
				</section>`).join("");
		this.$body.find(".sp-ai__history").html(html || `<p class="sp-ai__history-empty">${this.escape(__("Your conversations will appear here."))}</p>`);
	},

	render_thread(scroll = false) {
		const $thread = this.$body.find(".sp-ai__thread");
		this.messages = Array.isArray(this.messages) ? this.messages : [];
		if (!this.messages.length) {
			$thread.html(this.empty_state_html());
			return;
		}
		$thread.html(`
			<div class="sp-ai__messages">
				${this.messages.map((message) => this.message_html(message)).join("")}
				${this.busy ? `<div class="sp-ai__message sp-ai__message--assistant"><div class="sp-ai__avatar">✦</div><div class="sp-ai__typing"><i></i><i></i><i></i></div></div>` : ""}
			</div>
		`);
		this.mount_charts();
		if (scroll) $thread.get(0)?.scrollTo({ top: $thread.get(0).scrollHeight, behavior: "smooth" });
	},

	empty_state_html() {
		const prompts = [
			__("Who is in today and which department has the most absences?"),
			__("Show total regular and overtime hours for this month."),
			__("List pending time clock adjustments."),
		];
		return `
			<div class="sp-ai__empty">
				<div class="sp-ai__orb" aria-hidden="true">✦</div>
				<h1>${this.escape(__("Hi, there"))}</h1>
				<p>${this.escape(__("Ask about your workforce, hours, attendance, or payroll."))}</p>
				<div class="sp-ai__suggestions">
					${prompts.map((prompt, index) => `
						<button type="button" class="sp-ai__suggestion" data-prompt="${this.escape(prompt)}">
							<span class="sp-ai__suggestion-tag">${this.escape(index === 0 ? __("Live attendance") : index === 1 ? __("Hours analysis") : __("Approvals"))}</span>
							<strong>${this.escape(prompt)}</strong>
						</button>`).join("")}
				</div>
				<div class="sp-ai__shortcuts">
					<button type="button" data-prompt="${this.escape(__("Who is in today?"))}">◉ ${this.escape(__("Who Is In"))}</button>
					<button type="button" data-prompt="${this.escape(__("Show pending time clock adjustments."))}">◷ ${this.escape(__("Pending Adjustments"))}</button>
					<button type="button" data-prompt="${this.escape(__("Summarize upcoming payroll."))}">＄ ${this.escape(__("Upcoming Payroll"))}</button>
				</div>
			</div>`;
	},

	message_html(message) {
		const role = message.role === "user" ? "user" : "assistant";
		const blocks = Array.isArray(message.blocks) ? message.blocks : [];
		return `
			<article class="sp-ai__message sp-ai__message--${role}">
				<div class="sp-ai__avatar">${role === "user" ? this.escape((frappe.session.user_fullname || "U").charAt(0)) : "✦"}</div>
				<div class="sp-ai__message-body">
					${message.content ? `<div class="sp-ai__markdown">${this.markdown(message.content)}</div>` : ""}
					${blocks.map((block) => this.block_html(block)).join("")}
				</div>
			</article>`;
	},

	markdown(value) {
		let text = this.escape(value);
		text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
		text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
		text = text.replace(/(?:^|\n)- (.+)/g, "<br>• $1");
		return text.replace(/\n/g, "<br>");
	},

	block_html(block) {
		if (block.type === "table") {
			const columns = block.columns || [];
			return `<div class="sp-ai__table-wrap"><table><thead><tr>${columns.map((column) => `<th>${this.escape(column.label || column.key)}</th>`).join("")}</tr></thead>
				<tbody>${(block.rows || []).map((row) => `<tr>${columns.map((column) => `<td>${this.escape(row[column.key])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
		}
		if (block.type === "chart") {
			return `<div class="sp-ai__chart-card"><h4>${this.escape(block.title || "")}</h4><div class="sp-ai__chart" data-chart="${this.escape(JSON.stringify(block))}"></div></div>`;
		}
		if (block.type === "action") {
			const decided = block.status && block.status !== "pending";
			return `<div class="sp-ai__action ${decided ? "is-decided" : ""}">
				<div><span class="sp-ai__action-label">${this.escape(__("Confirmation required"))}</span><h4>${this.escape(block.title)}</h4><p>${this.escape(block.description)}</p></div>
				${decided ? `<strong>${this.escape(block.status === "approved" ? __("Completed") : block.status === "failed" ? __("Failed") : __("Cancelled"))}</strong>` : `
					<div class="sp-ai__action-buttons">
						<button type="button" class="btn btn-default" data-action-id="${this.escape(block.action_id)}" data-approved="0">${this.escape(__("Cancel"))}</button>
						<button type="button" class="btn btn-primary" data-action-id="${this.escape(block.action_id)}" data-approved="1">${this.escape(__("Confirm"))}</button>
					</div>`}
			</div>`;
		}
		if (block.type === "navigate") {
			return `<button type="button" class="sp-ai__navigate" data-route='${this.escape(JSON.stringify(block.route || []))}'>${this.escape(block.label || __("Open in Staff Pro"))} →</button>`;
		}
		if (block.type === "download") {
			const href = this.escape(block.file_url || "");
			const filename = this.escape(block.file_name || "");
			return `<a class="sp-ai__download" href="${href}" target="_blank" rel="noopener" download="${filename}">⬇ ${this.escape(block.label || __("Download"))}</a>`;
		}
		return block.content ? `<div class="sp-ai__markdown">${this.markdown(block.content)}</div>` : "";
	},

	mount_charts() {
		this.$body.find(".sp-ai__chart").each((_, element) => {
			const block = JSON.parse($(element).attr("data-chart") || "{}");
			if (typeof frappe.Chart !== "function") return;
			new frappe.Chart(element, {
				type: block.chart_type || "bar",
				height: 230,
				colors: block.colors || ["#7667ef", "#11a5dd", "#f2a7b8"],
				data: {
					labels: block.labels || [],
					datasets: block.datasets || [],
				},
			});
		});
	},

	server_error_message(error) {
		const raw = error?._server_messages;
		if (!raw) return "";
		try {
			const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
			return (Array.isArray(parsed) ? parsed : [parsed])
				.map((item) => {
					const row = typeof item === "string" ? JSON.parse(item) : item;
					return (row && (row.message || row.title)) || "";
				})
				.filter(Boolean)
				.join("\n");
		} catch (_error) {
			return "";
		}
	},

	render_error(error) {
		const server_message = this.server_error_message(error);
		if (server_message) {
			return;
		}
		const exception = String(error?.exception || "")
			.split("\n")
			.map((line) => line.trim())
			.filter(Boolean)
			.pop();
		const fallback = __("Ask AI is unavailable. Check System Settings > AI and try again.");
		const message = (exception || error?.message || fallback).toString().trim() || fallback;
		frappe.msgprint({ title: __("Ask AI"), message: this.escape(message), indicator: "red" });
	},
};
