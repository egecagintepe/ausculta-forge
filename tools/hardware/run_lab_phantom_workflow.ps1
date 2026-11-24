<#
.SYNOPSIS
AuscultaForge — Unified Laboratory Phantom Experiment Workflow (25 Nov 2026)

.DESCRIPTION
Self-bootstrapping, zero-prompt laboratory automation script for the Week 9
physical phantom PCG feasibility gate:
1. Self-bootstraps Python virtual environment (.venv) if missing on a clean laptop.
2. Supports -SetupOnly for offline verification without triggering hardware or audio.
3. Discovers ESP32-S3 USB CDC port automatically (fails safely if 0 or >1 found).
4. Records 10s fresh quiet baseline & verifies SHA-256.
5. Plays low-volume calibration tone (-18 dBFS, 120 Hz).
6. Requires explicit operator confirmation of physical power, BTL isolation, and vibration.
7. Executes synchronized reference PCG playback & live INMP441 acquisition.
8. Packages all evidence into a timestamped, signed ZIP bundle.

.EXAMPLE
.\tools\hardware\run_lab_phantom_workflow.ps1 -SetupOnly
.\tools\hardware\run_lab_phantom_workflow.ps1 -Simulate
.\tools\hardware\run_lab_phantom_workflow.ps1
#>

param(
    [string]$Port = "",
    [string]$Reference = "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav",
    [string]$Operator = "Kaan_Ozan_Ege",
    [string]$Notes = "W10_P0_Physical_Phantom",
    [switch]$Simulate,
    [switch]$SetupOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Runner = Join-Path $RepoRoot "tools\hardware\run_phantom_pcg_experiment.py"
$Packager = Join-Path $RepoRoot "tools\hardware\pack_lab_return.py"

# ==============================================================================
# 0. Sanal Ortam Kontrolu ve Otomatik Kurulum (Bootstrap)
# ==============================================================================
if (-not (Test-Path $Py)) {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  AUSCULTAFORGE — SANAL ORTAM OTOMATIK KURULUMU (BOOTSTRAP)" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "[BILGI] Python sanal ortami ($Py) bulunamadi." -ForegroundColor Yellow
    Write-Host "[BILGI] Pip tekerlerini (wheel) indirmek icin tek seferlik internet baglantisi gereklidir." -ForegroundColor Yellow
    Write-Host "[BILGI] Kurulum bittikten sonra tum testler ve laboratuvar is akisi %100 cevrimdisi (offline) calisir.`n" -ForegroundColor Cyan

    $BasePy = $null
    $Candidates = @(
        @{ Exe = "py"; Args = @("-3.11") },
        @{ Exe = "py"; Args = @("-3.12") },
        @{ Exe = "python"; Args = @() }
    )
    foreach ($cand in $Candidates) {
        $cmd = Get-Command $cand.Exe -ErrorAction SilentlyContinue
        if ($cmd) {
            try {
                & $cmd.Source @($cand.Args) -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $BasePy = @{ Path = $cmd.Source; Args = $cand.Args }
                    break
                }
            } catch {}
        }
    }
    if (-not $BasePy) {
        $PathCandidates = @(
            (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
            (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
            (Join-Path $env:ProgramFiles 'Python311\python.exe'),
            (Join-Path $env:ProgramFiles 'Python312\python.exe')
        )
        foreach ($p in $PathCandidates) {
            if (Test-Path $p) {
                $BasePy = @{ Path = $p; Args = @() }
                break
            }
        }
    }

    if (-not $BasePy) {
        throw "[HATA] Sistemde Python 3.11 veya uzeri bulunamadi. Lutfen Python 3.11+ yukleyin ve PATH ortam degiskenine ekleyin."
    }

    Write-Host "[1/3] Sanal ortam olusturuluyor: .venv ..." -ForegroundColor Green
    & $BasePy.Path @($BasePy.Args) -m venv (Join-Path $RepoRoot ".venv")
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Py)) {
        throw "[HATA] Python sanal ortami (.venv) olusturulamadi."
    }

    Write-Host "[2/3] Temel kutuphaneler yukleniyor (software/requirements.txt)..." -ForegroundColor Green
    & $Py -m pip install --upgrade pip --quiet
    & $Py -m pip install -r (Join-Path $RepoRoot "software\requirements.txt") --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "[HATA] requirements.txt kutuphaneleri yuklenemedi. Internet baglantinizi kontrol edin."
    }

    Write-Host "[3/3] AuscultaForge paketi gelistirici kipinde baglaniyor (-e software)..." -ForegroundColor Green
    & $Py -m pip install -e (Join-Path $RepoRoot "software") --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "[HATA] 'software' modulu kurulurken hata olustu."
    }

    Write-Host "[TAMAMLANDI] Sanal ortam basariyla hazirlandi!`n" -ForegroundColor Green
}

