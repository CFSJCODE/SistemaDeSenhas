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
Pop-Location

Start-Process powershell -WindowStyle Normal -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$Backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8777 --reload"
)

Start-Process powershell -WindowStyle Normal -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$Frontend'; npm run dev"
)

Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "Backend:  http://127.0.0.1:8777"
