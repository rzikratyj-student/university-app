# Packages only reviewed source files. No recursive directory archiving.
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$rootPrefix = $projectRoot.TrimEnd('\') + '\'

function Assert-RegularPath([string]$Path) {
    $current = Get-Item -LiteralPath $Path -Force
    while ($null -ne $current) {
        if (($current.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Symbolic links and junctions are not allowed in package paths.'
        }
        $current = if ($current -is [IO.DirectoryInfo]) { $current.Parent } else { $current.Directory }
    }
}

Assert-RegularPath $projectRoot
$manifestPath = Join-Path $projectRoot 'source-manifest.json'
Assert-RegularPath $manifestPath
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$manifest = @($manifest)
if ($manifest.Count -eq 0) { throw 'Empty source manifest.' }
$seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
$approved = @()
$rootFiles = @('.gitignore', '.env.example', 'AGENTS.md', 'README.md', 'SECURITY_AUDIT.md', 'requirements.txt', 'source-manifest.json', 'config.py', 'run.py')
foreach ($relative in $manifest) {
    if ($relative -isnot [string] -or $relative -match '\\|:|(^|/)\.{1,2}(/|$)' -or [IO.Path]::IsPathRooted($relative)) {
        throw 'Invalid relative source path.'
    }
    if (-not $seen.Add($relative)) { throw 'Duplicate source entry.' }
    $allowed = $rootFiles -ccontains $relative
    if (-not $allowed) {
        $allowed = $relative -cmatch '^(app|tests|migrations|scripts)/[A-Za-z0-9_./-]+\.(py|ps1|html|css|js|md|txt|ini|mako)$' -or $relative -ceq 'migrations/README'
    }
    if (-not $allowed -or $relative -match '(^|/)(\.[^/]+|__pycache__|secrets|backups|pgdata|postgres-data|postgres_data)(/|$)' -and $relative -notin @('.gitignore', '.env.example')) {
        throw 'Manifest contains a forbidden file.'
    }
    $full = [IO.Path]::GetFullPath((Join-Path $projectRoot $relative))
    if (-not $full.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Path escapes project.' }
    Assert-RegularPath $full
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw 'Source entry is not a file.' }
    $approved += [PSCustomObject]@{ Name = $relative; Path = $full }
}

# Fail closed when the local scanner or its dependencies are unavailable.
$python = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Install project dependencies in .venv first.' }
& $python (Join-Path $projectRoot 'scripts/check_secrets.py')
if ($LASTEXITCODE -ne 0) { throw 'Secret scan did not pass; no archive created.' }

$localPath = Join-Path $projectRoot '.local'
if (-not (Test-Path -LiteralPath $localPath)) { [IO.Directory]::CreateDirectory($localPath) | Out-Null }
Assert-RegularPath $localPath
$outputDir = Join-Path $localPath 'exports'
if (-not (Test-Path -LiteralPath $outputDir)) { [IO.Directory]::CreateDirectory($outputDir) | Out-Null }
Assert-RegularPath $outputDir
$name = 'campus-source-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8) + '.zip'
$archivePath = Join-Path $outputDir $name
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$stream = $null
$zip = $null
try {
    # CreateNew never overwrites an existing archive.
    $stream = [IO.File]::Open($archivePath, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $zip = New-Object IO.Compression.ZipArchive($stream, [IO.Compression.ZipArchiveMode]::Create, $true)
    foreach ($entry in $approved) {
        Assert-RegularPath $entry.Path
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $entry.Path, $entry.Name, [IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
} finally {
    if ($null -ne $zip) { $zip.Dispose() }
    if ($null -ne $stream) { $stream.Dispose() }
}

$readback = [IO.Compression.ZipFile]::OpenRead($archivePath)
try {
    $actual = @($readback.Entries | ForEach-Object { $_.FullName })
    if ($actual.Count -ne $approved.Count -or @(Compare-Object $manifest $actual -CaseSensitive).Count -ne 0) {
        throw 'Archive verification failed; do not share this archive.'
    }
} finally { $readback.Dispose() }
$sha = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
Write-Output "Created: $archivePath"
Write-Output "Source files: $($approved.Count)"
Write-Output "SHA256: $sha"
