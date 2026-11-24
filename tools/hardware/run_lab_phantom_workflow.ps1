<#
.SYNOPSIS
AuscultaForge — Unified Laboratory Phantom Experiment Workflow (25 Nov 2026)

.DESCRIPTION
Guides the operator through all 10 verified steps of the physical phantom gate:
1. Dynamic USB CDC port discovery
2. Fresh 10s quiet baseline acquisition & SHA-256 verification
3. Low-volume calibration tone playback (-18 dBFS, 120 Hz)
4. Explicit operator confirmation of physical routing (never auto-attested)
5. Synchronized CirCor PCG playback & live INMP441 acquisition
6. Chronological report & evidence ZIP packaging

.EXAMPLE
.\tools\hardware\run_lab_phantom_workflow.ps1
.\tools\hardware\run_lab_phantom_workflow.ps1 -Simulate
#>

param(
    [string]$Port = "",
    [string]$Reference = "data/raw/week6_real_pcg_20261026/circor/40058_AV.wav",
    [string]$Operator = "Kaan_Ozan_Ege",
    [string]$Notes = "W10_P0_Physical_Phantom",
    [switch]$Simulate
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Runner = Join-Path $RepoRoot "tools\hardware\run_phantom_pcg_experiment.py"
$Packager = Join-Path $RepoRoot "tools\hardware\pack_lab_return.py"

if (-not (Test-Path $Py)) {
    throw "Virtual environment Python not found at $Py"
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  AUSCULTAFORGE — 25 KASIM 2026 LABORATUVAR IS AKISI" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if ($Simulate) {
    Write-Host "[SIMULATE] Running deterministic simulation smoke check..." -ForegroundColor Yellow
    & $Py $Runner --simulate --reference $Reference --operator $Operator --notes "$Notes (SIMULATE)"
    exit $LASTEXITCODE
}

# 1. USB CDC Port Discovery
Write-Host "`n[1/5] USB CDC portlari taraniyor..." -ForegroundColor Green
$PortsJson = & $Py $Runner --discover-ports | ConvertFrom-Json
$PortsJson.ports | Format-Table device, description, is_espressif_usb_cdc

if ([string]::IsNullOrWhiteSpace($Port)) {
    $EspPorts = @($PortsJson.ports | Where-Object { $_.is_espressif_usb_cdc -eq $true })
    if ($EspPorts.Count -eq 1) {
        $Port = $EspPorts[0].device
        Write-Host "Secilen Espressif USB CDC portu: $Port" -ForegroundColor Green
    } else {
        $Port = Read-Host "Lutfen ESP32-S3 USB CDC COM portunu girin (orn. COM14)"
    }
}

# 2. Fresh 10s Quiet Baseline
Write-Host "`n[2/5] Sessiz taban olcumu (10s) aliniyor. Exciter KAPALI ve oda SESSIZ olmali!" -ForegroundColor Yellow
$QuietConfirm = Read-Host "Hazir oldugunuzda ENTER'a basin (iptal icin CTRL+C)"
$QuietOut = & $Py $Runner --quiet-baseline-only --port $Port --operator $Operator --notes "Quiet_Baseline"
$QuietObj = $QuietOut | ConvertFrom-Json
$QuietWav = $QuietObj.raw_wav_path
Write-Host "Sessiz kayit dogrulandi: $QuietWav (SHA256: $($QuietObj.raw_wav_sha256))" -ForegroundColor Green

# 3. Low-volume calibration tone
Write-Host "`n[3/5] Dusuk seviyeli kalibrasyon tonu (-18 dBFS, 120 Hz) caliniyor..." -ForegroundColor Yellow
& $Py $Runner --play-calibration-tone | Out-Null

# 4. Explicit Operator Confirmation
$RoutingConfirm = Read-Host "PC ses cikisi PAM8403'e bagli, PAM8403 5V beslemeli ve exciter titriyor mu? (EVET yazin)"
if ($RoutingConfirm -ne "EVET") {
    Write-Host "[DURDURULDU] Fiziksel ses yonlendirmesi onaylanmadi." -ForegroundColor Red
    exit 1
}

# 5. Synchronized Reference PCG Playback & Capture
Write-Host "`n[4/5] Senkronize PCG fantom deneyi baslatiliyor..." -ForegroundColor Green
& $Py $Runner --port $Port --reference $Reference --quiet-session $QuietWav --play-audio --verify-audio-routing --operator $Operator --notes $Notes
$RunExit = $LASTEXITCODE

# 6. Package Evidence
Write-Host "`n[5/5] Kanit paketi (ZIP) hazirlaniyor..." -ForegroundColor Green
& $Py $Packager --operator $Operator --notes $Notes
exit $RunExit
