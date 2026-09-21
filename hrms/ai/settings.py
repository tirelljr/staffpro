# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

import frappe
from frappe import _

PROVIDER_DEFAULTS = {
	"DeepSeek": {"model": "deepseek-chat", "api_base": "https://api.deepseek.com"},
	"OpenAI": {"model": "gpt-4.1-mini", "api_base": "https://api.openai.com/v1"},
	"Anthropic": {"model": "claude-sonnet-4-5", "api_base": ""},
	"Custom": {"model": "", "api_base": ""},
}

TOOL_PERMISSIONS = {
	"ask_ai_allow_employees": ("find_employees",),
	"ask_ai_allow_attendance": ("who_is_in", "attendance_hours"),
	"ask_ai_allow_overtime": ("overtime_summary",),
	"ask_ai_allow_agent_queries": ("list_agent_queries",),
	"ask_ai_allow_payroll": ("upcoming_payroll",),
	"ask_ai_allow_clock_adjustments": ("pending_clock_adjustments",),
	"ask_ai_allow_navigation": ("navigate_to_staff_pro",),
	"ask_ai_allow_floors": ("floor_map",),
	"ask_ai_allow_review_adjustments": ("review_time_clock_adjustment",),
	"ask_ai_allow_hours_comment": ("add_hours_comment",),
	"ask_ai_allow_hours_adjustment": ("add_hours_adjustment", "add_hours_entries", "set_clock_times"),
	"ask_ai_allow_book_time_off": ("book_time_off",),
	"ask_ai_allow_run_payroll": ("run_payroll",),
	"ask_ai_allow_respond_queries": ("respond_to_agent_query", "list_agent_queries"),
	"ask_ai_allow_floor_settings": ("update_floor_settings", "floor_map"),
	"ask_ai_allow_export": ("export_information",),
}


@dataclass(frozen=True)
class AssistantSettings:
	api_key: str
	provider: str = "DeepSeek"
	model: str = "deepseek-chat"
	api_base: str = "https://api.deepseek.com"
	temperature: float = 0
	max_tool_rounds: int = 6
	allowed_tools: frozenset[str] = field(default_factory=frozenset)


def _has_system_ai_fields() -> bool:
	return frappe.get_meta("System Settings").has_field("enable_ask_ai")


def _system_settings():
	return frappe.get_cached_doc("System Settings")


def is_ask_ai_enabled() -> bool:
	if _has_system_ai_fields():
		return bool(_system_settings().enable_ask_ai)
	if frappe.db.exists("DocType", "AI Settings"):
		return bool(frappe.get_cached_doc("AI Settings").enabled)
	return False


def allowed_tool_names() -> frozenset[str]:
	if not _has_system_ai_fields():
		return frozenset(name for names in TOOL_PERMISSIONS.values() for name in names)
	doc = _system_settings()
	allowed: set[str] = set()
	for fieldname, tools in TOOL_PERMISSIONS.items():
		if doc.get(fieldname):
			allowed.update(tools)
	return frozenset(allowed)


def assert_tool_allowed(name: str) -> None:
	if name not in allowed_tool_names():
		frappe.throw(_("Ask AI is not allowed to use {0}.").format(name), frappe.PermissionError)


def permission_field_for_tool(name: str) -> str | None:
	for fieldname, tools in TOOL_PERMISSIONS.items():
		if name in tools:
			return fieldname
	return None


def unlock_tool_permission(name: str) -> bool:
	"""Turn on the System Settings toolbox flag after an admin confirms a write."""
	if name in allowed_tool_names():
		return False
	fieldname = permission_field_for_tool(name)
	if not fieldname or not _has_system_ai_fields():
		return False
	if not frappe.get_meta("System Settings").has_field(fieldname):
		return False
	if frappe.db.get_single_value("System Settings", fieldname):
		return False
	frappe.db.set_single_value("System Settings", fieldname, 1)
	clear_assistant_cache()
	return True


def _password(doc, fieldname: str) -> str:
	if not getattr(doc, "name", None) or not doc.meta.has_field(fieldname):
		return ""
	return doc.get_password(fieldname, raise_exception=False) or ""


def get_assistant_settings(*, require_enabled: bool = True) -> AssistantSettings:
	if require_enabled and not is_ask_ai_enabled():
		frappe.throw(_("Ask AI is turned off. Enable it in System Settings > AI."))

	provider = "DeepSeek"
	model = "deepseek-chat"
	api_base = "https://api.deepseek.com"
	temperature = 0.0
	max_tool_rounds = 6
	api_key = ""

	if _has_system_ai_fields():
		doc = _system_settings()
		provider = (doc.ask_ai_provider or "DeepSeek").strip()
		model = (doc.ask_ai_model or "").strip()
		api_base = (doc.ask_ai_api_base or "").strip()
		temperature = float(doc.ask_ai_temperature or 0)
		max_tool_rounds = int(doc.ask_ai_max_tool_rounds or 6)
		api_key = _password(doc, "ask_ai_api_key")
	elif frappe.db.exists("DocType", "AI Settings"):
		legacy = frappe.get_cached_doc("AI Settings")
		model = (legacy.model or model).strip()
		api_base = (legacy.api_base or api_base).strip()
		temperature = float(legacy.temperature or 0)
		max_tool_rounds = int(legacy.max_tool_rounds or 6)
		api_key = _password(legacy, "deepseek_api_key")

	api_key = api_key or frappe.conf.get("deepseek_api_key") or frappe.conf.get("openai_api_key") or ""
	defaults = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["DeepSeek"])
	model = model or defaults["model"]
	api_base = api_base or defaults["api_base"]

	if not api_key:
		frappe.throw(_("Add an API key for {0} in System Settings > AI.").format(provider))
	if provider == "DeepSeek" and model == "deepseek-reasoner":
		frappe.throw(_("deepseek-reasoner cannot be used because Ask AI requires tool calling."))

	return AssistantSettings(
		api_key=api_key,
		provider=provider,
		model=model,
		api_base=api_base.rstrip("/"),
		temperature=temperature,
		max_tool_rounds=max(1, min(max_tool_rounds, 12)),
		allowed_tools=allowed_tool_names(),
	)


def validate_system_settings(doc, method: str | None = None) -> None:
	if not doc.meta.has_field("enable_ask_ai") or not doc.enable_ask_ai:
		return
	provider = (doc.ask_ai_provider or "DeepSeek").strip()
	if provider not in PROVIDER_DEFAULTS:
		frappe.throw(_("Select a valid Ask AI provider."))
	if provider == "DeepSeek" and (doc.ask_ai_model or "").strip() == "deepseek-reasoner":
		frappe.throw(_("Ask AI requires a DeepSeek model that supports tool calling. Use deepseek-chat."))
	api_base = (doc.ask_ai_api_base or "").strip()
	if api_base and urlparse(api_base).scheme not in {"http", "https"}:
		frappe.throw(_("API Base URL must be a valid HTTP or HTTPS URL."))
	rounds = int(doc.ask_ai_max_tool_rounds or 6)
	if not 1 <= rounds <= 12:
		frappe.throw(_("Maximum Tool Rounds must be between 1 and 12."))


def clear_assistant_cache(doc=None, method: str | None = None) -> None:
	frappe.clear_cache(doctype="System Settings")
