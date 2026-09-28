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

# 构建前先运行默认测试，避免为已知失败的代码创建镜像。
$ErrorActionPreference = "Continue"
& "C:\Windows\py.exe" -3.13 -m pytest -q
$testExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($testExitCode -ne 0) {
    throw "Tests failed. The image was not built."
}

$version = & "C:\Windows\py.exe" -3.13 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the project version from pyproject.toml."
}
$revision = & git rev-parse --short HEAD
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the current Git revision. Commit or repair the repository before building."
}
if ([string]::IsNullOrWhiteSpace($Tag)) {
    $Tag = "$version-$revision"
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
