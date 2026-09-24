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

$portInUse = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($null -ne $portInUse) {
    throw "Port $Port is already in use. Close the process or choose another port with -Port."
}

Write-Host "OpsPilot is starting..." -ForegroundColor Cyan
Write-Host "Project: $repoRoot"
Write-Host "API docs: http://127.0.0.1:$Port/docs"
Write-Host "Health: http://127.0.0.1:$Port/healthz"
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow

& $python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