# ==============================================================================
# -SetupOnly: Laboratuvar Oncesi Dogrulama (Hardware/Audio tetiklemez)
# ==============================================================================
if ($SetupOnly) {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  AUSCULTAFORGE — HAZIRLIK VE ORTAM DOGRULAMA (-SetupOnly)" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    Write-Host "`n[1/3] Temel Python kutuphaneleri test ediliyor..." -ForegroundColor Green
    & $Py -c "import pcg_app; import serial; import scipy; import numpy; print('  [OK] Python cekirdek modulleri eksiksiz yuklu.')"
    if ($LASTEXITCODE -ne 0) { throw "[HATA] Modul ice aktarma hatasi!" }

    Write-Host "`n[2/3] Referans PCG ses dosyasi ve SHA-256 hash'i denetleniyor..." -ForegroundColor Green
    $RefPath = Join-Path $RepoRoot $Reference
    if (-not (Test-Path $RefPath)) {
        throw "[HATA] Referans PCG dosyasi bulunamadi: $RefPath"
    }
    $RefHash = (Get-FileHash -Path $RefPath -Algorithm SHA256).Hash.ToLower()
    $ExpectedHash = "108df8f77491a5706209aa5b467ed10ac43f2a0b847801fe666ba8146dcbf8e8"
    if ($RefHash -ne $ExpectedHash) {
        throw "[HATA] Referans PCG hash uyusmazligi!`n  Alinan:   $RefHash`n  Beklenen: $ExpectedHash"
    }
    Write-Host "  [OK] Referans PCG dogrulandi: $RefPath (SHA256: $RefHash)" -ForegroundColor Green

    Write-Host "`n[3/3] Birim testleri calistiriliyor (35/35 test)..." -ForegroundColor Green
    & $Py -m pytest (Join-Path $RepoRoot "software\tests\test_phantom_pcg_experiment.py") (Join-Path $RepoRoot "software\tests\test_recording.py") -q
    if ($LASTEXITCODE -ne 0) { throw "[HATA] Test paketinde basarisiz testler var!" }

    Write-Host "`n============================================================" -ForegroundColor Green
    Write-Host "  TUM TESTLER VE ORTAM KONTROLLERI BASARILI (PASS)" -ForegroundColor Green
    Write-Host "  Sistem yarin sabahki fiziksel laboratuvar icin %100 hazirdir." -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    exit 0
}

