# Copyright (c) 2026, Staff Pro BPO and Contributors
# License: GNU General Public License v3. See license.txt

import json
from unittest.mock import patch

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from hrms.ai.graph import run_agent
from hrms.ai.memory import get_user_memory
from hrms.ai.settings import assert_tool_allowed
from hrms.ai.tools import ALL_TOOLS
from hrms.ai.tools.actions import execute_write_action
from hrms.api.assistant import chat, confirm_action, delete_conversation, list_conversations


@tool
def sample_read_tool() -> str:
	"""Return a deterministic rich response for tests."""
	return '{"summary":"Two employees are in.","blocks":[{"type":"chart","labels":["In"],"datasets":[]}]}'


@tool
def sample_not_in_tool() -> str:
	"""Return people who are not clocked in."""
	return json.dumps(
		{
			"summary": "2 employee(s) not in.",
			"data": {
				"status": "out",
				"employees": ["HR-EMP-1", "HR-EMP-2"],
				"rows": [
					{"employee": "HR-EMP-1", "employee_name": "A", "status": "out"},
					{"employee": "HR-EMP-2", "employee_name": "B", "status": "out"},
				],
			},
			"blocks": [
				{
					"type": "table",
					"columns": [
						{"key": "employee_name", "label": "Employee"},
						{"key": "status", "label": "Status"},
					],
					"rows": [
						{"employee_name": "A", "status": "out"},
						{"employee_name": "B", "status": "out"},
					],
				}
			],
		}
	)


class FakeToolCallingModel:
	def __init__(self, responses):
		self.responses = iter(responses)

	def bind_tools(self, tools):
		self.tools = tools
		return self

	def invoke(self, messages):
		return next(self.responses)


