$ErrorActionPreference = "Stop"
$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDirectory "ReleaseHistory.psm1") -Force

# 使用唯一临时文件验证追加、JSON 格式和字段边界。
$testPath = Join-Path ([System.IO.Path]::GetTempPath()) ("opspilot-release-test-{0}.jsonl" -f [Guid]::NewGuid().ToString("N"))
try {
    $null = Add-OpsPilotReleaseRecord -Path $testPath -Status success -Version "0.1.0" -GitSha "abc1234" -Image "opspilot:0.1.0-abc1234" -Stage "complete" -Readiness ready
    $null = Add-OpsPilotReleaseRecord -Path $testPath -Status failed -Version "0.1.0" -GitSha "def5678" -Image "opspilot:0.1.0-def5678" -Stage "readiness_timeout"
    $records = @(Get-Content -LiteralPath $testPath | ForEach-Object { ConvertFrom-Json $_ })

    if ($records.Count -ne 2 -or $records[0].status -ne "success" -or $records[1].stage -ne "readiness_timeout") {
        throw "Release history append or JSON validation failed."
    }
    if ($records[0].image -ne "opspilot:0.1.0-abc1234" -or $records[0].readiness -ne "ready") {
        throw "Release history metadata validation failed."
    }
    if ($records[1].readiness -ne "not_checked" -or $records[0].PSObject.Properties.Name -contains "message") {
        throw "Release history defaults or sensitive-detail boundary validation failed."
    }

    Write-Host "Release history checks passed." -ForegroundColor Green
} finally {
    if (Test-Path -LiteralPath $testPath) {
        Remove-Item -LiteralPath $testPath -Force
    }
}
