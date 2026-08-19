# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import Mock, patch

import frappe

from hrms.hr.teams_announce import (
	announce_to_teams,
	build_teams_payload,
	get_teams_channel,
	is_allowed_teams_webhook_url,
	save_teams_channel,
)
from hrms.tests.utils import HRMSTestSuite

VALID_WEBHOOK = "https://company.webhook.office.com/webhookb2/example"


class TestTeamsAnnounce(HRMSTestSuite):
	def test_allows_microsoft_webhook_hosts(self):
		self.assertTrue(is_allowed_teams_webhook_url(VALID_WEBHOOK))
		self.assertTrue(
			is_allowed_teams_webhook_url("https://prod-12.westus.logic.azure.com/workflows/abc")
		)
		self.assertTrue(
			is_allowed_teams_webhook_url(
				"https://default123.environment.api.powerplatform.com/powerautomate/automations/direct/workflows/abc"
			)
		)

	def test_rejects_unsafe_webhook_urls(self):
		self.assertFalse(is_allowed_teams_webhook_url("http://company.webhook.office.com/webhookb2/example"))
		self.assertFalse(is_allowed_teams_webhook_url("https://evil.example.com/hook"))
		self.assertFalse(is_allowed_teams_webhook_url("https://127.0.0.1/hook"))
		self.assertFalse(is_allowed_teams_webhook_url("https://company.webhook.office.com:8080/hook"))
		self.assertFalse(is_allowed_teams_webhook_url("https://user:pass@company.webhook.office.com/hook"))

	def test_payload_includes_text_and_adaptive_card(self):
		payload = build_teams_payload("Hello team", "Happy Birthday")
		self.assertEqual(payload["text"], "Hello team")
		self.assertEqual(payload["type"], "message")
		card = payload["attachments"][0]["content"]
		self.assertEqual(card["type"], "AdaptiveCard")
		self.assertEqual(card["body"][0]["text"], "Happy Birthday")
		self.assertEqual(card["body"][1]["text"], "Hello team")

	def test_saves_and_loads_user_channel(self):
		save_teams_channel("Celebrations", VALID_WEBHOOK)
		saved = get_teams_channel()
		self.assertEqual(saved["channel_name"], "Celebrations")
		self.assertEqual(saved["webhook_url"], VALID_WEBHOOK)

	def test_announce_rejects_unknown_host_without_posting(self):
		with patch("hrms.hr.teams_announce._post_json") as post_json:
			with self.assertRaises(frappe.ValidationError):
				announce_to_teams(message="Hello", webhook_url="https://evil.example.com/hook")
			post_json.assert_not_called()

	def test_announce_posts_message_card(self):
		ok = Mock(status_code=200)
		with patch("hrms.hr.teams_announce._post_json", return_value=ok) as post_json:
			result = announce_to_teams(
				message="🎂 Let's wish Ana a happy birthday!",
				webhook_url=VALID_WEBHOOK,
				channel_name="General",
				title="Happy Birthday, Ana Cruz",
				save_channel=1,
			)

		self.assertTrue(result["ok"])
		self.assertEqual(result["channel_name"], "General")
		post_json.assert_called_once()
		args = post_json.call_args
		self.assertEqual(args[0][0], VALID_WEBHOOK)
		self.assertEqual(args[0][1]["text"], "🎂 Let's wish Ana a happy birthday!")
		self.assertEqual(get_teams_channel()["channel_name"], "General")
