# Copyright (c) 2026, Staff Pro BPO and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint, flt, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.attendance.attendance import add_hours_entry, approve_hours_entries, get_hours_rows
from hrms.payroll.daily_pay import get_hour_rate, pair_checkin_logs
from hrms.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure
from hrms.tests.utils import HRMSTestSuite


class TestDailyPay(HRMSTestSuite):
	def test_hour_rate_from_structure_and_daily_pay(self):
		employee = make_employee("test_daily_pay_rate@example.com", company="_Test Company")
		make_salary_structure(
			"Daily Pay Hourly Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date=nowdate(),
			base=500,
			other_details={"hour_rate": 12.5},
		)

		self.assertEqual(flt(get_hour_rate(employee, nowdate()), 2), 12.5)

		name = add_hours_entry(employee, nowdate(), "09:00:00", "17:00:00")
		doc = frappe.get_doc("Attendance", name)
		self.assertEqual(flt(doc.working_hours), 8)
		self.assertEqual(flt(doc.daily_pay), 100)
		self.assertFalse(cint_hours_paid(doc))

		rows = get_hours_rows(from_date=nowdate(), to_date=nowdate(), employee=employee)
		self.assertEqual(len(rows["rows"]), 1)
		self.assertEqual(rows["rows"][0]["kind"], "pair")
		self.assertEqual(flt(rows["rows"][0]["daily_pay"]), 100)
		self.assertIn("ss_deduction", rows["rows"][0])
		self.assertEqual(rows["rows"][0]["unpaid"], 8)
		self.assertEqual(rows["rows"][0]["paid"], 0)
		self.assertEqual(rows["approval"], "Not Approved Yet")

		self.assertEqual(approve_hours_entries([name]).get("approved"), [name])
		rows = get_hours_rows(from_date=nowdate(), to_date=nowdate(), employee=employee)
		self.assertEqual(rows["rows"][0]["paid"], 8)
		self.assertEqual(rows["rows"][0]["unpaid"], 0)
		self.assertEqual(rows["approval"], "Approved")

	def test_hour_rate_from_weekly_base(self):
		employee = make_employee("test_daily_pay_base@example.com", company="_Test Company")
		make_salary_structure(
			"Daily Pay Base Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date=nowdate(),
			base=400,
			other_details={"hour_rate": 0},
		)
		self.assertEqual(flt(get_hour_rate(employee, nowdate()), 2), 10)

	def test_ss_is_weekly_not_per_punch(self):
		from frappe.utils import add_days, get_first_day_of_week, getdate

		employee = make_employee("test_weekly_ss_hours@example.com", company="_Test Company")
		make_salary_structure(
			"Weekly SS Hours Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date=nowdate(),
			base=500,
			other_details={"hour_rate": 12.5},
		)
		week_start = getdate(get_first_day_of_week(nowdate()))
		day_two = add_days(week_start, 1)
		add_hours_entry(employee, week_start, "09:00:00", "17:00:00")
		add_hours_entry(employee, day_two, "09:00:00", "17:00:00")

		payload = get_hours_rows(from_date=week_start, to_date=day_two, employee=employee)
		self.assertEqual(len(payload["rows"]), 2)
		self.assertEqual(flt(payload["rows"][0]["daily_pay"]), 100)
		self.assertEqual(flt(payload["rows"][1]["daily_pay"]), 100)
		self.assertEqual(flt(payload["rows"][0]["ss_deduction"]), 0)
		self.assertEqual(flt(payload["rows"][1]["ss_deduction"]), 0)
		self.assertEqual(flt(payload["rows"][0]["week_ss"]), 5.94)
		self.assertEqual(flt(payload["rows"][1]["week_ss"]), 5.94)
		self.assertEqual(flt(payload["totals"]["ss_deduction"]), 5.94)
		self.assertEqual(flt(payload["totals"]["daily_pay"]), 200)
		self.assertEqual(flt(payload["totals"]["net_daily_pay"]), 194.06)

		one_day = get_hours_rows(from_date=week_start, to_date=week_start, employee=employee)
		self.assertEqual(flt(one_day["totals"]["ss_deduction"]), 5.94)
		self.assertEqual(flt(one_day["totals"]["daily_pay"]), 100)
		self.assertEqual(flt(one_day["totals"]["net_daily_pay"]), 94.06)

	def test_lunch_punch_adds_paid_hour_and_extra_row(self):
		employee = make_employee("test_lunch_pairs@example.com", company="_Test Company")
		make_salary_structure(
			"Lunch Pair Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date=nowdate(),
			base=500,
			other_details={"hour_rate": 12.5},
		)
		day = nowdate()
		first = add_hours_entry(employee, day, "09:00:00", "12:00:00")
		second = add_hours_entry(employee, day, "13:00:00", "17:00:00")
		self.assertEqual(first, second)

		doc = frappe.get_doc("Attendance", first)
		self.assertEqual(flt(doc.working_hours), 8)  # 3 + 4 + 1 lunch
		self.assertEqual(flt(doc.daily_pay), 100)

		payload = get_hours_rows(from_date=day, to_date=day, employee=employee)
		kinds = [row["kind"] for row in payload["rows"]]
		self.assertEqual(len(payload["rows"]), 3)
		self.assertEqual(kinds.count("pair"), 2)
		self.assertEqual(kinds.count("lunch"), 1)
		self.assertEqual(flt(payload["totals"]["total"]), 8)
		self.assertEqual(flt(payload["totals"]["daily_pay"]), 100)
		lunch = next(row for row in payload["rows"] if row["kind"] == "lunch")
		self.assertEqual(flt(lunch["working_hours"]), 1)
		self.assertEqual(lunch["status"], "Lunch")
		self.assertFalse(lunch.get("in_log"))

	def test_open_in_pair_has_no_lunch(self):
		employee = make_employee("test_open_in_pair@example.com", company="_Test Company")
		day = nowdate()
		name = add_hours_entry(employee, day, "09:00:00", working_now=1)
		doc = frappe.get_doc("Attendance", name)
		self.assertEqual(flt(doc.working_hours), 0)
		self.assertTrue(doc.in_time)
		self.assertFalse(doc.out_time)

		payload = get_hours_rows(from_date=day, to_date=day, employee=employee)
		self.assertEqual(len(payload["rows"]), 1)
		self.assertEqual(payload["rows"][0]["kind"], "pair")
		self.assertEqual(flt(payload["rows"][0]["working_hours"]), 0)
		self.assertTrue(payload["rows"][0].get("in_log"))
		self.assertFalse(payload["rows"][0].get("out_log"))

	def test_pair_checkin_logs_helper(self):
		logs = [
			frappe._dict(name="in1", log_type="IN", time="2026-08-13 09:00:00"),
			frappe._dict(name="out1", log_type="OUT", time="2026-08-13 12:00:00"),
			frappe._dict(name="in2", log_type="IN", time="2026-08-13 13:00:00"),
			frappe._dict(name="out2", log_type="OUT", time="2026-08-13 17:00:00"),
		]
		result = pair_checkin_logs(logs)
		self.assertEqual(len(result["pairs"]), 2)
		self.assertEqual(flt(result["pair_hours"]), 7)
		self.assertEqual(flt(result["lunch_hours"]), 1)
		self.assertEqual(flt(result["working_hours"]), 8)

		single = pair_checkin_logs(logs[:2])
		self.assertEqual(flt(single["lunch_hours"]), 0)
		self.assertEqual(flt(single["working_hours"]), 3)

	def test_hours_between_from_in_and_out_clocks(self):
		from datetime import datetime, timedelta

		from hrms.payroll.daily_pay import _hours_between, ensure_working_hours_from_times

		start = datetime(2026, 8, 21, 13, 0, 0)
		end = datetime(2026, 8, 21, 17, 0, 0)
		self.assertEqual(flt(_hours_between(start, end)), 4)
		self.assertEqual(flt(_hours_between("2026-08-21 09:00:00", "2026-08-21 12:00:00")), 3)
		self.assertEqual(flt(_hours_between(timedelta(hours=9), timedelta(hours=17))), 8)

		as_datetimes = [
			frappe._dict(name="in1", log_type="IN", time=datetime(2026, 8, 21, 13, 0, 0)),
			frappe._dict(name="out1", log_type="OUT", time=datetime(2026, 8, 21, 17, 0, 0)),
		]
		from hrms.payroll.daily_pay import pair_checkin_logs

		self.assertEqual(flt(pair_checkin_logs(as_datetimes)["working_hours"]), 4)

		doc = frappe._dict(status="Present", working_hours=0, in_time=start, out_time=end)
		self.assertEqual(flt(ensure_working_hours_from_times(doc)), 4)
		self.assertEqual(flt(doc.working_hours), 4)

	def test_seed_day_hours_creates_lunch_rows_and_ss(self):
		from hrms.import_hr_demo_data import _seed_day_hours
		from hrms.payroll.social_security import seed_belize_ssb_2022_table

		seed_belize_ssb_2022_table()
		employee = make_employee("test_seed_week_hours@example.com", company="_Test Company")
		make_salary_structure(
			"Seed Hours Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date=nowdate(),
			base=500,
			other_details={"hour_rate": 12.5},
		)
		self.assertTrue(
			_seed_day_hours(
				employee,
				nowdate(),
				[("09:00:00", "IN"), ("12:00:00", "OUT"), ("13:00:00", "IN"), ("17:00:00", "OUT")],
			)
		)
		payload = get_hours_rows(from_date=nowdate(), to_date=nowdate(), employee=employee)
		kinds = [row["kind"] for row in payload["rows"]]
		self.assertEqual(kinds.count("pair"), 2)
		self.assertEqual(kinds.count("lunch"), 1)
		self.assertEqual(flt(payload["totals"]["total"]), 8)
		self.assertEqual(flt(payload["totals"]["daily_pay"]), 100)
		self.assertEqual(flt(payload["totals"]["ss_deduction"]), 1.69)
		self.assertEqual(flt(payload["totals"]["net_daily_pay"]), 98.31)

	def test_hours_rows_keep_pay_when_hour_rate_missing(self):
		employee = make_employee("test_dayview_missing_rate@example.com", company="_Test Company")
		make_salary_structure(
			"Day View Missing Rate Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date=nowdate(),
			base=500,
			other_details={"hour_rate": 12.5},
		)
		name = add_hours_entry(employee, nowdate(), "09:00:00", "12:00:00")
		add_hours_entry(employee, nowdate(), "13:00:00", "17:00:00")
		frappe.db.set_value("Attendance", name, {"hour_rate": 0, "daily_pay": 0, "net_daily_pay": 0})
		frappe.flags.hour_rate_cache = {}

		payload = get_hours_rows(from_date=nowdate(), to_date=nowdate(), employee=employee)
		self.assertEqual(flt(payload["totals"]["total"]), 8)
		self.assertEqual(flt(payload["totals"]["daily_pay"]), 100)
		self.assertGreater(flt(payload["totals"]["ss_deduction"]), 0)
		self.assertEqual(
			flt(payload["totals"]["net_daily_pay"]),
			flt(payload["totals"]["daily_pay"] - payload["totals"]["ss_deduction"] - payload["totals"]["tax_deduction"], 2),
		)

	def test_hours_rows_preserve_stored_daily_pay(self):
		employee = make_employee("test_dayview_stored_pay@example.com", company="_Test Company")
		name = add_hours_entry(employee, nowdate(), "09:00:00", "12:00:00")
		add_hours_entry(employee, nowdate(), "13:00:00", "17:00:00")
		frappe.db.set_value("Attendance", name, {"hour_rate": 0, "daily_pay": 80, "net_daily_pay": 80})
		frappe.flags.hour_rate_cache = {}

		payload = get_hours_rows(from_date=nowdate(), to_date=nowdate(), employee=employee)
		self.assertEqual(flt(payload["totals"]["daily_pay"]), 80)

	def test_belize_easter_weekend_2026(self):
		from hrms.hr.belize_holidays import get_belize_holidays

		by_desc = {row["description"]: row["holiday_date"] for row in get_belize_holidays(2026)}
		self.assertEqual(str(by_desc["Good Friday"]), "2026-04-03")
		self.assertEqual(str(by_desc["Holy Saturday"]), "2026-04-04")
		self.assertEqual(str(by_desc["Easter Monday"]), "2026-04-06")

	def test_holiday_pay_unworked_and_premiums(self):
		from frappe.utils import get_year_ending, get_year_start, getdate

		from hrms.hr.doctype.holiday_list_assignment.test_holiday_list_assignment import (
			create_holiday_list_assignment,
		)
		from hrms.payroll.daily_pay import calculate_holiday_daily_pay, ensure_paid_holiday_attendance
		from hrms.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list
		from hrms.patches.v16_0.seed_belize_holidays_and_pay_fields import _holiday_list_pay_fields
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		create_custom_fields(_holiday_list_pay_fields(), update=True)
		frappe.clear_cache(doctype="Holiday List")

		holiday_date = getdate("2026-09-21")  # Independence Day (Mon)
		list_name = make_holiday_list(
			"Holiday Pay Test List",
			from_date=get_year_start(holiday_date),
			to_date=get_year_ending(holiday_date),
			add_weekly_offs=True,
		)
		doc = frappe.get_doc("Holiday List", list_name)
		if not any(getdate(h.holiday_date) == holiday_date and not cint(h.weekly_off) for h in doc.holidays):
			doc.append(
				"holidays",
				{
					"holiday_date": holiday_date,
					"description": "Independence Day",
					"weekly_off": 0,
				},
			)
			doc.save()

		employee = make_employee("test_holiday_pay@example.com", company="_Test Company")
		create_holiday_list_assignment("Employee", employee, list_name)
		make_salary_structure(
			"Holiday Pay Structure",
			"Weekly",
			employee=employee,
			company="_Test Company",
			from_date=get_year_start(holiday_date),
			base=500,
			other_details={"hour_rate": 12.5},
		)

		# Unworked holiday → 8 × rate (even if time-and-a-half is on)
		frappe.db.set_value("Holiday List", list_name, {"pay_time_and_a_half": 1, "pay_double_time": 0})
		created = ensure_paid_holiday_attendance(holiday_date, holiday_date, employee=employee)
		self.assertTrue(created)
		att = frappe.get_doc("Attendance", created[0])
		self.assertEqual(flt(att.working_hours), 8)
		self.assertEqual(flt(att.daily_pay), 100)

		# Worked 8h, both toggles off → max(8, hours) × rate = 100
		frappe.db.set_value("Holiday List", list_name, {"pay_time_and_a_half": 0, "pay_double_time": 0})
		frappe.delete_doc("Attendance", att.name, force=1)
		name = add_hours_entry(employee, holiday_date, "09:00:00", "17:00:00")
		att = frappe.get_doc("Attendance", name)
		self.assertEqual(flt(att.daily_pay), 100)

		# Worked 8h, time and a half → 100 + 50 = 150
		frappe.db.set_value("Holiday List", list_name, {"pay_time_and_a_half": 1, "pay_double_time": 0})
		att.reload()
		att.save()
		att.reload()
		self.assertEqual(flt(att.daily_pay), 150)

		# Worked 8h, double time → 100 + 100 = 200
		frappe.db.set_value("Holiday List", list_name, {"pay_time_and_a_half": 0, "pay_double_time": 1})
		att.reload()
		att.save()
		att.reload()
		self.assertEqual(flt(att.daily_pay), 200)

		# Worked 4h, time and a half → 100 + 25 = 125
		self.assertEqual(flt(calculate_holiday_daily_pay(12.5, 4, 0.5)), 125)
		frappe.db.set_value("Holiday List", list_name, {"pay_time_and_a_half": 1, "pay_double_time": 0})
		frappe.delete_doc("Attendance", att.name, force=1)
		short_name = add_hours_entry(employee, holiday_date, "09:00:00", "13:00:00")
		short_att = frappe.get_doc("Attendance", short_name)
		self.assertEqual(flt(short_att.working_hours), 4)
		self.assertEqual(flt(short_att.daily_pay), 125)

		# Sunday weekly off with toggle on → regular rate × hours (no premium / no 8h gift)
		sunday = getdate("2026-09-20")  # Sunday
		frappe.db.set_value("Holiday List", list_name, {"pay_time_and_a_half": 0, "pay_double_time": 1})
		sun_name = add_hours_entry(employee, sunday, "09:00:00", "17:00:00")
		sun_att = frappe.get_doc("Attendance", sun_name)
		self.assertEqual(flt(sun_att.daily_pay), 100)

		# Both toggles cannot be saved on at once
		doc = frappe.get_doc("Holiday List", list_name)
		doc.pay_time_and_a_half = 1
		doc.pay_double_time = 1
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_holiday_list_toggles_mutually_exclusive_validate(self):
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
		from frappe.utils import get_year_ending, get_year_start, getdate

		from hrms.patches.v16_0.seed_belize_holidays_and_pay_fields import _holiday_list_pay_fields
		from hrms.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list

		create_custom_fields(_holiday_list_pay_fields(), update=True)
		frappe.clear_cache(doctype="Holiday List")
		list_name = make_holiday_list(
			"Holiday Toggle Validate List",
			from_date=get_year_start(getdate()),
			to_date=get_year_ending(getdate()),
			add_weekly_offs=False,
		)
		doc = frappe.get_doc("Holiday List", list_name)
		doc.pay_time_and_a_half = 1
		doc.pay_double_time = 1
		with self.assertRaises(frappe.ValidationError):
			doc.save()


def cint_hours_paid(doc):
	return int(doc.get("hours_paid") or 0)
