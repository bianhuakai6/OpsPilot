param(
    [ValidateSet("deploy", "status", "stop")]
    [string]$Action = "deploy"
)

$ErrorActionPreference = "Stop"
$scriptPath = (Resolve-Path $MyInvocation.MyCommand.Path).Path
$scriptDirectory = Split-Path -Parent $scriptPath
$repoRoot = Split-Path -Parent $scriptDirectory
Set-Location $repoRoot
$composeArguments = @("-f", "docker-compose.yml", "-f", "docker-compose.release.yml")

# Compose requires image variables even for status and stop actions.
$env:OPSPILOT_IMAGE = "opspilot:local-placeholder"
$env:OPSPILOT_APP_VERSION = "local"

if ($Action -eq "status") {
    & docker compose @composeArguments ps
    exit $LASTEXITCODE
}

if ($Action -eq "stop") {
    # Stop only the API container and keep data services running.
    & docker stop opspilot-api 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "API container is already stopped."
    }
    exit 0
}

$portInUse = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($null -ne $portInUse) {
    throw "Port 8000 is already in use. Stop the native OpsPilot window with Ctrl+C, then run this release command again."
}

$versionLine = Select-String -Path "pyproject.toml" -Pattern '^version\s*=\s*"([^"]+)"'
if ($null -eq $versionLine) {
    throw "Could not read the project version from pyproject.toml."
}
$version = [regex]::Match($versionLine.Line, '"([^"]+)"').Groups[1].Value
$revision = & git rev-parse --short HEAD
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the current Git revision. Commit or repair the repository before deployment."
}
$image = "opspilot:$version-$revision"

# Deployment accepts only an image that was built successfully.
& docker image inspect $image *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Image $image was not found. Run scripts/build-image.ps1 first; deployment was not started."
}

$env:OPSPILOT_IMAGE = $image
$env:OPSPILOT_APP_VERSION = $version
& docker compose @composeArguments up -d --no-build
if ($LASTEXITCODE -ne 0) {
    throw "Container startup failed. Check 'release-local.ps1 -Action status' and Docker logs."
}

$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
    $services = & docker compose @composeArguments ps --format '{{.Service}}|{{.Health}}|{{.State}}'
    if ($services -contains "api|healthy|running") {
        try {
            $ready = Invoke-RestMethod -Uri "http://127.0.0.1:8000/readyz" -TimeoutSec 5
            if ($ready.status -eq "ready" -and $ready.dependencies.mysql -eq "connected" -and $ready.dependencies.redis -eq "connected") {
                Write-Host "Release succeeded: $image" -ForegroundColor Green
                exit 0
            }
        } catch {
            # Retry while the container is starting.
        }
    }
    Start-Sleep -Seconds 2
}

& docker compose @composeArguments ps
throw "Release did not become ready within 90 seconds. The API container was left running for diagnosis."
