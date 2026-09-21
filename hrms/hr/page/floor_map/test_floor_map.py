# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.page.floor_map.floor_map import assign_cubicle, get_employee_workstation
from hrms.tests.utils import HRMSTestSuite


class TestFloorMap(HRMSTestSuite):
	def test_employee_workstation_returns_cubicle_device(self):
		employee = make_employee("floor.device@example.com", company="_Test Company")
		floor_name = f"Floor Device {frappe.generate_hash(length=8)}"
		frappe.get_doc({"doctype": "Office Floor", "floor_name": floor_name}).insert()
		frappe.get_doc(
			{
				"doctype": "Cubicle",
				"office_floor": floor_name,
				"row": "B",
				"seat_number": 2,
				"employee": employee,
				"device_id": "real-device-22",
			}
		).insert()

		result = get_employee_workstation(employee)
		self.assertEqual(result["device_id"], "real-device-22")

	def test_assign_cubicle_moves_employee_from_old_seat(self):
		employee = make_employee("floor.move@example.com", company="_Test Company")
		floor_name = f"Floor Move {frappe.generate_hash(length=8)}"
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
				"row": "B",
				"seat_number": 2,
			}
		).insert()

		assign_cubicle(cubicle=target.name, employee=employee)
		current.reload()
		target.reload()
		self.assertFalse(current.employee)
		self.assertEqual(target.employee, employee)

		again = assign_cubicle(cubicle=target.name, employee=employee)
		self.assertEqual(again["name"], target.name)
		target.reload()
		self.assertEqual(target.employee, employee)
