param(
    [string]$Tag
)

$ErrorActionPreference = "Stop"
$invokedPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($invokedPath)) {
    throw "Could not determine the build script location. Run this file directly from the repository."
}
$scriptPath = (Resolve-Path $invokedPath).Path
$scriptDirectory = Split-Path -Parent $scriptPath
$repoRoot = Split-Path -Parent $scriptDirectory
if ([string]::IsNullOrWhiteSpace($repoRoot)) {
    throw "Could not determine the repository root from script path: $scriptPath"
}
Set-Location $repoRoot

$versionLine = Select-String -Path "pyproject.toml" -Pattern '^version\s*=\s*"([^"]+)"'
if ($null -eq $versionLine) {
    throw "Could not read the project version from pyproject.toml."
}
$version = [regex]::Match($versionLine.Line, '"([^"]+)"').Groups[1].Value
$revision = & git rev-parse --short HEAD
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the current Git revision. Commit or repair the repository before building."
}
if ([string]::IsNullOrWhiteSpace($Tag)) {
    $Tag = "$version-$revision"
}

# Tests run in Docker, so the build machine does not need Python or pytest.
$releaseHistoryTest = Join-Path $scriptDirectory "test-release-history.ps1"
Write-Host "Validating release history behavior..." -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File $releaseHistoryTest
if ($LASTEXITCODE -ne 0) {
    throw "Release history validation failed. The application image was not built."
}

$testImage = "opspilot:test-$revision"
Write-Host "Running tests in Docker: $testImage..." -ForegroundColor Cyan
& docker build --file Dockerfile.test --tag $testImage .
if ($LASTEXITCODE -ne 0) {
    & docker image inspect $testImage *> $null
    if ($LASTEXITCODE -eq 0) {
        & docker image rm $testImage *> $null
    }
    throw "Tests failed in Docker. The application image was not built."
}
& docker image inspect $testImage *> $null
if ($LASTEXITCODE -eq 0) {
    & docker image rm $testImage *> $null
}

$image = "opspilot:$Tag"
Write-Host "Building $image from revision $revision..." -ForegroundColor Cyan
& docker build --build-arg "APP_VERSION=$version" --build-arg "VCS_REF=$revision" --tag $image .
if ($LASTEXITCODE -ne 0) {
    throw "Image build failed. Review the Docker output above."
}

& docker image inspect $image --format '{{json .Config.Labels}}'
if ($LASTEXITCODE -ne 0) {
    throw "Image was built but its metadata could not be inspected."
}
Write-Host "Build completed: $image" -ForegroundColor Green
