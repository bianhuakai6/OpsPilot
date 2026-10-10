$ErrorActionPreference = "Stop"
$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDirectory "ReleaseHistory.psm1") -Force

# 使用唯一临时文件验证追加、JSON 格式和字段边界。
$testPath = Join-Path ([System.IO.Path]::GetTempPath()) ("opspilot-release-test-{0}.jsonl" -f [Guid]::NewGuid().ToString("N"))
try {
    $null = Add-OpsPilotReleaseRecord -Path $testPath -Action deploy -Status success -Version "0.1.0" -GitSha "abc1234" -Image "opspilot:0.1.0-abc1234" -Stage "complete" -Readiness ready
    $null = Add-OpsPilotReleaseRecord -Path $testPath -Action deploy -Status success -Version "0.1.0" -GitSha "def5678" -Image "opspilot:0.1.0-def5678" -Stage "complete" -Readiness ready
    $null = Add-OpsPilotReleaseRecord -Path $testPath -Action rollback -Status failed -Version "0.1.0" -GitSha "ghi9012" -Image "opspilot:0.1.0-ghi9012" -Stage "rollback_readiness_timeout"
    $records = @(Get-Content -LiteralPath $testPath | ForEach-Object { ConvertFrom-Json $_ })

    if ($records.Count -ne 3 -or $records[0].status -ne "success" -or $records[2].stage -ne "rollback_readiness_timeout") {
        throw "Release history append or JSON validation failed."
    }
    if ($records[0].image -ne "opspilot:0.1.0-abc1234" -or $records[0].readiness -ne "ready") {
        throw "Release history metadata validation failed."
    }
    if ($records[2].action -ne "rollback" -or $records[2].readiness -ne "not_checked" -or $records[0].PSObject.Properties.Name -contains "message") {
        throw "Release history defaults or sensitive-detail boundary validation failed."
    }

    $target = Get-OpsPilotRollbackTarget -Path $testPath -CurrentImage "opspilot:0.1.0-def5678"
    if ($target.image -ne "opspilot:0.1.0-abc1234") {
        throw "Rollback target selection did not choose the previous successful deployment."
    }
    $noTarget = Get-OpsPilotRollbackTarget -Path $testPath -CurrentImage "opspilot:0.1.0-abc1234"
    if ($noTarget.image -ne "opspilot:0.1.0-def5678") {
        throw "Rollback target selection did not select the latest successful deployment other than the current image."
    }
    try {
        $null = Get-OpsPilotRollbackTarget -Path $testPath -CurrentImage " "
        throw "Rollback target selection accepted an unknown running image."
    } catch {
        if ($_.Exception.Message -notlike "The currently running API image could not be identified.*") { throw }
    }

    Write-Host "Release history checks passed." -ForegroundColor Green
} finally {
    if (Test-Path -LiteralPath $testPath) {
        Remove-Item -LiteralPath $testPath -Force
    }
}
