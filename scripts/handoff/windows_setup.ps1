param(
    [switch]$NonInteractive,
    [switch]$SkipFrontend,
    [string]$JunctionPath = "C:\pcg_starter"
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AuscultaForge — Safe Windows Environment Setup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Repository: $repoRoot"

# Refresh User PATH so newly installed tools are discovered
$machinePath = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
$userPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
if ($machinePath -or $userPath) {
    $env:Path = "$machinePath;$userPath;$env:Path"
}

# 1. Optional ASCII junction check (for ESP-IDF builds without modifying system registry/paths)
$needsAsciiJunction = ($repoRoot -match '[^\x20-\x7E]') -or ($repoRoot -match '\s')
if ($needsAsciiJunction) {
    if (Test-Path -LiteralPath $JunctionPath) {
        Write-Host "[OK] ASCII/space-free path exists at $JunctionPath" -ForegroundColor Green
    } else {
        $createJunction = $NonInteractive
        if (-not $NonInteractive) {
            $answer = Read-Host "Repo path contains spaces or non-ASCII characters. Create NTFS junction at '$JunctionPath' for ESP-IDF builds? [y/N]"
            $createJunction = ($answer -match '^[yYeE]')
        }
        if ($createJunction) {
            cmd /c mklink /J "`"$JunctionPath`"" "`"$repoRoot`""
            if ($LASTEXITCODE -ne 0) {
                Write-Host "[WARN] Could not create junction at $JunctionPath. You can continue with Python/frontend setup." -ForegroundColor Yellow
            } else {
                Write-Host "[OK] Created NTFS junction $JunctionPath -> $repoRoot" -ForegroundColor Green
            }
        }
    }
}

# 2. Check Python 3.11+
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "[STEP] Creating Python .venv..." -ForegroundColor Yellow
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $py311Check = & py -3.11 -c "import sys; print(sys.version)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            & py -3.11 -m venv (Join-Path $repoRoot '.venv')
        } else {
            Write-Host "[WARN] Python 3.11 not found via 'py -3.11'; checking default python..." -ForegroundColor Yellow
            & python -m venv (Join-Path $repoRoot '.venv')
        }
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv (Join-Path $repoRoot '.venv')
    } else {
        throw "Python 3.11+ not found. Install Python 3.11 (user scope) and retry."
    }
} else {
    Write-Host "[OK] Existing .venv found at $venvPython" -ForegroundColor Green
}

$pyVerOut = & $venvPython -c "import sys; assert sys.version_info >= (3, 11), f'Python >=3.11 required, got {sys.version}'; print(sys.version.split()[0])"
if ($LASTEXITCODE -ne 0) {
    throw "Python version check failed inside .venv."
}
Write-Host "[OK] .venv Python version: $pyVerOut" -ForegroundColor Green

# 3. Install/verify Python packages
Write-Host "[STEP] Installing software/requirements.txt and editable package..." -ForegroundColor Yellow
& $venvPython -m pip install -r (Join-Path $repoRoot 'software\requirements.txt') -e (Join-Path $repoRoot 'software')
if ($LASTEXITCODE -ne 0) {
    throw "pip install failed."
}

# 4. Frontend npm ci (if needed)
if (-not $SkipFrontend) {
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        throw "Node.js not found. Install Node LTS (>=20.19.0 or >=22.12.0) and retry."
    }
    $nodeVer = (& node --version).Trim()
    Write-Host "[OK] Node version: $nodeVer" -ForegroundColor Green
    $nodeModules = Join-Path $repoRoot 'software\frontend\node_modules'
    if (-not (Test-Path -LiteralPath $nodeModules)) {
        Write-Host "[STEP] Installing frontend dependencies via npm.cmd ci..." -ForegroundColor Yellow
        Push-Location (Join-Path $repoRoot 'software\frontend')
        try {
            & npm.cmd ci
            if ($LASTEXITCODE -ne 0) {
                throw "npm.cmd ci failed."
            }
        } finally {
            Pop-Location
        }
    } else {
        Write-Host "[OK] Frontend node_modules present." -ForegroundColor Green
    }
}

# 5. Run passive preflight verification
Write-Host "[STEP] Running passive preflight check..." -ForegroundColor Yellow
& (Join-Path $PSScriptRoot 'windows_preflight.ps1')
exit $LASTEXITCODE
