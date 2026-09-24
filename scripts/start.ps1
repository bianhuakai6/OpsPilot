param(
    [int]$Port = 8000
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
        Write-Host "OpsPilot is already running on port $effectivePort." -ForegroundColor Yellow
        Write-Host "API docs: http://${effectiveHost}:$effectivePort/docs"
        Write-Host "Health: http://${effectiveHost}:$effectivePort/healthz"
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
& $python -m uvicorn app.main:app --host $effectiveHost --port $effectivePort
