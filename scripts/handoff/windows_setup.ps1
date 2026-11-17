param(
    [switch]$NonInteractive,
    [switch]$SkipFrontend,
    [switch]$SkipAutoInstall,
    [switch]$RequireEspIdf,
    [string]$PythonExeOverride = "",
    [string]$NodeExeOverride = "",
    [string]$JunctionPath = "C:\pcg_starter"
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

function Refresh-ProcessPath {
    $machinePath = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    $parts = @($machinePath, $userPath, $env:Path) | Where-Object { $_ }
    $env:Path = ($parts -join ';')
}

function Test-Python311Plus {
    param([string]$ExePath, [string[]]$PrefixArgs = @())
    if (-not $ExePath) { return $false }
    try {
        $null = & $ExePath @PrefixArgs -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Resolve-PythonCommand {
    param([string]$Override, [string]$VenvPython)
    if ($Override -ne "") {
        if ((Test-Path -LiteralPath $Override) -and (Test-Python311Plus -ExePath $Override)) {
            return @{ Exe = $Override; Args = @() }
        }
        return $null
    }
    if ((Test-Path -LiteralPath $VenvPython) -and (Test-Python311Plus -ExePath $VenvPython)) {
        return @{ Exe = $VenvPython; Args = @() }
    }
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd -and (Test-Python311Plus -ExePath $pyCmd.Source -PrefixArgs @('-3.11'))) {
        return @{ Exe = $pyCmd.Source; Args = @('-3.11') }
    }
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd -and (Test-Python311Plus -ExePath $pythonCmd.Source)) {
        return @{ Exe = $pythonCmd.Source; Args = @() }
    }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:ProgramFiles 'Python311\python.exe'),
        (Join-Path $env:ProgramFiles 'Python312\python.exe'),
        (Join-Path $env:ProgramFiles 'Python313\python.exe')
    )
    foreach ($c in $candidates) {
        if ((Test-Path -LiteralPath $c) -and (Test-Python311Plus -ExePath $c)) {
            return @{ Exe = $c; Args = @() }
        }
    }
    return $null
}

function Install-UserPython311 {
    Write-Host "[STEP] Python 3.11+ eksik - kullanici kapsamli kurulum deneniyor..." -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        & $winget.Source install --id Python.Python.3.11 --scope user --silent --accept-package-agreements --accept-source-agreements
        Refresh-ProcessPath
        $found = Resolve-PythonCommand -Override "" -VenvPython ""
        if ($found) { return $found }
    }
    $url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
    $installer = Join-Path $env:TEMP 'auscultaforge-python-3.11.9-amd64.exe'
    Write-Host "[STEP] Resmi Python 3.11.9 yukleyicisi indiriliyor: $url" -ForegroundColor Yellow
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing -TimeoutSec 180
    $sig = Get-AuthenticodeSignature -FilePath $installer
    if ($sig.Status -ne 'Valid') {
        throw "[SECURITY] Indirilen Python yukleyicisinin dijital imzasi dogrulanamadi ($($sig.Status))."
    }
    $proc = Start-Process -FilePath $installer -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1' -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        throw "Python 3.11.9 yukleyicisi hata kodu ile cikti: $($proc.ExitCode)"
    }
    Refresh-ProcessPath
    return Resolve-PythonCommand -Override "" -VenvPython ""
}

function Resolve-NodeCommand {
    param([string]$Override)
    if ($Override -ne "") {
        if (Test-Path -LiteralPath $Override) { return $Override }
        return $null
    }
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    if ($nodeCmd) { return $nodeCmd.Source }
    $localRoot = Join-Path $env:LOCALAPPDATA 'Programs\nodejs'
    $candidates = @(
        (Join-Path $env:ProgramFiles 'nodejs\node.exe'),
        (Join-Path $localRoot 'node.exe')
    )
    if (Test-Path -LiteralPath $localRoot) {
        Get-ChildItem -Path $localRoot -Filter 'node.exe' -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            $candidates += $_.FullName
        }
    }
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return $null
}

function Install-UserNodeLts {
    Write-Host "[STEP] Node.js LTS eksik - kullanici kapsamli kurulum deneniyor..." -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        & $winget.Source install --id OpenJS.NodeJS.LTS --scope user --silent --accept-package-agreements --accept-source-agreements
        Refresh-ProcessPath
        $found = Resolve-NodeCommand -Override ""
        if ($found) { return $found }
    }
    $url = 'https://nodejs.org/dist/v22.14.0/node-v22.14.0-win-x64.zip'
    $zipPath = Join-Path $env:TEMP 'auscultaforge-node-v22.14.0-win-x64.zip'
    $destRoot = Join-Path $env:LOCALAPPDATA 'Programs\nodejs'
    New-Item -ItemType Directory -Force -Path $destRoot | Out-Null
    Write-Host "[STEP] Resmi Node.js LTS arsivi indiriliyor: $url" -ForegroundColor Yellow
    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing -TimeoutSec 180
    Expand-Archive -Path $zipPath -DestinationPath $destRoot -Force
    $nodeBinDir = Join-Path $destRoot 'node-v22.14.0-win-x64'
    $env:Path = "$nodeBinDir;$env:Path"
    $existingUserPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    if (-not $existingUserPath) { $existingUserPath = "" }
    if ($existingUserPath -notlike "*$nodeBinDir*") {
        [System.Environment]::SetEnvironmentVariable('Path', "$nodeBinDir;$existingUserPath", 'User')
    }
    return Resolve-NodeCommand -Override ""
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AuscultaForge - Safe Windows Environment Setup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Repository: $repoRoot"

