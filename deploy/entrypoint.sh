#!/bin/bash
set -euo pipefail

export PYTHONUNBUFFERED=1

BENCH=/home/frappe/frappe-bench
cd "$BENCH"

PORT="${PORT:-10000}"
DB_HOST="${DB_HOST:?DB_HOST is required}"
DB_PORT="${DB_PORT:-3306}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:?DB_ROOT_PASSWORD is required}"
REDIS_URL="${REDIS_URL:?REDIS_URL is required}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:?ADMIN_PASSWORD is required}"
SITE_NAME="${SITE_NAME:-${RENDER_EXTERNAL_HOSTNAME:-staffpro.localhost}}"
export FRAPPE_SITE_NAME_HEADER="${FRAPPE_SITE_NAME_HEADER:-$SITE_NAME}"
export PORT

wait_for_tcp() {
	local host="$1"
	local port="$2"
	local label="$3"
	python3 - "$host" "$port" "$label" <<'PY'
import socket, sys, time
host, port, label = sys.argv[1], int(sys.argv[2]), sys.argv[3]
deadline = time.time() + 180
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"{label} is reachable at {host}:{port}", flush=True)
            raise SystemExit(0)
    except OSError:
        time.sleep(3)
print(f"Timed out waiting for {label} at {host}:{port}", file=sys.stderr)
raise SystemExit(1)
PY
}

redis_hostport() {
	python3 - "$REDIS_URL" <<'PY'
from urllib.parse import urlparse
import sys
parsed = urlparse(sys.argv[1])
host = parsed.hostname or "127.0.0.1"
port = parsed.port or 6379
print(f"{host} {port}")
PY
}

mkdir -p sites/assets logs
# Persistent sites disk keeps old files. Never use cp -n here or hrms JS stays stale.
if [ -d "$BENCH/assets" ]; then
	cp -a "$BENCH/assets/." sites/assets/ || true
fi
ls -1 apps > sites/apps.txt

echo "{}" > sites/common_site_config.json
bench set-config -g db_host "$DB_HOST"
bench set-config -gp db_port "$DB_PORT"
bench set-config -g redis_cache "$REDIS_URL"
bench set-config -g redis_queue "$REDIS_URL"
bench set-config -g redis_socketio "$REDIS_URL"
bench set-config -gp socketio_port 9000
bench set-config -g default_site "$SITE_NAME"

wait_for_tcp "$DB_HOST" "$DB_PORT" "MariaDB"
read -r REDIS_HOST REDIS_PORT < <(redis_hostport)
wait_for_tcp "$REDIS_HOST" "$REDIS_PORT" "Redis"

render_nginx_conf() {
	sed \
		-e "s/\${PORT}/${PORT}/g" \
		-e "s/\${FRAPPE_SITE_NAME_HEADER}/${FRAPPE_SITE_NAME_HEADER}/g" \
		/opt/staffpro/nginx.conf.template > /tmp/nginx.conf
}

start_nginx() {
	if command -v nginx >/dev/null 2>&1; then
		render_nginx_conf
		nginx -c /tmp/nginx.conf &
		echo "nginx listening on 0.0.0.0:${PORT}"
	else
		echo "nginx not found; gunicorn will bind to PORT" >&2
	fi
}

start_realtime_service() {
	local socketio="$BENCH/apps/frappe/socketio.js"
	if [ ! -f "$socketio" ]; then
		echo "Frappe socketio.js not found; desk realtime disabled" >&2
		return 0
	fi
	(
		while true; do
			echo "Starting Frappe realtime on port 9000..." >&2
			node "$socketio" || echo "Frappe realtime exited; restarting in 3s..." >&2
			sleep 3
		done
	) &
}

