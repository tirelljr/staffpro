"""Drop leftover columns outside Frappe so migrate can finish on Render.

DocType sync runs ALTER TABLE inside a transaction. Frappe then raises
ImplicitCommitError and the container never reaches gunicorn.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _connect(cfg: dict):
	try:
		import pymysql
	except ImportError:  # pragma: no cover
		import MySQLdb as pymysql

	return pymysql.connect(
		host=os.environ.get("DB_HOST") or cfg.get("db_host") or "127.0.0.1",
		port=int(os.environ.get("DB_PORT") or cfg.get("db_port") or 3306),
		user=cfg.get("db_user") or cfg.get("db_name"),
		password=cfg["db_password"],
		database=cfg["db_name"],
		autocommit=True,
	)


def drop_vehicle_log(site: str) -> int:
	cfg_path = Path("sites") / site / "site_config.json"
	if not cfg_path.exists():
		print(f"No site config at {cfg_path}; skip column drop", flush=True)
		return 0

	cfg = json.loads(cfg_path.read_text())
	conn = _connect(cfg)
	try:
		with conn.cursor() as cur:
			cur.execute("SHOW COLUMNS FROM `tabExpense Claim` LIKE 'vehicle_log'")
			if not cur.fetchone():
				print("Expense Claim.vehicle_log already gone", flush=True)
				return 0
			cur.execute("ALTER TABLE `tabExpense Claim` DROP COLUMN `vehicle_log`")
		print("Dropped leftover Expense Claim.vehicle_log", flush=True)
	finally:
		conn.close()
	return 0


if __name__ == "__main__":
	site = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SITE_NAME")
	if not site:
		print("SITE_NAME is required", file=sys.stderr, flush=True)
		raise SystemExit(1)
	raise SystemExit(drop_vehicle_log(site))