class TestAskAIGraph(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_read_tool_path_returns_rich_blocks(self):
		model = FakeToolCallingModel(
			[
				AIMessage(
					content="",
					tool_calls=[{"name": "sample_read_tool", "args": {}, "id": "read-1"}],
				),
				AIMessage(content="Two employees are currently in."),
			]
		)
		with patch("hrms.ai.graph.get_enabled_tools", return_value=[sample_read_tool]):
			result = run_agent(
				[{"role": "user", "content": "Who is in?"}],
				model=model,
				tools=[sample_read_tool],
			)
		self.assertEqual(result["content"], "Two employees are currently in.")
		self.assertEqual(result["blocks"][0]["type"], "chart")

	def test_write_tool_stops_for_confirmation(self):
		model = FakeToolCallingModel(
			[
				AIMessage(
					content="",
					tool_calls=[
						{
							"name": "review_time_clock_adjustment",
							"args": {"name": "TCA-1", "action": "Approve", "comment": ""},
							"id": "write-1",
						}
					],
				)
			]
		)
		result = run_agent(
			[{"role": "user", "content": "Approve TCA-1"}],
			model=model,
			tools=ALL_TOOLS,
		)
		self.assertEqual(result["pending_action"]["tool"], "review_time_clock_adjustment")
		self.assertEqual(result["blocks"][-1]["status"], "pending")

	def test_disallowed_write_tool_is_blocked(self):
		with patch("hrms.ai.settings.allowed_tool_names", return_value=frozenset()):
			with self.assertRaises(frappe.PermissionError):
				assert_tool_allowed("review_time_clock_adjustment")

	def test_new_write_tools_stop_for_confirmation(self):
		model = FakeToolCallingModel(
			[
				AIMessage(
					content="",
					tool_calls=[
						{
							"name": "run_payroll",
							"args": {"payroll_frequency": "Weekly"},
							"id": "pay-1",
						}
					],
				)
			]
		)
		result = run_agent(
			[{"role": "user", "content": "Run weekly payroll"}],
			model=model,
			tools=ALL_TOOLS,
		)
		self.assertEqual(result["pending_action"]["tool"], "run_payroll")
		self.assertEqual(result["blocks"][-1]["status"], "pending")

	def test_multiple_write_tools_use_one_confirmation(self):
		model = FakeToolCallingModel(
			[
				AIMessage(
					content="",
					tool_calls=[
						{
							"name": "add_hours_adjustment",
							"args": {
								"employee": "HR-EMP-1",
								"attendance_date": "2026-09-21",
								"hours": 8,
								"comment": "Correction",
							},
							"id": "write-1",
						},
						{
							"name": "add_hours_adjustment",
							"args": {
								"employee": "HR-EMP-2",
								"attendance_date": "2026-09-21",
								"hours": 8,
								"comment": "Correction",
							},
							"id": "write-2",
						},
					],
				)
			]
		)
		result = run_agent(
			[{"role": "user", "content": "Add 8 hours for both people on 21 Sep"}],
			model=model,
			tools=ALL_TOOLS,
		)
		pending = result["pending_action"]
		self.assertEqual(pending["tool"], "bulk_actions")
		self.assertEqual(len(pending["arguments"]["actions"]), 2)
		self.assertEqual(result["blocks"][-1]["status"], "pending")

	def test_clock_times_for_a_group_use_one_confirmation(self):
		model = FakeToolCallingModel(
			[
				AIMessage(
					content="",
					tool_calls=[
						{
							"name": "add_hours_entries",
							"args": {
								"employees": "HR-EMP-1, HR-EMP-2, HR-EMP-3",
								"attendance_date": "2026-09-21",
								"in_time": "9:00 AM",
								"out_time": "5:00 PM",
								"comment": "Worked 9AM–5PM per HR correction.",
							},
							"id": "write-1",
						}
					],
				)
			]
		)
		result = run_agent(
			[{"role": "user", "content": "Set 9 to 5 for the team on 21 Sep"}],
			model=model,
			tools=ALL_TOOLS,
		)
		self.assertEqual(result["pending_action"]["tool"], "add_hours_entries")
		self.assertIn("3 employees", result["pending_action"]["description"])

	def test_parallel_read_tools_run_serially(self):
		@tool
		def sample_read_tool_a() -> str:
			return '{"summary":"A","blocks":[]}'

		@tool
		def sample_read_tool_b() -> str:
			return '{"summary":"B","blocks":[]}'

		model = FakeToolCallingModel(
			[
				AIMessage(
					content="",
					tool_calls=[
						{"name": "sample_read_tool_a", "args": {}, "id": "read-a"},
						{"name": "sample_read_tool_b", "args": {}, "id": "read-b"},
					],
				),
				AIMessage(content="Looked both up."),
			]
		)
		result = run_agent(
			[{"role": "user", "content": "Check both"}],
			model=model,
			tools=[sample_read_tool_a, sample_read_tool_b],
		)
		self.assertEqual(result["content"], "Looked both up.")

	def test_write_tools_stay_available_when_toggles_are_off(self):
		from hrms.ai.tools import get_enabled_tools

		with patch("hrms.ai.tools.allowed_tool_names", return_value=frozenset()):
			names = {item.name for item in get_enabled_tools()}
		self.assertIn("set_clock_times", names)
		self.assertIn("run_payroll", names)
		self.assertNotIn("find_employees", names)

	def test_set_clock_times_stops_for_confirmation(self):
		model = FakeToolCallingModel(
			[
				AIMessage(
					content="",
					tool_calls=[
						{
							"name": "set_clock_times",
							"args": {
								"employee": "Diego Lopez",
								"attendance_date": "2026-09-20",
								"in_time": "10:00 AM",
								"out_time": "4:00 PM",
							},
							"id": "clock-1",
						}
					],
				)
			]
		)
		result = run_agent(
			[{"role": "user", "content": "Change Diego Lopez to 10 AM - 4 PM today"}],
			model=model,
			tools=ALL_TOOLS,
		)
		self.assertEqual(result["pending_action"]["tool"], "set_clock_times")
		self.assertIn("Diego Lopez", result["pending_action"]["description"])

	def test_permission_map_covers_registered_tools(self):
		from hrms.ai.settings import TOOL_PERMISSIONS

		registered = {tool.name for tool in ALL_TOOLS}
		mapped = {name for names in TOOL_PERMISSIONS.values() for name in names}
		self.assertEqual(registered, mapped)

	def test_who_is_in_returns_compact_not_in_list(self):
		from hrms.ai.tools.attendance import who_is_in

		payload = {
			"date": "2026-09-21",
			"departments": ["Ops"],
			"totals": {"in_count": 1, "out_count": 2, "total": 3, "late": 0},
			"summary": [{"department": "Ops", "in_count": 1, "out_count": 2, "late": 0}],
			"details": [
				{
					"employee": "HR-EMP-1",
					"employee_name": "In Person",
					"department": "Ops",
					"status": "IN",
					"in_time": "9:00 AM",
					"out_time": "",
					"image": "data:image/png;base64,AAAA",
					"comments": ["note"] * 20,
					"adjustment": {"foo": "bar"},
				},
				{
					"employee": "HR-EMP-2",
					"employee_name": "Out Person",
					"department": "Ops",
					"status": "OUT",
					"in_time": "",
					"out_time": "",
				},
				{
					"employee": "HR-EMP-3",
					"employee_name": "Left Early",
					"department": "Ops",
					"status": "OUT",
					"in_time": "9:00 AM",
					"out_time": "1:00 PM",
				},
			],
		}
		with patch("hrms.ai.tools.attendance.get_in_out_today", return_value=payload):
			raw = who_is_in.invoke({"status": "out", "attendance_date": "2026-09-21"})
		data = json.loads(raw)
		self.assertEqual(data["data"]["employees"], ["HR-EMP-2", "HR-EMP-3"])
		self.assertNotIn("image", json.dumps(data["data"]))
		self.assertNotIn("comments", json.dumps(data["data"]))
		self.assertIn("not in", data["summary"])
		table = next(block for block in data["blocks"] if block.get("type") == "table")
		self.assertEqual([row["employee_name"] for row in table["rows"]], ["Out Person", "Left Early"])
		self.assertEqual(table["rows"][1]["out_time"], "1:00 PM")

	def test_mixed_lookup_and_write_opens_one_confirmation(self):
		model = FakeToolCallingModel(
			[
				AIMessage(
					content="",
					tool_calls=[
						{"name": "sample_not_in_tool", "args": {}, "id": "read-1"},
						{
							"name": "set_clock_times",
							"args": {
								"employees": "",
								"attendance_date": "2026-09-21",
								"in_time": "9:00 AM",
								"out_time": "5:00 PM",
							},
							"id": "write-1",
						},
					],
				)
			]
		)
		result = run_agent(
			[{"role": "user", "content": "Set 9 to 5 for people not in today"}],
			model=model,
			tools=[sample_not_in_tool, *ALL_TOOLS],
		)
		self.assertEqual(result["pending_action"]["tool"], "set_clock_times")
		self.assertIn("HR-EMP-1", result["pending_action"]["description"])
		self.assertIn("HR-EMP-2", result["pending_action"]["description"])
		self.assertEqual(result["pending_action"]["arguments"]["attendance_date"], str(getdate()))
		self.assertIn("not in", result["content"])
		self.assertEqual(result["blocks"][0]["type"], "table")
		self.assertEqual(result["blocks"][-1]["status"], "pending")

	def test_lookup_opens_clock_confirm_without_asking(self):
		model = FakeToolCallingModel(
			[
				AIMessage(
					content="",
					tool_calls=[{"name": "sample_not_in_tool", "args": {}, "id": "read-1"}],
				)
			]
		)
		result = run_agent(
			[
				{
					"role": "user",
					"content": "Set 9:00 AM to 5:00 PM on 21 Sep 2026 for those 14 employees not in today",
				}
			],
			model=model,
			tools=[sample_not_in_tool, *ALL_TOOLS],
		)
		self.assertEqual(result["pending_action"]["tool"], "set_clock_times")
		self.assertIn("HR-EMP-1", result["pending_action"]["description"])
		self.assertIn("9:00 AM", result["pending_action"]["description"])
		self.assertEqual(result["blocks"][-1]["status"], "pending")

	def test_utc_tomorrow_clock_date_coerces_to_site_today(self):
		from frappe.utils import add_days

		from hrms.ai.graph import coerce_attendance_date

		tomorrow = str(add_days(getdate(), 1))
		self.assertEqual(
			coerce_attendance_date(tomorrow, "set 9:00 AM to 5:00 PM for people not clocked in"),
			str(getdate()),
		)
		self.assertEqual(coerce_attendance_date(tomorrow, "set times for tomorrow"), tomorrow)
		self.assertEqual(
			coerce_attendance_date("2026-09-21", "Set 9:00 AM to 5:00 PM on 21 Sep 2026"),
			"2026-09-21",
		)

	def test_run_agent_errors_are_readable(self):
		class Boom(FakeToolCallingModel):
			def invoke(self, messages):
				raise RuntimeError("provider exploded")

		with self.assertRaises(frappe.ValidationError) as ctx:
			run_agent(
				[{"role": "user", "content": "Who is in?"}],
				model=Boom([]),
				tools=[sample_read_tool],
			)
		self.assertIn("Ask AI failed", str(ctx.exception))


class TestAskAIAPI(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.created = []
		if frappe.get_meta("System Settings").has_field("enable_ask_ai"):
			frappe.db.set_single_value("System Settings", "enable_ask_ai", 1)
			frappe.clear_cache(doctype="System Settings")

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in self.created:
			if frappe.db.exists("AI Conversation", name):
				frappe.delete_doc("AI Conversation", name, force=True, ignore_permissions=True)
		for memory_user in ("ask.ai.history@example.com", "ask.ai.delete@example.com"):
			if frappe.db.exists("AI User Memory", memory_user):
				frappe.delete_doc("AI User Memory", memory_user, force=True, ignore_permissions=True)

	def _pending_conversation(self):
		response = {
			"content": "Please confirm.",
			"blocks": [
				{
					"type": "action",
					"action_id": "action-1",
					"title": "Add hours comment",
					"description": "Attendance: ATT-1",
					"status": "pending",
				}
			],
			"pending_action": {
				"action_id": "action-1",
				"tool": "add_hours_comment",
				"arguments": {"name": "ATT-1", "comment": "Checked"},
				"title": "Add hours comment",
				"description": "Attendance: ATT-1",
			},
		}
		with patch("hrms.api.assistant.run_agent", return_value=response):
			payload = chat("Add a checked comment")
		self.created.append(payload["conversation"])
		return payload["conversation"]

	def test_confirm_executes_pending_action_once(self):
		name = self._pending_conversation()
		with patch("hrms.api.assistant.execute_write_action", return_value=None) as execute:
			payload = confirm_action(name, "action-1", 1)
		execute.assert_called_once()
		action = next(message for message in payload["messages"] if message["action_id"] == "action-1")
		self.assertEqual(action["action_status"], "approved")

	def test_yes_message_confirms_pending_action(self):
		name = self._pending_conversation()
		with patch("hrms.api.assistant.execute_write_action", return_value=None) as execute:
			with patch("hrms.api.assistant.run_agent") as agent:
				payload = chat("yes", conversation=name)
		execute.assert_called_once()
		agent.assert_not_called()
		action = next(message for message in payload["messages"] if message["action_id"] == "action-1")
		self.assertEqual(action["action_status"], "approved")

	def test_reject_does_not_execute_action(self):
		name = self._pending_conversation()
		with patch("hrms.api.assistant.execute_write_action") as execute:
			payload = confirm_action(name, "action-1", 0)
		execute.assert_not_called()
		action = next(message for message in payload["messages"] if message["action_id"] == "action-1")
		self.assertEqual(action["action_status"], "rejected")

	def test_user_can_delete_own_conversation(self):
		from hrms.ai.memory import get_last_conversation
		from hrms.api.assistant import get_conversation

		with patch("hrms.api.assistant.run_agent", return_value={"content": "Payroll summary.", "blocks": [], "pending_action": None}):
			payload = chat("Summarize upcoming payroll.")
		name = payload["conversation"]
		self.created.append(name)
		self.assertEqual(get_last_conversation(), name)
		self.assertTrue(any(row["name"] == name for row in list_conversations()["conversations"]))

		history = delete_conversation(name)
		self.assertFalse(any(row["name"] == name for row in history["conversations"]))
		self.assertFalse(frappe.db.exists("AI Conversation", name))
		self.assertIsNone(get_last_conversation())
		with self.assertRaises(frappe.DoesNotExistError):
			get_conversation(name)

	def test_user_cannot_delete_another_users_conversation(self):
		with patch("hrms.api.assistant.run_agent", return_value={"content": "Hello from admin.", "blocks": [], "pending_action": None}):
			admin_chat = chat("Admin only question")
		self.created.append(admin_chat["conversation"])

		other = "ask.ai.delete@example.com"
		if not frappe.db.exists("User", other):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": other,
					"first_name": "Ask",
					"last_name": "Delete",
					"send_welcome_email": 0,
				}
			)
			user.insert(ignore_permissions=True)
			user.add_roles("HR User")
			self.addCleanup(lambda: frappe.delete_doc("User", other, force=True, ignore_permissions=True))
		frappe.set_user(other)
		with self.assertRaises((frappe.PermissionError, frappe.DoesNotExistError)):
			delete_conversation(admin_chat["conversation"])
		frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists("AI Conversation", admin_chat["conversation"]))

	def test_guest_cannot_chat(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			chat("Show payroll")

	def test_history_and_memory_are_user_specific(self):
		from hrms.api.assistant import get_conversation

		with patch("hrms.api.assistant.run_agent", return_value={"content": "Hello from admin.", "blocks": [], "pending_action": None}):
			admin_chat = chat("Admin only question")
		self.created.append(admin_chat["conversation"])
		admin_history = list_conversations()
		self.assertEqual(admin_history["user"], "Administrator")
		self.assertTrue(any(row["name"] == admin_chat["conversation"] for row in admin_history["conversations"]))
		self.assertIn("Admin only question", get_user_memory("Administrator"))

		other = "ask.ai.history@example.com"
		if not frappe.db.exists("User", other):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": other,
					"first_name": "Ask",
					"last_name": "History",
					"send_welcome_email": 0,
				}
			)
			user.insert(ignore_permissions=True)
			user.add_roles("HR User")
			self.addCleanup(lambda: frappe.delete_doc("User", other, force=True, ignore_permissions=True))
		frappe.set_user(other)
		other_history = list_conversations()
		self.assertEqual(other_history["user"], other)
		self.assertFalse(any(row["name"] == admin_chat["conversation"] for row in other_history["conversations"]))
		self.assertFalse(get_user_memory())
		with self.assertRaises((frappe.PermissionError, frappe.DoesNotExistError)):
			get_conversation(admin_chat["conversation"])

		with patch("hrms.api.assistant.run_agent", return_value={"content": "Hello from other.", "blocks": [], "pending_action": None}):
			other_chat = chat("Other user question")
		self.created.append(other_chat["conversation"])
		self.assertIn("Other user question", get_user_memory())
		self.assertTrue(any(row["name"] == other_chat["conversation"] for row in list_conversations()["conversations"]))

		frappe.set_user("Administrator")
		admin_again = list_conversations()
		self.assertFalse(any(row["name"] == other_chat["conversation"] for row in admin_again["conversations"]))
		self.assertNotIn("Other user question", get_user_memory("Administrator"))

	def test_confirm_includes_download_block(self):
		name = self._pending_conversation()
		download = {
			"file_url": "/private/files/staff_pro_employees.csv",
			"file_name": "staff_pro_employees.csv",
			"blocks": [
				{
					"type": "download",
					"file_url": "/private/files/staff_pro_employees.csv",
					"file_name": "staff_pro_employees.csv",
					"label": "Download CSV",
				}
			],
		}
		with patch("hrms.api.assistant.execute_write_action", return_value=download):
			payload = confirm_action(name, "action-1", 1)
		blocks = payload["messages"][-1]["blocks"]
		self.assertEqual(blocks[0]["type"], "download")
		self.assertEqual(blocks[0]["file_name"], "staff_pro_employees.csv")

	def test_confirm_failed_action_stays_in_thread(self):
		name = self._pending_conversation()
		with patch(
			"hrms.api.assistant.execute_write_action",
			side_effect=frappe.ValidationError(
				"Ana Cruz already sits at San Ignacio - Downstairs row B seat 1"
			),
		):
			payload = confirm_action(name, "action-1", 1)
		action = next(message for message in payload["messages"] if message["action_id"] == "action-1")
		self.assertEqual(action["action_status"], "failed")
		self.assertIn("already sits", payload["messages"][-1]["content"])


