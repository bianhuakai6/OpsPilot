param(
    [int]$Port = 8000,
    [ValidateSet("full", "memory")]
    [string]$Mode = "full"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# Prefer the project virtual environment when it exists.
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCommand) {
        throw "Python was not found. Install Python 3.13 or create .venv."
    }
    $python = $pythonCommand.Source
}

# Fail early when required runtime packages are missing.
& $python -c 'import fastapi, uvicorn' 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "FastAPI or Uvicorn is missing. Install the project dependencies first."
}

# Full mode starts local MySQL and Redis; memory mode is for lightweight development.
if ($Mode -eq "full") {
    $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
    if ($null -eq $dockerCommand) {
        throw "Docker CLI was not found. Install/start Docker Desktop, or explicitly use -Mode memory."
    }
    & docker info --format '{{.ServerVersion}}' *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Engine is unavailable. Start Docker Desktop, wait until Engine is ready, then run start-project.bat again."
    }
    & docker compose up -d
    if ($LASTEXITCODE -ne 0) {
        throw "Could not start MySQL and Redis with Docker Compose. Check 'docker compose ps' and container logs."
    }

    $composeDeadline = (Get-Date).AddSeconds(90)
    while ($true) {
        # Compose JSON is newline-delimited; use compact text for reliable parsing in Windows PowerShell.
        $serviceStatuses = & docker compose ps --format '{{.Service}}|{{.Health}}'
        if ($LASTEXITCODE -ne 0) {
            throw "Could not read Docker Compose service health. Check 'docker compose ps' and retry."
        }
        $mysqlHealthy = $serviceStatuses -contains "mysql|healthy"
        $redisHealthy = $serviceStatuses -contains "redis|healthy"
        if ($mysqlHealthy -and $redisHealthy) { break }
        if ((Get-Date) -ge $composeDeadline) {
            & docker compose ps
            throw "MySQL and Redis did not both become healthy within 90 seconds. Review the status above and retry."
        }
        Start-Sleep -Seconds 2
    }
}

# Explicit arguments take precedence over environment variables.
$effectivePort = $Port
$envPort = [Environment]::GetEnvironmentVariable("OPSPILOT_PORT")
if ($Port -eq 8000 -and -not [string]::IsNullOrWhiteSpace($envPort)) {
    try {
        $effectivePort = [int]$envPort
    } catch {
        throw "OPSPILOT_PORT must be an integer."
    }
}
if ($effectivePort -lt 1 -or $effectivePort -gt 65535) {
    throw "Port must be between 1 and 65535."
}

$effectiveHost = [Environment]::GetEnvironmentVariable("OPSPILOT_HOST")
if ([string]::IsNullOrWhiteSpace($effectiveHost)) {
    $effectiveHost = "127.0.0.1"
}

$portInUse = Get-NetTCPConnection -LocalPort $effectivePort -State Listen -ErrorAction SilentlyContinue
if ($null -ne $portInUse) {
    # Reuse an existing OpsPilot instance instead of treating it as a foreign conflict.
    $expectedTitle = [Environment]::GetEnvironmentVariable("OPSPILOT_APP_NAME")
    if ([string]::IsNullOrWhiteSpace($expectedTitle)) {
        $expectedTitle = "OpsPilot"
    }
    $openApiUrl = "http://127.0.0.1:$effectivePort/openapi.json"
    $runningTitle = & $python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('$openApiUrl', timeout=2)).get('info', {}).get('title', ''))" 2>$null
    if ($LASTEXITCODE -eq 0 -and $runningTitle -eq $expectedTitle) {
        try {
            $readiness = Invoke-RestMethod -Uri "http://127.0.0.1:$effectivePort/readyz" -TimeoutSec 3
        } catch {
            throw "OpsPilot is listening on port $effectivePort but is not ready. Stop that instance and restart it with this script."
        }
        if ($Mode -eq "full" -and ($readiness.dependencies.mysql -ne "connected" -or $readiness.dependencies.redis -ne "connected")) {
            throw "OpsPilot on port $effectivePort is using a different dependency mode. Stop that instance with Ctrl+C, then run start-project.bat again."
        }
        Write-Host "OpsPilot is already running on port $effectivePort ($Mode mode)." -ForegroundColor Yellow
        Write-Host "API docs: http://${effectiveHost}:$effectivePort/docs"
        Write-Host "Health: http://${effectiveHost}:$effectivePort/healthz"
        Write-Host "Readiness: http://${effectiveHost}:$effectivePort/readyz"
        exit 0
    }

    $ownerPid = $portInUse[0].OwningProcess
    $owner = Get-CimInstance Win32_Process -Filter "ProcessId=$ownerPid" -ErrorAction SilentlyContinue
    $ownerName = if ($null -ne $owner) { $owner.Name } else { "unknown process" }
    throw "Port $effectivePort is used by PID $ownerPid ($ownerName), and is not the expected OpsPilot service. Choose another port with -Port."
}

Write-Host "OpsPilot is starting..." -ForegroundColor Cyan
Write-Host "Project: $repoRoot"
Write-Host "API docs: http://${effectiveHost}:$effectivePort/docs"
Write-Host "Health: http://${effectiveHost}:$effectivePort/healthz"
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow

$env:OPSPILOT_HOST = $effectiveHost
$env:OPSPILOT_PORT = [string]$effectivePort
$env:OPSPILOT_STORAGE = if ($Mode -eq "full") { "mysql" } else { "memory" }
$env:OPSPILOT_REDIS_ENABLED = if ($Mode -eq "full") { "true" } else { "false" }
& $python -m uvicorn app.main:app --host $effectiveHost --port $effectivePort
