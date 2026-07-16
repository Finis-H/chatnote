[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
$buildId = Get-Date -Format 'yyyyMMdd-HHmmss'
$stageRoot = Join-Path $repoRoot "temp\windows-release-$buildId"
$sidecarSource = Join-Path $stageRoot 'dist\vault_engine'
$sidecarBin = Join-Path $repoRoot 'chat-ui\src-tauri\bin'

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python virtual environment was not found: $python"
}

New-Item -ItemType Directory -Path $stageRoot | Out-Null

& $python -m PyInstaller --noconfirm `
    --distpath (Join-Path $stageRoot 'dist') `
    --workpath (Join-Path $stageRoot 'build') `
    (Join-Path $repoRoot 'vault_engine.spec')
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Copy-Item -LiteralPath (Join-Path $sidecarSource 'vault_engine.exe') `
    -Destination (Join-Path $sidecarBin 'vault_engine-x86_64-pc-windows-msvc.exe') -Force

& robocopy (Join-Path $sidecarSource '_internal') (Join-Path $sidecarBin '_internal') /E /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -gt 7) {
    throw "Failed to copy the bundled Python runtime. Robocopy exit code: $LASTEXITCODE"
}

Push-Location (Join-Path $repoRoot 'chat-ui')
try {
    npm run tauri -- build
    if ($LASTEXITCODE -ne 0) {
        throw "Tauri bundle build failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Output (Join-Path $repoRoot 'chat-ui\src-tauri\target\release\bundle\nsis\Vault OS_0.1.0_x64-setup.exe')
