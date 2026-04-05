# dev.ps1 - single entry point for all project tasks
#
# Usage:
#   .\dev.ps1 <command>
#
# Commands:
#   install          Install all three services
#   install-be       Install backend only
#   install-fe       Install frontend only
#   install-admin    Install admin only
#
#   start            Start all three services (each in its own window)
#   start-be         Start backend only  (http://localhost:8000)
#   start-fe         Start frontend only (http://localhost:5174)
#   start-admin      Start admin only    (http://localhost:5173)

param(
    [Parameter(Position = 0)]
    [string]$Command = ""
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ErrorActionPreference = "Stop"

$VenvPython   = "$Root\backend\.venv\Scripts\python.exe"

function Install-Backend {
    Write-Host "==> [backend] Setting up virtual environment..." -ForegroundColor Cyan
    Set-Location "$Root\backend"

    if (-not (Test-Path ".venv")) {
        python -m venv .venv
        Write-Host "    Created .venv" -ForegroundColor Gray
    }

    Write-Host "==> [backend] Installing dependencies into .venv..." -ForegroundColor Cyan
    & $VenvPython -m pip install --upgrade pip setuptools wheel
    & $VenvPython -m pip install -e ".[dev]"

    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "    WARNING: Created backend/.env - set SECRET_KEY before running." -ForegroundColor Yellow
    }

    Write-Host "==> [backend] Running database migrations..." -ForegroundColor Cyan
    & $VenvPython -m alembic upgrade head

    Write-Host "OK Backend ready." -ForegroundColor Green
    Set-Location $Root
}

function Install-Frontend {
    Write-Host "==> [frontend] Installing npm dependencies..." -ForegroundColor Cyan
    Set-Location "$Root\frontend"
    npm install
    if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
    Write-Host "OK Frontend ready." -ForegroundColor Green
    Set-Location $Root
}

function Install-Admin {
    Write-Host "==> [admin] Installing npm dependencies..." -ForegroundColor Cyan
    Set-Location "$Root\admin"
    npm install
    if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
    Write-Host "OK Admin ready." -ForegroundColor Green
    Set-Location $Root
}

function Show-Help {
    Write-Host ""
    Write-Host "Usage: .\dev.ps1 <command>" -ForegroundColor White
    Write-Host ""
    Write-Host "  install          Install all three services"
    Write-Host "  install-be       Install backend only"
    Write-Host "  install-fe       Install frontend only"
    Write-Host "  install-admin    Install admin only"
    Write-Host ""
    Write-Host "  start            Start all three services (each in a new window)"
    Write-Host "  start-be         Start backend  (http://localhost:8000)"
    Write-Host "  start-fe         Start frontend (http://localhost:5174)"
    Write-Host "  start-admin      Start admin    (http://localhost:5173)"
    Write-Host ""
}

if ($Command -eq "install") {
    Install-Backend
    Write-Host ""
    Install-Frontend
    Write-Host ""
    Install-Admin
    Write-Host ""
    Write-Host "All services installed. Edit backend\.env then run: .\dev.ps1 start" -ForegroundColor Green

} elseif ($Command -eq "install-be") {
    Install-Backend

} elseif ($Command -eq "install-fe") {
    Install-Frontend

} elseif ($Command -eq "install-admin") {
    Install-Admin

} elseif ($Command -eq "start-be") {
    Write-Host "==> Starting backend on http://localhost:8000  (docs: http://localhost:8000/docs)" -ForegroundColor Cyan
    Set-Location "$Root\backend"
    & $VenvPython -m uvicorn app.main:app --reload --port 8000

} elseif ($Command -eq "start-fe") {
    Write-Host "==> Starting frontend on http://localhost:5174" -ForegroundColor Cyan
    Set-Location "$Root\frontend"
    npm run dev

} elseif ($Command -eq "start-admin") {
    Write-Host "==> Starting admin on http://localhost:5173" -ForegroundColor Cyan
    Set-Location "$Root\admin"
    npm run dev

} elseif ($Command -eq "start") {
    Write-Host "Starting all services in separate windows..." -ForegroundColor Cyan
    Write-Host "  Backend  -> http://localhost:8000  (docs: /docs)"
    Write-Host "  Frontend -> http://localhost:5174"
    Write-Host "  Admin    -> http://localhost:5173"
    Write-Host ""
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root\backend'; & '$VenvPython' -m uvicorn app.main:app --reload --port 8000"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root\frontend'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root\admin'; npm run dev"
    Write-Host "All three services launched in separate windows." -ForegroundColor Green

} else {
    if ($Command -ne "") {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
    }
    Show-Help
    exit 1
}
