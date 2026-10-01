[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,

    [Parameter(Mandatory = $true, Position = 1)]
    [ValidateNotNullOrEmpty()]
    [string]$Changelog
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-RequiredCommand {
    param([Parameter(Mandatory = $true)][string]$Name)

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        throw "Không tìm thấy lệnh '$Name' trong PATH."
    }
    return $command.Source
}

function Invoke-NativeCapture {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList
    )

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        # Windows PowerShell 5.1 wraps native stderr as ErrorRecord objects.
        # Keep collecting that output and decide success only from the exit code.
        $ErrorActionPreference = 'Continue'
        $output = @(& $FilePath @ArgumentList 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = $output
    }
}

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$Label
    )

    Write-Host "`n==> $Label" -ForegroundColor Cyan
    $result = Invoke-NativeCapture $FilePath $ArgumentList
    foreach ($line in $result.Output) {
        Write-Host $line
    }
    if ($result.ExitCode -ne 0) {
        throw "$Label thất bại (exit code $($result.ExitCode))."
    }
    return @($result.Output | ForEach-Object { "$_" })
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $encoding = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Set-JsonProperty {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)]$Value
    )

    if ($null -eq $Object.PSObject.Properties[$Name]) {
        $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
    }
    else {
        $Object.$Name = $Value
    }
}

$projectRoot = $PSScriptRoot
$clientPath = Join-Path $projectRoot 'client_app.py'
$versionJsonPath = Join-Path $projectRoot 'version.json'
$specPath = Join-Path $projectRoot 'client_app.spec'
$exePath = Join-Path $projectRoot 'dist\client_app.exe'
$tagName = "v$Version"
$originalClientContent = $null
$sourceCommitted = $false
$downloadDirectory = $null
$failure = $null