# Referans dosya varlik kontrolu
$RefPath = Join-Path $RepoRoot $Reference
if (-not (Test-Path $RefPath)) {
    throw "[HATA] Referans PCG dosyasi bulunamadi: $RefPath"
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  AUSCULTAFORGE — 25 KASIM 2026 LABORATUVAR IS AKISI" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# ==============================================================================
# -Simulate: Deterministik Yazilim Simulasyon Kipi
# ==============================================================================
if ($Simulate) {
    Write-Host "[SIMULATE] Deterministik simulasyon smoke check baslatiliyor..." -ForegroundColor Yellow
    & $Py $Runner --simulate --reference $Reference --operator $Operator --notes "$Notes (SIMULATE)"
    exit $LASTEXITCODE
}

# ==============================================================================
# 1. USB CDC Port Discovery (Sifir istem, tam guvenlik)
# ==============================================================================
Write-Host "`n[1/5] USB CDC portlari taraniyor..." -ForegroundColor Green
$PortsJsonRaw = & $Py $Runner --discover-ports
$PortsJson = $PortsJsonRaw | ConvertFrom-Json
$PortsJson.ports | Format-Table device, description, is_espressif_usb_cdc

if ([string]::IsNullOrWhiteSpace($Port)) {
    $EspPorts = @($PortsJson.ports | Where-Object { $_.is_espressif_usb_cdc -eq $true })
    if ($EspPorts.Count -eq 1) {
        $Port = $EspPorts[0].device
        Write-Host "Otomatik secilen Espressif USB CDC portu: $Port" -ForegroundColor Green
    } elseif ($EspPorts.Count -eq 0) {
        Write-Host "`n[HATA] Bagli Espressif USB CDC (VID: 0x303A) aygiti bulunamadi!" -ForegroundColor Red
        Write-Host "Kontrol Listesi:" -ForegroundColor Yellow
        Write-Host " 1. ESP32-S3 kartinin USB-C kablosu dogrudan laptopa bagli mi?" -ForegroundColor Yellow
        Write-Host " 2. Kullanilan kablo veri (data) kablosu mu (yalnizca sarj kablosu veri iletmez)?" -ForegroundColor Yellow
        Write-Host " 3. Arduino IDE Seri Monitoru, PuTTY veya WebSerial tarayici sekmesi acik mi?" -ForegroundColor Yellow
        Write-Host "Kablonuzu takip tekrar deneyin veya hedef port biliniyorsa '-Port COMxx' parametresi verin.`n" -ForegroundColor Yellow
        throw "Bagli Espressif USB CDC aygiti bulunamadi. Is akisi durduruldu."
    } else {
        $DeviceList = ($EspPorts | ForEach-Object { $_.device }) -join ", "
        Write-Host "`n[HATA] Birden fazla ($($EspPorts.Count)) Espressif USB CDC portu tespit edildi: $DeviceList" -ForegroundColor Red
        Write-Host "Belirsizlik nedeniyle otomatik secim yapilamaz. Lutfen diger gelistirme kartlarini cikarin veya '-Port COMxx' parametresi verin.`n" -ForegroundColor Yellow
        throw "Birden fazla Espressif portu tespit edildi. Is akisi durduruldu."
    }
} else {
    Write-Host "Belirtilen port kullaniliyor: $Port" -ForegroundColor Green
}

# ==============================================================================
# 2. Fresh 10s Quiet Baseline
# ==============================================================================
Write-Host "`n[2/5] Sessiz taban olcumu (10s) aliniyor. Exciter KAPALI ve oda SESSIZ olmali!" -ForegroundColor Yellow
$QuietConfirm = Read-Host "Hazir oldugunuzda ENTER'a basin (iptal icin CTRL+C)"
$QuietOut = & $Py $Runner --quiet-baseline-only --port $Port --operator $Operator --notes "Quiet_Baseline"
$QuietObj = $QuietOut | ConvertFrom-Json
$QuietWav = $QuietObj.raw_wav_path
Write-Host "Sessiz kayit dogrulandi: $QuietWav (SHA256: $($QuietObj.raw_wav_sha256))" -ForegroundColor Green

# ==============================================================================
# 3. Low-Volume Calibration Tone
# ==============================================================================
Write-Host "`n[3/5] Dusuk seviyeli kalibrasyon tonu (-18 dBFS, 120 Hz) caliniyor..." -ForegroundColor Yellow
& $Py $Runner --play-calibration-tone | Out-Null

# ==============================================================================
# 4. Explicit Operator Physical Confirmation
# ==============================================================================
$RoutingConfirm = Read-Host "PC ses cikisi PAM8403'e bagli, PAM8403 bagimsiz 5V beslemeli ve exciter titriyor mu? (EVET yazin)"
if ($RoutingConfirm -ne "EVET") {
    Write-Host "[DURDURULDU] Fiziksel ses yonlendirmesi onaylanmadi." -ForegroundColor Red
    exit 1
}

# ==============================================================================
# 5. Synchronized Reference PCG Playback & Capture
# ==============================================================================
Write-Host "`n[4/5] Senkronize PCG fantom deneyi baslatiliyor..." -ForegroundColor Green
& $Py $Runner --port $Port --reference $Reference --quiet-session $QuietWav --play-audio --verify-audio-routing --operator $Operator --notes $Notes
$RunExit = $LASTEXITCODE

# ==============================================================================
# 6. Package Evidence ZIP
# ==============================================================================
Write-Host "`n[5/5] Kanit paketi (ZIP) hazirlaniyor..." -ForegroundColor Green
& $Py $Packager --operator $Operator --notes $Notes
exit $RunExit
