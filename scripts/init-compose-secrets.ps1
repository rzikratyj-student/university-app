[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$secretDir = Join-Path $projectRoot '.local/compose'
foreach ($part in @($projectRoot, (Join-Path $projectRoot '.local'), $secretDir)) {
    if (Test-Path -LiteralPath $part) {
        if (((Get-Item -LiteralPath $part -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Refusing redirected secret directory.' }
    } else { [IO.Directory]::CreateDirectory($part) | Out-Null }
}
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try {
    foreach ($name in @('admin-password', 'app-password')) {
        $path = Join-Path $secretDir $name
        if (Test-Path -LiteralPath $path) {
            $file = Get-Item -LiteralPath $path -Force
            if (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $file.PSIsContainer -or $file.Length -eq 0) { throw 'Invalid existing secret file.' }
            continue # Never rotate or overwrite an existing password.
        }
        $bytes = New-Object byte[] 32
        $rng.GetBytes($bytes)
        $secret = [BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
        $stream = [IO.File]::Open($path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            $encoded = [Text.Encoding]::ASCII.GetBytes($secret)
            $stream.Write($encoded, 0, $encoded.Length)
        } finally { $stream.Dispose() }
    }
} finally { $rng.Dispose() }
Write-Output 'Compose secret files are ready; existing values were preserved. No credentials displayed.'
