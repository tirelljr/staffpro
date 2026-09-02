# Build Staff Pro PWA + Roster inside the Docker container.
# Usage:
#   .\docker\build-frontend.ps1
#   .\docker\build-frontend.ps1 -Interactive

param(
    [switch]$Interactive
)

$ErrorActionPreference = "Stop"
$ComposeFile = Join-Path $PSScriptRoot "docker-compose.yml"
$Container = "staff-pro-frappe-1"

$running = docker ps --filter "name=$Container" --filter "status=running" -q
if (-not $running) {
    Write-Host "Starting Docker containers..."
    docker compose -f $ComposeFile up -d
}

$execArgs = @("exec")
if ($Interactive) {
    $execArgs += "-it"
}
$execArgs += $Container, "bash", "/workspace/build-frontend.sh"

Write-Host "Running frontend build in $Container..."
& docker @execArgs
