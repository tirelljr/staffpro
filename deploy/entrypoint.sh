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

GUNICORN_HOST="127.0.0.1"
GUNICORN_PORT="8000"
if ! command -v nginx >/dev/null 2>&1; then
	GUNICORN_HOST="0.0.0.0"
	GUNICORN_PORT="$PORT"
fi

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

port_open() {
	python3 - "$1" "$2" <<'PY'
import socket, sys
host, port = sys.argv[1], int(sys.argv[2])
try:
    with socket.create_connection((host, port), timeout=1):
        raise SystemExit(0)
except OSError:
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
		echo "${RENDER_GIT_COMMIT:-unknown}" > "sites/${SITE_NAME}/.staffpro_migrated_commit"
		echo "Site ${SITE_NAME} is ready. Sign in as Matt Chavez, Micheal Graylord, or Myra Chavez (password: admin)."
		return
	fi

	if [ -n "${RENDER_EXTERNAL_HOSTNAME:-}" ]; then
		bench --site "$SITE_NAME" set-config host_name "https://${RENDER_EXTERNAL_HOSTNAME}" || true
	fi

	local build_id="${RENDER_GIT_COMMIT:-unknown}"
	local stamp="sites/${SITE_NAME}/.staffpro_migrated_commit"
	if [ "${STAFFPRO_FORCE_MIGRATE:-}" != "1" ] && [ -f "$stamp" ] && [ "$(cat "$stamp")" = "$build_id" ]; then
		echo "Skipping migrate; site already on ${build_id}"
		return
	fi

	echo "Migrating site ${SITE_NAME}..."
	# Drop leftover DDL outside Frappe first. Sync dies with ImplicitCommitError
	# if Expense Claim.vehicle_log is still present (progress bar freezes ~60%).
	"$BENCH/env/bin/python" "$BENCH/apps/hrms/deploy/drop_blocked_columns.py" "$SITE_NAME" || true
	bench --site "$SITE_NAME" migrate
	bench --site "$SITE_NAME" clear-cache || true
	echo "$build_id" > "$stamp"
}

start_gunicorn() {
	echo "Starting gunicorn on ${GUNICORN_HOST}:${GUNICORN_PORT}..."
	"$BENCH/env/bin/gunicorn" \
		--chdir="$BENCH/sites" \
		--bind="${GUNICORN_HOST}:${GUNICORN_PORT}" \
		--threads="${GUNICORN_THREADS:-4}" \
		--workers="${GUNICORN_WORKERS:-1}" \
		--worker-class=gthread \
		--worker-tmp-dir=/dev/shm \
		--timeout="${GUNICORN_TIMEOUT:-120}" \
		frappe.app:application &
}

gunicorn_ready() {
	port_open "$GUNICORN_HOST" "$GUNICORN_PORT"
}

wait_for_gunicorn() {
	local seconds="${1:-180}"
	local elapsed=0
	while [ "$elapsed" -lt "$seconds" ]; do
		if gunicorn_ready; then
			echo "Gunicorn is accepting connections"
			return 0
		fi
		sleep 2
		elapsed=$((elapsed + 2))
	done
	return 1
}

trap 'kill $(jobs -p) 2>/dev/null; wait' SIGTERM SIGINT

start_nginx
create_or_migrate_site
start_gunicorn
start_realtime_service

if ! wait_for_gunicorn 180; then
	echo "Gunicorn did not accept connections; retrying once..." >&2
	pkill -f '[g]unicorn' || true
	sleep 2
	start_gunicorn
	wait_for_gunicorn 180 || echo "Gunicorn still starting; keeping the container up" >&2
fi

bench worker --queue short,default,long &
bench schedule &

echo "Staff Pro is running on port ${PORT}"

set +e
while true; do
	sleep 15
	if gunicorn_ready; then
		continue
	fi
	echo "Gunicorn is not accepting connections; restarting it" >&2
	pkill -f '[g]unicorn' || true
	sleep 2
	start_gunicorn
	wait_for_gunicorn 120 || true
done
