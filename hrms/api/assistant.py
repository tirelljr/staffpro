# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cstr, getdate, now_datetime, strip_html

from hrms.ai.graph import run_agent
from hrms.ai.memory import clear_last_conversation, get_last_conversation, get_user_memory, remember_exchange
from hrms.ai.permissions import ensure_ai_access, ensure_conversation_access
from hrms.ai.tools import execute_write_action


def _normalized_reply(message: str) -> str:
	return strip_html(message or "").strip().lower().rstrip(".!?").strip()


_AFFIRM_REPLIES = frozenset(
	{
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
		"make the change",
		"apply",
		"apply it",
		"approve",
	}
)
_DENY_REPLIES = frozenset(
	{
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
	}
)


def _pending_message_row(doc):
	for row in reversed(list(doc.messages or [])):
		if row.action_status == "pending" and row.action_id:
			return row
	return None


def _loads(value: str | None, fallback):
	if not value:
		return fallback
	try:
		return json.loads(value)
	except (TypeError, ValueError):
		return fallback


def _dumps(value: Any) -> str:
	return json.dumps(value, default=str, ensure_ascii=False)


def _exception_message(exc: Exception) -> str:
	messages = []
	for item in list(getattr(frappe, "message_log", None) or []):
		if isinstance(item, str):
			try:
				item = json.loads(item)
			except (TypeError, ValueError):
				messages.append(item)
				continue
		if isinstance(item, dict):
			text = item.get("message") or item.get("title")
			if text:
				messages.append(cstr(text))
		elif item:
			messages.append(cstr(item))
	text = "\n".join(part for part in messages if part).strip()
	if not text:
		text = cstr(getattr(exc, "message", None) or exc)
	text = strip_html(text).strip()
	return text or _("That action could not be completed.")


def _result_blocks(result: Any) -> list:
	if isinstance(result, str):
		result = _loads(result, {})
	if isinstance(result, dict) and isinstance(result.get("blocks"), list):
		return result["blocks"]
	return []


def _message_dict(row) -> dict:
	blocks = _loads(row.blocks_json, [])
	if row.action_id:
		for block in blocks:
			if block.get("type") == "action" and block.get("action_id") == row.action_id:
				block["status"] = row.action_status or "pending"
	return {
		"name": row.name,
		"role": row.role,
		"content": row.content or "",
		"blocks": blocks,
		"action_id": row.action_id,
		"action_status": row.action_status,
		"creation": row.creation,
	}


def _conversation_dict(doc) -> dict:
	return {
		"name": doc.name,
		"title": doc.title,
		"last_message_at": doc.last_message_at,
		"messages": [_message_dict(row) for row in doc.messages],
	}


def _new_conversation(title: str | None = None):
	doc = frappe.new_doc("AI Conversation")
	doc.user = frappe.session.user
	doc.owner = frappe.session.user
	doc.title = (strip_html(title or "").strip() or _("New conversation"))[:140]
	doc.last_message_at = now_datetime()
	doc.insert()
	return doc


def _owned_conversations() -> list[dict]:
	user = frappe.session.user
	fields = ["name", "title", "last_message_at", "modified", "owner"]
	kwargs = {
		"order_by": "last_message_at desc, modified desc",
		"limit_page_length": 100,
		"ignore_permissions": True,
	}
	if frappe.get_meta("AI Conversation").has_field("user"):
		fields.append("user")
		kwargs["or_filters"] = {"user": user, "owner": user}
	else:
		kwargs["filters"] = {"owner": user}
	rows = []
	seen = set()
	for row in frappe.get_all("AI Conversation", fields=fields, **kwargs):
		name = row.get("name")
		owner = row.get("user") or row.get("owner")
		if owner != user or name in seen:
			continue
		seen.add(name)
		rows.append(
			{
				"name": name,
				"title": row.get("title"),
				"last_message_at": row.get("last_message_at"),
				"modified": row.get("modified"),
			}
		)
	return rows


@frappe.whitelist()
def list_conversations() -> dict:
	ensure_ai_access()
	rows = _owned_conversations()
	today = getdate()
	for row in rows:
		day = getdate(row.get("last_message_at") or row.get("modified"))
		delta = (today - day).days
		row["group"] = "Today" if delta <= 0 else "Yesterday" if delta == 1 else "Older"
	last = get_last_conversation()
	if last and last not in {row["name"] for row in rows}:
		last = None
	return {
		"conversations": rows,
		"user": frappe.session.user,
		"last_conversation": last,
	}


@frappe.whitelist()
def get_conversation(name: str) -> dict:
	doc = ensure_conversation_access(name)
	return _conversation_dict(doc)


