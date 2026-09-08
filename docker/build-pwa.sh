#!/bin/bash
set -euo pipefail
export PATH="/home/frappe/.nvm/versions/node/v24.20.0/bin:$PATH"
yarn config set ignore-scripts false
rm -rf /home/frappe/pwa-build
mkdir -p /home/frappe/pwa-build
echo COPY_FRONTEND
tar --exclude=node_modules --exclude=dist -C /workspace/hrms -cf - frontend | tar -C /home/frappe/pwa-build -xf -
cd /home/frappe/pwa-build/frontend
echo YARN_INSTALL
yarn install --ignore-engines
echo VITE_BUILD
yarn vite build --base=/assets/hrms/frontend/ --outDir=/home/frappe/pwa-build/dist
echo PUBLISH
mkdir -p /workspace/hrms/hrms/public/frontend /workspace/hrms/hrms/www /home/frappe/frappe-bench/sites/assets/hrms/frontend
rm -rf /workspace/hrms/hrms/public/frontend/* /home/frappe/frappe-bench/sites/assets/hrms/frontend/*
cp -a /home/frappe/pwa-build/dist/. /workspace/hrms/hrms/public/frontend/
cp -a /home/frappe/pwa-build/dist/. /home/frappe/frappe-bench/sites/assets/hrms/frontend/
cp /home/frappe/pwa-build/dist/index.html /workspace/hrms/hrms/www/hrms.html
echo BUILD_OK
ls /home/frappe/pwa-build/dist | head
