#!/usr/bin/env python3
"""Ensure sites/apps.txt lists hrms on its own line (avoid paymentshrms glue)."""

from __future__ import annotations

from pathlib import Path

APPS_TXT = Path("sites/apps.txt")
HRMS = "hrms"


def normalize_apps(raw: str) -> list[str]:
	apps: list[str] = []
	for line in raw.splitlines():
		token = line.strip()
		if not token:
			continue
		if token == "paymentshrms":
			for part in ("payments", HRMS):
				if part not in apps:
					apps.append(part)
			continue
		if token not in apps:
			apps.append(token)
	if HRMS not in apps:
		apps.append(HRMS)
	return apps


def main() -> None:
	if not APPS_TXT.exists():
		APPS_TXT.parent.mkdir(parents=True, exist_ok=True)
		APPS_TXT.write_text(f"{HRMS}\n", encoding="utf-8")
		return
	apps = normalize_apps(APPS_TXT.read_text(encoding="utf-8"))
	APPS_TXT.write_text("\n".join(apps) + "\n", encoding="utf-8")


if __name__ == "__main__":
	main()
