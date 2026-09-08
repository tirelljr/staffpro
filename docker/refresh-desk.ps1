# Rebuild Staff Pro desk UI and clear all server caches.
$ComposeFile = Join-Path $PSScriptRoot "docker-compose.yml"
docker compose -f $ComposeFile exec staff-pro bash -lc @'
cd /home/frappe/frappe-bench
redis-cli -h redis FLUSHALL
node apps/frappe/esbuild --production --apps hrms
bench --site hrms.localhost migrate
bench --site hrms.localhost execute hrms.branding.apply_branding
bench --site hrms.localhost execute hrms.boot.prepare_staff_pro_first_login
bench --site hrms.localhost clear-cache
bench --site hrms.localhost clear-website-cache 2>/dev/null || true
grep hrms.bundle sites/assets/assets.json
'@
Write-Host ""
Write-Host "Done. Hard refresh the browser: Ctrl+Shift+R on http://localhost:8001"
Write-Host "Use an Incognito window if the UI still looks old."