@frappe.whitelist()
def create_conversation(title: str | None = None) -> dict:
	ensure_ai_access()
	return _conversation_dict(_new_conversation(title))


@frappe.whitelist()
def delete_conversation(name: str) -> dict:
	doc = ensure_conversation_access(name)
	doc.check_permission("delete")
	clear_last_conversation(name)
	frappe.delete_doc("AI Conversation", doc.name, force=True)
	return list_conversations()


@frappe.whitelist()
def chat(message: str, conversation: str | None = None) -> dict:
	ensure_ai_access()
	message = strip_html(message or "").strip()
	if not message:
		frappe.throw(_("Enter a message for Ask AI."))
	if len(message) > 4000:
		frappe.throw(_("Messages cannot exceed 4,000 characters."))

	doc = ensure_conversation_access(conversation) if conversation else _new_conversation(message[:80])
	doc.check_permission("write")
	pending_row = _pending_message_row(doc) if conversation else None
	reply = _normalized_reply(message)
	if pending_row and reply in _AFFIRM_REPLIES:
		return confirm_action(doc.name, pending_row.action_id, 1)
	if pending_row and reply in _DENY_REPLIES:
		return confirm_action(doc.name, pending_row.action_id, 0)

	history = [{"role": row.role, "content": row.content or ""} for row in doc.messages]
	agent_message = message
	if reply in _AFFIRM_REPLIES:
		agent_message = (
			f"{message}\n\nThe user confirmed. Call the write tool now using the people from the previous lookup. "
			"Do not ask for confirmation in chat."
		)
	history.append({"role": "user", "content": agent_message})
	try:
		response = run_agent(history, memory=get_user_memory())
	except frappe.ValidationError:
		raise
	except Exception as exc:
		frappe.log_error(title="Ask AI", message=frappe.get_traceback())
		frappe.throw(_(_exception_message(exc)), title=_("Ask AI"))

	doc.append("messages", {"role": "user", "content": message, "blocks_json": "[]"})
	assistant_row = doc.append(
		"messages",
		{
			"role": "assistant",
			"content": response["content"],
			"blocks_json": _dumps(response.get("blocks") or []),
		},
	)
	if response.get("pending_action"):
		pending = response["pending_action"]
		assistant_row.action_id = pending["action_id"]
		assistant_row.action_status = "pending"
		assistant_row.pending_action_json = _dumps(pending)
	doc.last_message_at = now_datetime()
	doc.save()
	remember_exchange(doc.title, message, response["content"], conversation=doc.name)
	payload = _conversation_dict(doc)
	payload["conversation"] = doc.name
	return payload


@frappe.whitelist()
def confirm_action(conversation: str, action_id: str, approved: int | str | bool) -> dict:
	ensure_ai_access()
	doc = ensure_conversation_access(conversation)
	doc.check_permission("write")
	row = next((item for item in doc.messages if item.action_id == action_id), None)
	if not row:
		frappe.throw(_("This Ask AI action could not be found."))
	if row.action_status != "pending":
		frappe.throw(_("This action has already been decided."))

	is_approved = str(approved).lower() in {"1", "true", "yes"}
	row.confirmed_by = frappe.session.user
	row.confirmed_on = now_datetime()
	if not is_approved:
		row.action_status = "rejected"
		doc.append(
			"messages",
			{
				"role": "assistant",
				"content": _("Cancelled. No changes were made."),
				"blocks_json": "[]",
			},
		)
	else:
		pending = _loads(row.pending_action_json, {})
		if not pending.get("tool"):
			frappe.throw(_("This action is missing its execution details."))
		try:
			result = execute_write_action(
				pending["tool"],
				pending.get("arguments") or {},
				conversation=doc.name,
			)
		except Exception as exc:
			row.action_status = "failed"
			doc.append(
				"messages",
				{
					"role": "assistant",
					"content": _exception_message(exc),
					"blocks_json": "[]",
				},
			)
			frappe.clear_messages()
			if getattr(frappe.local, "response", None) is not None:
				frappe.local.response.pop("http_status_code", None)
		else:
			row.action_status = "approved"
			row.action_result_json = _dumps(result)
			content = _("Completed **{0}** successfully.").format(pending.get("title") or _("action"))
			if isinstance(result, dict) and result.get("toolbox_enabled"):
				content = f"{content} {_('This action is now available in the Ask AI toolbox.')}"
			doc.append(
				"messages",
				{
					"role": "assistant",
					"content": content,
					"blocks_json": _dumps(_result_blocks(result)),
				},
			)
	doc.last_message_at = now_datetime()
	doc.save()
	follow_up = next((item.content for item in reversed(doc.messages) if item.role == "assistant"), "")
	remember_exchange(doc.title, "", follow_up or "", conversation=doc.name)
	return _conversation_dict(doc)
