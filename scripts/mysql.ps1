param(
    [ValidateSet("up", "down", "status", "logs")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

switch ($Action) {
    "up" { docker compose up -d mysql }
    "down" { docker compose down }
    "status" { docker compose ps }
    "logs" { docker compose logs --tail=100 mysql }
}
