#!/bin/bash
set -euo pipefail

cd /workspace/hrms

echo "Enabling yarn scripts and installing dependencies..."
yarn config set ignore-scripts false
yarn install

echo "Building PWA and Roster apps..."
yarn build

echo "Syncing built assets into bench..."
cd /home/frappe/frappe-bench
node apps/frappe/esbuild --production --apps hrms
bench --site hrms.localhost clear-cache

echo "Frontend build complete."
