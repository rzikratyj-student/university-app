# Explicit, fail-fast readiness -> migration -> web sequence.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Push-Location $projectRoot
try {
    $composeArgs = @('compose', '-p', 'campus-compose-dev', '-f', (Join-Path $projectRoot 'compose.yaml'))
    & docker @composeArgs config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed.' }
    & docker @composeArgs build web
    if ($LASTEXITCODE -ne 0) { throw 'Image build failed.' }
    & docker @composeArgs stop web
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop the Compose web service before migration.' }
    & docker @composeArgs up -d --wait db
    if ($LASTEXITCODE -ne 0) { throw 'Database is not ready; migration and web startup cancelled.' }
    & docker @composeArgs --profile tools run --rm migrate
    if ($LASTEXITCODE -ne 0) { throw 'Migration failed; web startup cancelled.' }
    & docker @composeArgs up -d --wait web
    if ($LASTEXITCODE -ne 0) { throw 'Web startup failed.' }
} finally { Pop-Location }
