$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (!(Test-Path $Python)) {
    python -m venv (Join-Path $Backend ".venv")
}

Push-Location $Backend
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt
Pop-Location

Push-Location $Frontend
if (!(Test-Path (Join-Path $Frontend "node_modules"))) {
    npm install
}
npm run build
Pop-Location

Push-Location $Backend
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name SistemaDeSenhas `
    --collect-submodules app `
    --hidden-import app.main `
    --add-data "$Frontend\dist;frontend\dist" `
    desktop_entry.py
Pop-Location

Write-Host "EXE: $Backend\dist\SistemaDeSenhas.exe"
