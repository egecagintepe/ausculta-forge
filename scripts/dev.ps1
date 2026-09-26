<#
.SYNOPSIS
    AuscultaForge Desktop Development Launcher
.DESCRIPTION
    Starts both the Python DSP application bridge (FastAPI/Uvicorn) and the React/Vite
    frontend desktop client simultaneously for local development.
.EXAMPLE
    ./scripts/dev.ps1
#>

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Split-Path -Parent $scriptDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AuscultaForge — Desktop Development Environment" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python virtual environment
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "[ERROR] Python virtual environment not found at .venv" -ForegroundColor Red
    Write-Host "Please create and configure the virtual environment first:" -ForegroundColor Yellow
    Write-Host "  py -3.11 -m venv .venv" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\pip install -r software/requirements.txt" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\pip install -e ./software" -ForegroundColor Yellow
    exit 1
}

# 2. Check Frontend node_modules
$nodeModules = Join-Path $repoRoot "software\frontend\node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "[INFO] Frontend node_modules missing. Running npm install..." -ForegroundColor Yellow
    Push-Location (Join-Path $repoRoot "software\frontend")
    npm install
    Pop-Location
}

Write-Host "[1/2] Starting Python DSP Bridge on http://127.0.0.1:8000..." -ForegroundColor Green
$backendProc = Start-Process -FilePath $pythonExe `
    -ArgumentList "-m", "uvicorn", "pcg_app.app:create_app", "--factory", "--host", "127.0.0.1", "--port", "8000", "--log-level", "info" `
    -WorkingDirectory $repoRoot `
    -PassThru

Write-Host "[2/2] Starting React/Vite Frontend on http://localhost:3000..." -ForegroundColor Green
$frontendDir = Join-Path $repoRoot "software\frontend"

Write-Host ""
Write-Host "Both services are running:" -ForegroundColor Cyan
Write-Host "  - Frontend UI    : http://localhost:3000" -ForegroundColor White
Write-Host "  - Backend Bridge : http://127.0.0.1:8000/api/status" -ForegroundColor White
Write-Host "  - WebSocket Stream: ws://127.0.0.1:8000/ws" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to terminate both processes." -ForegroundColor Yellow
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray

try {
    Push-Location $frontendDir
    npm run dev
}
finally {
    Pop-Location
    Write-Host "`nStopping Python DSP Bridge (PID: $($backendProc.Id))..." -ForegroundColor Yellow
    if ($backendProc -and -not $backendProc.HasExited) {
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "AuscultaForge development environment stopped cleanly." -ForegroundColor Green
}