class TestAskAIWriteActions(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.created_files = []

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in self.created_files:
			if name and frappe.db.exists("File", name):
				frappe.delete_doc("File", name, force=True)

	def test_respond_to_agent_query(self):
		from erpnext.setup.doctype.employee.test_employee import make_employee

		from hrms.hr.doctype.hr_request_type.hr_request_type import seed_hr_request_types

		seed_hr_request_types()
		employee = make_employee("ask.ai.query@example.com", company="_Test Company")
		request = frappe.get_doc(
			{
				"doctype": "HR Request",
				"employee": employee,
				"request_type": "Job Letter",
				"subject": "Need a job letter",
				"description": "Please issue a job letter.",
			}
		).insert()
		with patch("hrms.ai.settings.allowed_tool_names", return_value=frozenset({"respond_to_agent_query"})):
			execute_write_action(
				"respond_to_agent_query",
				{"name": request.name, "response": "Letter is ready.", "status": "Resolved"},
			)
		request.reload()
		self.assertEqual(request.status, "Resolved")
		self.assertEqual(request.resolution, "Letter is ready.")

	def test_update_floor_settings(self):
		floor_name = f"Ask AI Floor {frappe.generate_hash(length=8)}"
		frappe.get_doc({"doctype": "Office Floor", "floor_name": floor_name, "notes": "Old"}).insert()
		with patch("hrms.ai.settings.allowed_tool_names", return_value=frozenset({"update_floor_settings"})):
			execute_write_action(
				"update_floor_settings",
				{"action": "update_floor", "office_floor": floor_name, "notes": "Updated by Ask AI"},
			)
		self.assertEqual(frappe.db.get_value("Office Floor", floor_name, "notes"), "Updated by Ask AI")

	def test_assign_seat_moves_existing_employee(self):
		from erpnext.setup.doctype.employee.test_employee import make_employee

		employee = make_employee("ask.ai.seat@example.com", company="_Test Company")
		employee_name = frappe.db.get_value("Employee", employee, "employee_name")
		floor_name = f"Ask AI Seat {frappe.generate_hash(length=8)}"
		frappe.get_doc({"doctype": "Office Floor", "floor_name": floor_name}).insert()
		current = frappe.get_doc(
			{
				"doctype": "Cubicle",
				"office_floor": floor_name,
				"row": "B",
				"seat_number": 1,
				"employee": employee,
			}
		).insert()
		target = frappe.get_doc(
			{
				"doctype": "Cubicle",
				"office_floor": floor_name,
				"row": "C",
				"seat_number": 2,
			}
		).insert()
		with patch("hrms.ai.settings.allowed_tool_names", return_value=frozenset({"update_floor_settings"})):
			execute_write_action(
				"update_floor_settings",
				{
					"action": "assign_seat",
					"office_floor": floor_name,
					"row": "C",
					"seat_number": 2,
					"employee": employee_name,
				},
			)
			same_seat = execute_write_action(
				"update_floor_settings",
				{
					"action": "assign_seat",
					"office_floor": floor_name,
					"row": "C",
					"seat_number": 2,
					"employee": employee_name,
				},
			)
		current.reload()
		target.reload()
		self.assertFalse(current.employee)
		self.assertEqual(target.employee, employee)
		self.assertEqual(same_seat["name"], target.name)

	def test_export_employees_csv(self):
		from erpnext.setup.doctype.employee.test_employee import make_employee

		make_employee("ask.ai.export@example.com", company="_Test Company")
		with patch("hrms.ai.settings.allowed_tool_names", return_value=frozenset({"export_information"})):
			result = execute_write_action(
				"export_information",
				{"dataset": "employees", "file_format": "csv"},
			)
		self.assertTrue(result["file_name"].endswith(".csv"))
		self.assertEqual(result["blocks"][0]["type"], "download")
		file_name = frappe.db.get_value("File", {"file_url": result["file_url"]})
		self.created_files.append(file_name)

	def test_add_hours_entries_updates_a_group(self):
		from erpnext.setup.doctype.employee.test_employee import make_employee

		from frappe.utils import flt

		from hrms.ai.tools.common import parse_name_list

		first = make_employee("ask.ai.bulk1@example.com", company="_Test Company")
		second = make_employee("ask.ai.bulk2@example.com", company="_Test Company")
		self.assertEqual(parse_name_list(f"{first}, {second}"), [first, second])
		with patch("hrms.ai.settings.allowed_tool_names", return_value=frozenset({"add_hours_entries"})):
			created = execute_write_action(
				"add_hours_entries",
				{
					"employees": f"{first}, {second}",
					"attendance_date": "2026-09-21",
					"in_time": "9:00 AM",
					"out_time": "5:00 PM",
					"comment": "Worked 9AM–5PM per HR correction.",
				},
			)
		self.assertEqual(len(created), 2)
		hours = frappe.get_all(
			"Attendance",
			filters={"name": ["in", created]},
			pluck="working_hours",
		)
		self.assertTrue(all(flt(value) >= 7 for value in hours))

	def test_run_payroll_is_permission_gated(self):
		with patch("hrms.ai.settings.allowed_tool_names", return_value=frozenset()):
			with self.assertRaises(frappe.PermissionError):
				execute_write_action("run_payroll", {"payroll_frequency": "Weekly"})

