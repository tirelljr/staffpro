#!/bin/bash

cd /home/frappe

# Windows bind mounts can trigger Git's dubious ownership check
git config --global --add safe.directory /workspace/hrms

APP_PATH="/workspace/hrms"

finish_site_setup() {
    cd /home/frappe/frappe-bench

    # Register the host-mounted app if get-app did not finish
    if [ -L apps/hrms ] || [ -d apps/hrms ]; then
        if ! grep -qx "hrms" sites/apps.txt 2>/dev/null; then
            printf '\nhrms\n' >> sites/apps.txt
        fi
    fi

    if [ ! -f sites/hrms.localhost/site_config.json ]; then
        echo "Creating site hrms.localhost..."
        bench new-site hrms.localhost \
            --force \
            --mariadb-root-password 123 \
            --admin-password admin \
            --no-mariadb-socket

        bench --site hrms.localhost install-app hrms
        bench --site hrms.localhost set-config developer_mode 1
        bench --site hrms.localhost enable-scheduler
        bench --site hrms.localhost clear-cache
        bench use hrms.localhost
    fi
}

if [ -d "/home/frappe/frappe-bench/apps/frappe" ]; then
    echo "Bench already exists, finishing setup if needed"
    finish_site_setup
    cd /home/frappe/frappe-bench
    bench start
    exit 0
fi

echo "Creating new bench..."

export PATH="${NVM_DIR}/versions/node/v${NODE_VERSION_DEVELOP}/bin/:${PATH}"

# PWA/roster yarn postinstall is extremely slow on Windows bind mounts.
# Desk UI still works; run those installs later if you need the Vue apps.
yarn config set ignore-scripts true

cd /home/frappe
bench init --skip-redis-config-generation frappe-bench

cd frappe-bench

# Use containers instead of localhost
bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

# Redis runs in a separate container; keep `watch` so frontend edits reload
sed -i '/redis/d' ./Procfile
sed -i 's/bench serve --port 8000/bench serve --host 0.0.0.0 --port 8000/' ./Procfile

bench get-app erpnext

# Use the repo mounted from the host so Cursor edits apply live
if bench get-app --help 2>/dev/null | grep -q -- "--soft-link"; then
    bench get-app --soft-link "$APP_PATH"
else
    ln -sfn "$APP_PATH" /home/frappe/frappe-bench/apps/hrms
    bench setup requirements hrms
fi

finish_site_setup

cd /home/frappe/frappe-bench
bench start
