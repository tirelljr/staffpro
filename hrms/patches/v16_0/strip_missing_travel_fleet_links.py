"""Remove leftover links to travel and fleet doctypes deleted by remove_travel_fleet."""

from hrms.patches.v16_0.remove_travel_fleet import strip_missing_travel_fleet_links


def execute():
	strip_missing_travel_fleet_links()
