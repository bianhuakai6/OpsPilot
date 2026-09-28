param(
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

# 只处理明确的临时验证标签；带版本和 Git SHA 的正式镜像不在清理范围内。
$temporaryImages = @(& docker image ls opspilot --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -match '^opspilot:verification-' })

if ($temporaryImages.Count -eq 0) {
    Write-Host "No temporary OpsPilot images found."
    exit 0
}

Write-Host "Temporary images:" -ForegroundColor Yellow
$temporaryImages | ForEach-Object { Write-Host "  $_" }

if (-not $Apply) {
    Write-Host "Preview only. Re-run with -Apply to remove these temporary tags." -ForegroundColor Cyan
    exit 0
}

& docker image rm @temporaryImages
if ($LASTEXITCODE -ne 0) {
    throw "Image cleanup failed. No formal versioned image was selected for deletion."
}
Write-Host "Temporary image cleanup completed." -ForegroundColor Green
