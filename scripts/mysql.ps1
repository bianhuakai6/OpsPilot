param(
    [ValidateSet("up", "down", "status", "logs")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

switch ($Action) {
    "up" {
        docker compose up -d mysql
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        docker compose exec -T mysql mysqladmin ping -h localhost -u root -proot_local_password --silent
    }
    "down" { docker compose down }
    "status" { docker compose ps }
    "logs" { docker compose logs --tail=100 mysql }
}