create_or_migrate_site() {
	if [ ! -f "sites/${SITE_NAME}/site_config.json" ]; then
		echo "Creating site ${SITE_NAME}..."
		bench new-site "$SITE_NAME" \
			--db-root-username root \
			--db-root-password "$DB_ROOT_PASSWORD" \
			--admin-password "$ADMIN_PASSWORD" \
			--mariadb-user-host-login-scope '%' \
			--no-mariadb-socket \
			--install-app erpnext \
			--install-app hrms
		bench use "$SITE_NAME"
		if [ -n "${RENDER_EXTERNAL_HOSTNAME:-}" ]; then
			bench --site "$SITE_NAME" set-config host_name "https://${RENDER_EXTERNAL_HOSTNAME}"
		fi
		bench --site "$SITE_NAME" enable-scheduler
		bench --site "$SITE_NAME" execute "frappe.get_attr('hrms.branding.apply_branding')()" || true
		bench --site "$SITE_NAME" execute "frappe.get_attr('hrms.boot.prepare_staff_pro_first_login')()" || true
		bench --site "$SITE_NAME" clear-cache || true
		echo "Site ${SITE_NAME} is ready. Sign in as Matt Chavez, Micheal Graylord, or Myra Chavez (password: admin)."
	else
		echo "Migrating site ${SITE_NAME}..."
		if [ -n "${RENDER_EXTERNAL_HOSTNAME:-}" ]; then
			bench --site "$SITE_NAME" set-config host_name "https://${RENDER_EXTERNAL_HOSTNAME}" || true
		fi
		# Drop leftover DDL outside Frappe first. Sync dies with ImplicitCommitError
		# if Expense Claim.vehicle_log is still present (progress bar freezes ~60%).
		"$BENCH/env/bin/python" "$BENCH/apps/hrms/deploy/drop_blocked_columns.py" "$SITE_NAME" || true
		bench --site "$SITE_NAME" migrate
		bench --site "$SITE_NAME" clear-cache || true
	fi
}

refresh_desk_assets() {
	# Assets are built in the image. A second yarn/bench build here OOMs the
	# 2 GB Render instance once gunicorn is already running.
	echo "Refreshing desk cache..."
	bench --site "$SITE_NAME" execute "frappe.get_attr('hrms.branding.repair_desk_ltr_bundles')()" || true
	bench --site "$SITE_NAME" execute "frappe.get_attr('hrms.branding.apply_branding')()" || true
	bench --site "$SITE_NAME" clear-cache || true
}

trap 'kill $(jobs -p) 2>/dev/null; wait' SIGTERM SIGINT

start_nginx
create_or_migrate_site

GUNICORN_BIND="127.0.0.1:8000"
if ! command -v nginx >/dev/null 2>&1; then
	GUNICORN_BIND="0.0.0.0:${PORT}"
fi

"$BENCH/env/bin/gunicorn" \
	--chdir="$BENCH/sites" \
	--bind="$GUNICORN_BIND" \
	--threads="${GUNICORN_THREADS:-4}" \
	--workers="${GUNICORN_WORKERS:-2}" \
	--worker-class=gthread \
	--worker-tmp-dir=/dev/shm \
	--timeout="${GUNICORN_TIMEOUT:-120}" \
	--preload \
	frappe.app:application &

start_realtime_service

bench worker --queue short,default,long &
bench schedule &

echo "Staff Pro is running on port ${PORT}"
refresh_desk_assets || true
# Gunicorn --preload can take a while; do not treat "not in ps yet" as a crash.
set +e
for _ in $(seq 1 90); do
	if pgrep -f "frappe.app:application" >/dev/null 2>&1; then
		break
	fi
	sleep 2
done
if ! pgrep -f "frappe.app:application" >/dev/null 2>&1; then
	echo "Gunicorn failed to start within 3 minutes" >&2
	exit 1
fi
while true; do
	sleep 30
	if ! pgrep -f "frappe.app:application" >/dev/null 2>&1; then
		echo "Gunicorn stopped; exiting container" >&2
		exit 1
	fi
done
