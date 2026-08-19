# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from urllib.parse import urlparse

import requests

import frappe
from frappe import _
from frappe.utils import cint

CHANNEL_NAME_KEY = "staff_pro_teams_channel_name"
WEBHOOK_URL_KEY = "staff_pro_teams_webhook_url"

ALLOWED_WEBHOOK_HOSTS = {
	"outlook.office.com",
	"webhook.office.com",
}

ALLOWED_WEBHOOK_HOST_SUFFIXES = (
	".webhook.office.com",
	".office.com",
	".office365.com",
	".logic.azure.com",
	".environment.api.powerplatform.com",
	".powerautomate.com",
	".api.powerplatform.com",
	".microsoft.com",
)


def is_allowed_teams_webhook_url(url: str) -> bool:
	"""Return True when the URL looks like a Microsoft Teams / Power Automate webhook."""
	if not url or not isinstance(url, str):
		return False

	url = url.strip()
	if not url.startswith("https://"):
		return False

	try:
		parsed = urlparse(url)
	except ValueError:
		return False

	host = (parsed.hostname or "").lower()
	if not host or parsed.username or parsed.password:
		return False

	if parsed.port not in (None, 443):
		return False

	if host in ALLOWED_WEBHOOK_HOSTS:
		return True

	return any(host.endswith(suffix) for suffix in ALLOWED_WEBHOOK_HOST_SUFFIXES)


def build_teams_payload(message: str, title: str | None = None) -> dict:
	"""Adaptive Card payload accepted by Teams incoming webhooks and Workflows."""
	body = []
	if title:
		body.append(
			{
				"type": "TextBlock",
				"text": title,
				"weight": "Bolder",
				"size": "Medium",
				"wrap": True,
			}
		)
	body.append(
		{
			"type": "TextBlock",
			"text": message,
			"wrap": True,
		}
	)
	return {
		"text": message,
		"type": "message",
		"attachments": [
			{
				"contentType": "application/vnd.microsoft.card.adaptive",
				"contentUrl": None,
				"content": {
					"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
					"type": "AdaptiveCard",
					"version": "1.4",
					"body": body,
				},
			}
		],
	}


def _user_default(key: str) -> str:
	value = frappe.defaults.get_user_default(key)
	if isinstance(value, list):
		value = value[0] if value else ""
	return (value or "").strip()


def _require_webhook_url(url: str) -> str:
	url = (url or "").strip()
	if not url:
		frappe.throw(_("Enter a Teams incoming webhook URL for the channel."))
	if not is_allowed_teams_webhook_url(url):
		frappe.throw(_("That does not look like a Microsoft Teams webhook URL."))
	return url


@frappe.whitelist()
def get_teams_channel() -> dict:
	"""Return the current user's saved Teams channel settings."""
	return {
		"channel_name": _user_default(CHANNEL_NAME_KEY),
		"webhook_url": _user_default(WEBHOOK_URL_KEY),
	}


@frappe.whitelist()
def save_teams_channel(channel_name: str, webhook_url: str) -> dict:
	"""Remember which Teams channel this user announces celebrations to."""
	channel_name = (channel_name or "").strip()
	webhook_url = _require_webhook_url(webhook_url)
	if not channel_name:
		frappe.throw(_("Enter the Teams channel name."))

	frappe.defaults.set_user_default(CHANNEL_NAME_KEY, channel_name)
	frappe.defaults.set_user_default(WEBHOOK_URL_KEY, webhook_url)
	return {"channel_name": channel_name, "webhook_url": webhook_url}


def _post_json(url: str, payload: dict):
	return requests.post(url, json=payload, timeout=15)


def post_teams_message(webhook_url: str, message: str, title: str | None = None):
	payload = build_teams_payload(message, title)
	response = _post_json(webhook_url, payload)
	if response.status_code >= 400:
		response = _post_json(webhook_url, {"text": message})
	if response.status_code >= 400:
		frappe.throw(_("Could not post to Teams. Check the webhook URL and try again."))
	return True


@frappe.whitelist()
def announce_to_teams(
	message: str,
	webhook_url: str | None = None,
	channel_name: str | None = None,
	title: str | None = None,
	save_channel: int | str = 0,
) -> dict:
	"""Post a celebration message to the user's Teams channel webhook."""
	message = (message or "").strip()
	if not message:
		frappe.throw(_("Enter a message to announce."))

	webhook_url = (webhook_url or "").strip() or _user_default(WEBHOOK_URL_KEY)
	webhook_url = _require_webhook_url(webhook_url)
	channel_name = (channel_name or "").strip() or _user_default(CHANNEL_NAME_KEY)

	if cint(save_channel):
		if not channel_name:
			frappe.throw(_("Enter the Teams channel name."))
		save_teams_channel(channel_name, webhook_url)

	post_teams_message(webhook_url, message, title)
	return {"ok": True, "channel_name": channel_name}
