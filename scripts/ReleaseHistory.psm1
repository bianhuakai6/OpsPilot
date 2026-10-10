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
        [string]$Readiness = "not_checked",

        [ValidateSet("deploy", "rollback")]
        [string]$Action = "deploy"
    )

    $parentDirectory = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($parentDirectory) -and -not (Test-Path -LiteralPath $parentDirectory)) {
        New-Item -ItemType Directory -Path $parentDirectory -Force | Out-Null
    }

    $record = [ordered]@{
        recorded_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
        action = $Action
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

# 回滚目标从成功部署记录中选择，不依赖本机镜像列表猜测版本关系。
function Get-OpsPilotRollbackTarget {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$CurrentImage
    )

    if ([string]::IsNullOrWhiteSpace($CurrentImage)) {
        throw "The currently running API image could not be identified."
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    $records = Get-Content -LiteralPath $Path | ForEach-Object {
        try { ConvertFrom-Json $_ } catch { $null }
    }
    return $records | Where-Object {
        $_.action -eq "deploy" -and $_.status -eq "success" -and
        -not [string]::IsNullOrWhiteSpace($_.image) -and $_.image -ne $CurrentImage
    } | Select-Object -Last 1
}

Export-ModuleMember -Function Add-OpsPilotReleaseRecord, Get-OpsPilotRollbackTarget