Refresh-ProcessPath

# 1. Optional ASCII junction check (needed only for ESP-IDF builds; Python/G1/staged-G2 work anywhere)
$needsAsciiJunction = ($repoRoot -match '[^\x20-\x7E]') -or ($repoRoot -match '\s')
if ($needsAsciiJunction) {
    if (Test-Path -LiteralPath $JunctionPath) {
        Write-Host "[OK] ASCII/space-free path exists at $JunctionPath" -ForegroundColor Green
    } else {
        $createJunction = $RequireEspIdf
        if (-not $NonInteractive -and $RequireEspIdf) {
            $answer = Read-Host "Repo path contains spaces or non-ASCII chars. Create NTFS junction '$JunctionPath' for ESP-IDF? [y/N]"
            $createJunction = ($answer -match '^[yYeE]')
        }
        if ($createJunction) {
            cmd /c mklink /J "`"$JunctionPath`"" "`"$repoRoot`"" | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "[WARN] Could not create junction at $JunctionPath. Continuing with Python/staged binary workflow." -ForegroundColor Yellow
            } else {
                Write-Host "[OK] Created NTFS junction $JunctionPath -> $repoRoot" -ForegroundColor Green
            }
        } else {
            Write-Host "[INFO] Path contains spaces/non-ASCII chars; Python & staged G1/G2 binaries work directly. For ESP-IDF rebuilds use $JunctionPath." -ForegroundColor DarkGray
        }
    }
}

# 2. Check / install Python 3.11+
$venvDir = Join-Path $repoRoot '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$resolvedPy = Resolve-PythonCommand -Override $PythonExeOverride -VenvPython $venvPython

if (-not $resolvedPy) {
    if ($SkipAutoInstall) {
        Write-Host "[MISSING_PYTHON] Python 3.11+ bulunamadi (SkipAutoInstall aktif)." -ForegroundColor Red
        exit 2
    }
    $resolvedPy = Install-UserPython311
    if (-not $resolvedPy) {
        Write-Host "[MISSING_PYTHON] Python 3.11+ otomatik kurulamadi. Resmi python.org uzerinden Python 3.11 kurup tekrar calistirin." -ForegroundColor Red
        exit 2
    }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "[STEP] Creating Python .venv using $($resolvedPy.Exe)..." -ForegroundColor Yellow
    & $resolvedPy.Exe @($resolvedPy.Args) -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Python .venv"
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
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r (Join-Path $repoRoot 'software\requirements.txt') -e (Join-Path $repoRoot 'software')
if ($LASTEXITCODE -ne 0) {
    throw "pip install failed."
}

# 4. Node.js + Frontend npm ci (if needed)
if (-not $SkipFrontend) {
    $nodeExe = Resolve-NodeCommand -Override $NodeExeOverride
    if (-not $nodeExe) {
        if ($SkipAutoInstall) {
            Write-Host "[MISSING_NODE] Node.js LTS bulunamadi (SkipAutoInstall aktif)." -ForegroundColor Red
            exit 3
        }
        $nodeExe = Install-UserNodeLts
        if (-not $nodeExe) {
            Write-Host "[MISSING_NODE] Node.js otomatik kurulamadi. https://nodejs.org uzerinden LTS kurup tekrar deneyin." -ForegroundColor Red
            exit 3
        }
    }
    $nodeDir = Split-Path $nodeExe -Parent
    if ($env:Path -notlike "*$nodeDir*") { $env:Path = "$nodeDir;$env:Path" }
    $nodeVer = (& $nodeExe --version).Trim()
    Write-Host "[OK] Node version: $nodeVer ($nodeExe)" -ForegroundColor Green
    $nodeModules = Join-Path $repoRoot 'software\frontend\node_modules'
    if (-not (Test-Path -LiteralPath $nodeModules)) {
        Write-Host "[STEP] Installing frontend dependencies via npm.cmd ci..." -ForegroundColor Yellow
        $npmCmd = Join-Path $nodeDir 'npm.cmd'
        if (-not (Test-Path -LiteralPath $npmCmd)) { $npmCmd = 'npm.cmd' }
        Push-Location (Join-Path $repoRoot 'software\frontend')
        try {
            & $npmCmd ci
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

# 5. ESP-IDF policy: DO NOT download 2 GB SDK unless explicitly required
$stagedG1 = Join-Path $repoRoot 'firmware\releases\g1_release_20261117\firmware_build_manifest.json'
$stagedG2 = Join-Path $repoRoot 'firmware\releases\g2_candidate_20261117\firmware_build_manifest.json'
$idfCmd = Get-Command idf.py -ErrorAction SilentlyContinue
if ((Test-Path -LiteralPath $stagedG1) -and (Test-Path -LiteralPath $stagedG2) -and (-not $RequireEspIdf)) {
    Write-Host "[OK] Staged & hash-verified G1/G2 firmware binaries exist; ESP-IDF download skipped (only needed if GPIO pins differ from BCLK=4, WS=5, DIN=6)." -ForegroundColor Green
} elseif ($RequireEspIdf -and (-not $idfCmd)) {
    Write-Host "[WARN] -RequireEspIdf specified but idf.py is not active. Install ESP-IDF v5.5.1 per docs/engineering/hardware/WINDOWS_LAPTOP_SETUP.md." -ForegroundColor Yellow
    exit 4
}

# 6. Run passive preflight verification
Write-Host "[STEP] Running passive preflight check..." -ForegroundColor Yellow
& (Join-Path $PSScriptRoot 'windows_preflight.ps1')
exit $LASTEXITCODE
