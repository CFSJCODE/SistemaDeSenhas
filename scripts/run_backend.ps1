$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (!(Test-Path $Python)) {
    python -m venv (Join-Path $Backend ".venv")
}

Push-Location $Backend
& $Python -m pip install -r requirements.txt
& $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8777 --reload
Pop-Location
