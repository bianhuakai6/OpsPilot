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
    throw "Port $effectivePort is already in use. Close the process or choose another port with -Port."
}

Write-Host "OpsPilot is starting..." -ForegroundColor Cyan
Write-Host "Project: $repoRoot"
Write-Host "API docs: http://${effectiveHost}:$effectivePort/docs"
Write-Host "Health: http://${effectiveHost}:$effectivePort/healthz"
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow

$env:OPSPILOT_HOST = $effectiveHost
$env:OPSPILOT_PORT = [string]$effectivePort
& $python -m uvicorn app.main:app --host $effectiveHost --port $effectivePort
