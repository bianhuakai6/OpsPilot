$ErrorActionPreference = "Stop"
$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDirectory
Set-Location $repoRoot

& docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Engine is unavailable. Start Docker Desktop and retry."
}

Write-Host "Building and testing the OpsPilot image in Docker..." -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scriptDirectory "build-image.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "Container build failed. The application was not started."
}

Write-Host "Starting the complete local delivery stack..." -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scriptDirectory "release-local.ps1") -Action deploy
if ($LASTEXITCODE -ne 0) {
    throw "Container deployment failed. Check Docker status and logs."
}

Write-Host "OpsPilot is ready: http://127.0.0.1:8000/dashboard" -ForegroundColor Green