Push-Location $projectRoot
try {
    $git = Get-RequiredCommand 'git'
    $gh = Get-RequiredCommand 'gh'
    $python = Get-RequiredCommand 'python'

    foreach ($requiredFile in @($clientPath, $versionJsonPath, $specPath)) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            throw "Thiếu file bắt buộc: $requiredFile"
        }
    }

    Invoke-NativeChecked $gh @('auth', 'status') 'Kiểm tra đăng nhập GitHub CLI' | Out-Null

    $branchResult = Invoke-NativeCapture $git @('branch', '--show-current')
    $branch = ($branchResult.Output -join [Environment]::NewLine).Trim()
    if ($branchResult.ExitCode -ne 0 -or $branch -ne 'main') {
        throw "Release chỉ được chạy trên nhánh main. Nhánh hiện tại: '$branch'."
    }

    Invoke-NativeChecked $git @('fetch', 'origin', 'main', '--tags') 'Đồng bộ thông tin origin/main và tag' | Out-Null

    $aheadBehindResult = Invoke-NativeCapture $git @('rev-list', '--left-right', '--count', 'origin/main...HEAD')
    $aheadBehind = (($aheadBehindResult.Output -join [Environment]::NewLine).Trim()) -split '\s+'
    if ($aheadBehindResult.ExitCode -ne 0 -or $aheadBehind.Count -lt 2) {
        throw 'Không thể so sánh nhánh main với origin/main.'
    }
    if ([int]$aheadBehind[0] -gt 0) {
        throw 'Nhánh main trên máy đang chậm hơn origin/main. Hãy pull/rebase trước khi release.'
    }

    $localTagResult = Invoke-NativeCapture $git @('show-ref', '--verify', '--quiet', "refs/tags/$tagName")
    $localTagExit = $localTagResult.ExitCode
    if ($localTagExit -eq 0) {
        throw "Tag $tagName đã tồn tại trên máy."
    }
    if ($localTagExit -ne 1) {
        throw "Không thể kiểm tra tag $tagName trên máy."
    }

    $remoteTagResult = Invoke-NativeCapture $git @('ls-remote', '--tags', 'origin', "refs/tags/$tagName")
    $remoteTag = ($remoteTagResult.Output -join [Environment]::NewLine).Trim()
    if ($remoteTagResult.ExitCode -ne 0) {
        throw "Không thể kiểm tra tag $tagName trên origin."
    }
    if ($remoteTag) {
        throw "Tag $tagName đã tồn tại trên origin."
    }

    $repositoryResult = Invoke-NativeCapture $gh @('repo', 'view', '--json', 'nameWithOwner', '--jq', '.nameWithOwner')
    $repository = ($repositoryResult.Output -join [Environment]::NewLine).Trim()
    if ($repositoryResult.ExitCode -ne 0 -or -not $repository) {
        throw 'Không xác định được GitHub repository hiện tại.'
    }

    $releaseTags = Invoke-NativeChecked $gh @(
        'api', '--paginate', "repos/$repository/releases?per_page=100", '--jq', '.[].tag_name'
    ) 'Kiểm tra Release đã tồn tại' 
    if ($releaseTags -contains $tagName) {
        throw "GitHub Release $tagName đã tồn tại. Script sẽ không ghi đè."
    }

    $originalClientContent = [System.IO.File]::ReadAllText($clientPath)
    $versionPattern = [regex]'(?m)^CURRENT_VERSION\s*=\s*"[^"]+"\s*$'
    if ($versionPattern.Matches($originalClientContent).Count -ne 1) {
        throw 'Không tìm thấy duy nhất một dòng CURRENT_VERSION trong client_app.py.'
    }
    $updatedClientContent = $versionPattern.Replace(
        $originalClientContent,
        "CURRENT_VERSION = `"$Version`"",
        1
    )
    Write-Utf8NoBom $clientPath $updatedClientContent
    Write-Host "Đã cập nhật CURRENT_VERSION thành $Version." -ForegroundColor Green

    $testOutput = Invoke-NativeChecked $python @('-m', 'pytest', '-v', '--color=no') 'Chạy unit test'
    $testText = $testOutput -join "`n"
    # Invoke-NativeChecked validates the process exit code; counts are display-only.
    $testSummary = [regex]::Matches($testText, '\b(\d+)\s+passed\b')
    if ($testSummary.Count -gt 0) {
        $testsPassed = $testSummary[$testSummary.Count - 1].Groups[1].Value
        Write-Host "Tests passed: $testsPassed"
    }
    else {
        Write-Host 'Tests passed: N/A (pytest không báo số passed).'
    }
    Write-Host 'Result: PASS' -ForegroundColor Green

    if (Test-Path -LiteralPath $exePath) {
        Remove-Item -LiteralPath $exePath -Force
    }
    Invoke-NativeChecked $python @('-m', 'PyInstaller', '--noconfirm', '--clean', $specPath) 'Build client_app.exe' | Out-Null
    if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
        throw "Build hoàn tất nhưng không tìm thấy $exePath."
    }

    $header = [System.IO.File]::ReadAllBytes($exePath)
    if ($header.Length -lt 2 -or $header[0] -ne 0x4D -or $header[1] -ne 0x5A) {
        throw 'File build không phải Windows EXE hợp lệ.'
    }
    $localSha256 = (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash.ToUpperInvariant()
    Write-Host "SHA256 local: $localSha256" -ForegroundColor Green

    Invoke-NativeChecked $git @('add', '-A', '--', '.') 'Đưa source vào staging' | Out-Null
    Invoke-NativeChecked $git @('reset', '--', 'version.json') 'Để version.json cho commit cuối' | Out-Null
    $stagedDiffResult = Invoke-NativeCapture $git @('diff', '--cached', '--quiet')
    if ($stagedDiffResult.ExitCode -eq 0) {
        throw 'Không có thay đổi source để commit cho release này.'
    }
    if ($stagedDiffResult.ExitCode -ne 1) {
        throw 'Không thể kiểm tra thay đổi source trong staging.'
    }

    Invoke-NativeChecked $git @('commit', '-m', "release: $tagName") 'Commit source release' | Out-Null
    $sourceCommitted = $true
    Invoke-NativeChecked $git @('push', 'origin', 'main') 'Push source lên main' | Out-Null
    Invoke-NativeChecked $git @('tag', '-a', $tagName, '-m', "Release $tagName") 'Tạo tag release' | Out-Null
    Invoke-NativeChecked $git @('push', 'origin', $tagName) 'Push tag release' | Out-Null

    Invoke-NativeChecked $gh @(
        'release', 'create', $tagName,
        '--repo', $repository,
        '--verify-tag',
        '--draft',
        '--title', $tagName,
        '--notes', $Changelog
    ) 'Tạo Draft GitHub Release' | Out-Null

    Invoke-NativeChecked $gh @(
        'release', 'upload', $tagName, $exePath, '--repo', $repository
    ) 'Upload client_app.exe vào Draft Release' | Out-Null

    $downloadDirectory = Join-Path ([System.IO.Path]::GetTempPath()) "facebook-tool-release-$([guid]::NewGuid())"
    New-Item -ItemType Directory -Path $downloadDirectory | Out-Null
    Invoke-NativeChecked $gh @(
        'release', 'download', $tagName,
        '--repo', $repository,
        '--pattern', 'client_app.exe',
        '--dir', $downloadDirectory
    ) 'Tải lại asset để kiểm tra SHA256' | Out-Null

    $downloadedExe = Join-Path $downloadDirectory 'client_app.exe'
    if (-not (Test-Path -LiteralPath $downloadedExe -PathType Leaf)) {
        throw 'Không tải lại được client_app.exe từ Draft Release.'
    }
    $releaseSha256 = (Get-FileHash -LiteralPath $downloadedExe -Algorithm SHA256).Hash.ToUpperInvariant()
    Write-Host "SHA256 release: $releaseSha256" -ForegroundColor Green
    if ($releaseSha256 -ne $localSha256) {
        throw 'SHA256 của asset trên GitHub không khớp. Draft Release sẽ không được publish.'
    }

    Invoke-NativeChecked $gh @(
        'release', 'edit', $tagName, '--repo', $repository, '--draft=false', '--latest'
    ) 'Publish Release và đặt Latest' | Out-Null

    $metadata = Get-Content -LiteralPath $versionJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Set-JsonProperty $metadata 'version' $Version
    Set-JsonProperty $metadata 'download_url' "https://github.com/$repository/releases/download/$tagName/client_app.exe"
    Set-JsonProperty $metadata 'sha256' $localSha256
    Set-JsonProperty $metadata 'changelog' $Changelog
    $metadataJson = $metadata | ConvertTo-Json -Depth 100
    Write-Utf8NoBom $versionJsonPath ($metadataJson + [Environment]::NewLine)

    Invoke-NativeChecked $git @('add', '--', 'version.json') 'Đưa version.json vào staging' | Out-Null
    $stagedFilesResult = Invoke-NativeCapture $git @('diff', '--cached', '--name-only')
    $stagedFiles = @($stagedFilesResult.Output | ForEach-Object { "$_" })
    if ($stagedFilesResult.ExitCode -ne 0 -or $stagedFiles.Count -ne 1 -or $stagedFiles[0] -ne 'version.json') {
        throw 'Commit metadata cuối phải chỉ chứa version.json.'
    }
    Invoke-NativeChecked $git @('commit', '-m', "chore: publish metadata for $tagName") 'Commit version.json' | Out-Null
    Invoke-NativeChecked $git @('push', 'origin', 'main') 'Push version.json lên main' | Out-Null

    Write-Host "`nRelease $tagName đã phát hành thành công và được đặt là Latest." -ForegroundColor Green
}
catch {
    $failure = $_
    if (-not $sourceCommitted -and $null -ne $originalClientContent) {
        Write-Utf8NoBom $clientPath $originalClientContent
        Write-Host 'Đã hoàn nguyên CURRENT_VERSION vì release dừng trước commit source.' -ForegroundColor Yellow
    }
}
finally {
    if ($null -ne $downloadDirectory -and (Test-Path -LiteralPath $downloadDirectory)) {
        Remove-Item -LiteralPath $downloadDirectory -Recurse -Force
    }
    Pop-Location
}

if ($null -ne $failure) {
    Write-Error "Release thất bại: $($failure.Exception.Message)"
    exit 1
}
