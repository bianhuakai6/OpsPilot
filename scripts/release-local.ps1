param(
    [ValidateSet("deploy", "status", "stop")]
    [string]$Action = "deploy"
)

$ErrorActionPreference = "Stop"
$scriptPath = (Resolve-Path $MyInvocation.MyCommand.Path).Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)
Set-Location $repoRoot
$composeArguments = @("-f", "docker-compose.yml", "-f", "docker-compose.release.yml")

if ($Action -eq "status") {
    & docker compose @composeArguments ps
    exit $LASTEXITCODE
}

if ($Action -eq "stop") {
    # 只停止 API 容器，保留 MySQL/Redis 和数据卷供下一次发布复用。
    & docker compose @composeArguments stop api
    exit $LASTEXITCODE
}

$portInUse = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($null -ne $portInUse) {
    throw "Port 8000 is already in use. Stop the native OpsPilot window with Ctrl+C, then run this release command again."
}

$version = & "C:\Windows\py.exe" -3.13 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"
$revision = & git rev-parse --short HEAD
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the current Git revision. Commit or repair the repository before deployment."
}
$image = "opspilot:$version-$revision"

# 先构建当前提交对应的镜像，构建脚本内含默认测试门禁。
& powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\build-image.ps1" -Tag "$version-$revision"
if ($LASTEXITCODE -ne 0) {
    throw "Image build failed. Deployment was not started."
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
            # Container health remains the primary wait condition; retry until timeout.
        }
    }
    Start-Sleep -Seconds 2
}

& docker compose @composeArguments ps
throw "Release did not become ready within 90 seconds. The API container was left running for diagnosis."
