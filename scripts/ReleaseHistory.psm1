# 发布记录模块：仅保存可追溯元数据，不写入凭据或异常原文。
function Add-OpsPilotReleaseRecord {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [ValidateSet("success", "failed")]
        [string]$Status,

        [string]$Version,
        [string]$GitSha,
        [string]$Image,
        [string]$Stage,
        [string]$Readiness = "not_checked"
    )

    $parentDirectory = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($parentDirectory) -and -not (Test-Path -LiteralPath $parentDirectory)) {
        New-Item -ItemType Directory -Path $parentDirectory -Force | Out-Null
    }

    $record = [ordered]@{
        recorded_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
        action = "deploy"
        status = $Status
        version = $Version
        git_sha = $GitSha
        image = $Image
        stage = $Stage
        readiness = $Readiness
    }
    $line = $record | ConvertTo-Json -Depth 4 -Compress
    $utf8WithoutBom = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $false
    $content = $line + [Environment]::NewLine
    [System.IO.File]::AppendAllText($Path, $content, $utf8WithoutBom)

}

Export-ModuleMember -Function Add-OpsPilotReleaseRecord
