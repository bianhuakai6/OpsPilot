param(
    [ValidateSet("deploy", "status", "stop", "rollback")]
    [string]$Action = "deploy"
)

$ErrorActionPreference = "Stop"
$scriptPath = (Resolve-Path $MyInvocation.MyCommand.Path).Path
$scriptDirectory = Split-Path -Parent $scriptPath
$repoRoot = Split-Path -Parent $scriptDirectory
Set-Location $repoRoot
$composeArguments = @("-f", "docker-compose.yml", "-f", "docker-compose.release.yml")
$releaseHistoryPath = Join-Path $repoRoot "data\release-history.jsonl"
Import-Module (Join-Path $scriptDirectory "ReleaseHistory.psm1") -Force

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

if ($Action -eq "rollback") {
    # 回滚只选择最近一次成功记录中的正式镜像，不重新构建，也不拉取远程镜像。
    $currentImage = (& docker inspect --format '{{.Config.Image}}' opspilot-api 2>$null | Out-String).Trim()
    $successfulRecord = $null
    $status = "failed"
    $stage = "rollback_precheck"
    $readiness = "not_checked"
    try {
        $successfulRecord = Get-OpsPilotRollbackTarget -Path $releaseHistoryPath -CurrentImage $currentImage
        if ($null -eq $successfulRecord) {
            throw "No previous successful release is available for rollback."
        }
        $stage = "rollback_image_check"
        & docker image inspect $successfulRecord.image *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "Rollback image $($successfulRecord.image) is not available locally."
        }

        $env:OPSPILOT_IMAGE = $successfulRecord.image
        $env:OPSPILOT_APP_VERSION = $successfulRecord.version
        $stage = "rollback_compose_start"
        & docker compose @composeArguments up -d --no-build
        if ($LASTEXITCODE -ne 0) { throw "Rollback container startup failed." }
        $stage = "rollback_readiness_check"
        $deadline = (Get-Date).AddSeconds(90)
        while ((Get-Date) -lt $deadline) {
            $services = & docker compose @composeArguments ps --format '{{.Service}}|{{.Health}}|{{.State}}'
            if ($services -contains "api|healthy|running") {
                try {
                    $ready = Invoke-RestMethod -Uri "http://127.0.0.1:8000/readyz" -TimeoutSec 5
                    if ($ready.status -eq "ready" -and $ready.dependencies.mysql -eq "connected" -and $ready.dependencies.redis -eq "connected") {
                        $readiness = "ready"
                        $status = "success"
                        $stage = "rollback_complete"
                        break
                    }
                } catch { }
            }
            Start-Sleep -Seconds 2
        }
        if ($status -ne "success") {
            $stage = "rollback_readiness_timeout"
            throw "Rollback did not become ready within 90 seconds."
        }
    } catch {
        $failureMessage = $_.Exception.Message
    } finally {
        try {
            $null = Add-OpsPilotReleaseRecord -Path $releaseHistoryPath -Action rollback -Status $status -Version $successfulRecord.version -GitSha $successfulRecord.git_sha -Image $successfulRecord.image -Stage $stage -Readiness $readiness
        } catch { Write-Warning "Could not append the rollback history record." }
    }
    if ($status -eq "success") {
        Write-Host "Rollback succeeded: $($successfulRecord.image)" -ForegroundColor Green
        exit 0
    }
    throw $failureMessage
}

# 发布流程统一收口，确保成功和失败尝试都能留下记录。
$version = $null
$revision = $null
$image = $null
$stage = "metadata"
$readiness = "not_checked"
$status = "failed"
$failureMessage = $null

try {
    $versionLine = Select-String -Path "pyproject.toml" -Pattern '^version\s*=\s*"([^"]+)"'
    if ($null -eq $versionLine) {
        throw "Could not read the project version from pyproject.toml."
    }
    $version = [regex]::Match($versionLine.Line, '"([^"]+)"').Groups[1].Value
    $revisionOutput = & git rev-parse --short HEAD
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read the current Git revision. Commit or repair the repository before building."
    }
    $revision = ($revisionOutput | Out-String).Trim()
    $image = "opspilot:$version-$revision"

    $stage = "port_check"
    $portInUse = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($null -ne $portInUse) {
        throw "Port 8000 is already in use. Stop the native OpsPilot window with Ctrl+C, then run this release command again."
    }

    # 只接受已经构建好的版本镜像，避免发布阶段隐式构建或拉取。
    $stage = "image_check"
    & docker image inspect $image *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Image $image was not found. Run scripts/build-image.ps1 first; deployment was not started."
    }

    $env:OPSPILOT_IMAGE = $image
    $env:OPSPILOT_APP_VERSION = $version
    $stage = "compose_start"
    & docker compose @composeArguments up -d --no-build
    if ($LASTEXITCODE -ne 0) {
        throw "Container startup failed. Check 'release-local.ps1 -Action status' and Docker logs."
    }

    $stage = "readiness_check"
    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $deadline) {
        $services = & docker compose @composeArguments ps --format '{{.Service}}|{{.Health}}|{{.State}}'
        if ($services -contains "api|healthy|running") {
            try {
                $ready = Invoke-RestMethod -Uri "http://127.0.0.1:8000/readyz" -TimeoutSec 5
                if ($ready.status -eq "ready" -and $ready.dependencies.mysql -eq "connected" -and $ready.dependencies.redis -eq "connected") {
                    $readiness = "ready"
                    $status = "success"
                    $stage = "complete"
                    break
                }
            } catch {
                # 服务启动期间暂时不可达时继续轮询，不记录异常原文。
            }
        }
        Start-Sleep -Seconds 2
    }

    if ($status -ne "success") {
        $stage = "readiness_timeout"
        throw "Release did not become ready within 90 seconds. The API container was left running for diagnosis."
    }
} catch {
    $failureMessage = $_.Exception.Message
} finally {
    try {
        $null = Add-OpsPilotReleaseRecord -Path $releaseHistoryPath -Action deploy -Status $status -Version $version -GitSha $revision -Image $image -Stage $stage -Readiness $readiness
        Write-Host "Release record: $releaseHistoryPath" -ForegroundColor DarkGray
    } catch {
        Write-Warning "Could not append the release history record. Check local data directory permissions."
    }
}

if ($status -eq "success") {
    Write-Host "Release succeeded: $image" -ForegroundColor Green
    exit 0
}

& docker compose @composeArguments ps
throw $failureMessage
