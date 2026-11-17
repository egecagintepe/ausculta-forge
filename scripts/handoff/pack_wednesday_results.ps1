param(
    [string]$Output = "",
    [string]$Operator = "Kaan_Ozan",
    [string]$Notes = "",
    [string]$PhotosDir = ""
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    $pyExe = $venvPython
    $pyPrefix = @()
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pyExe = "py"
    $pyPrefix = @("-3.11")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pyExe = "python"
    $pyPrefix = @()
} else {
    throw "Python bulunamadi. Once .\scripts\handoff\windows_setup.ps1 calistirin."
}

$scriptPath = Join-Path $repoRoot 'tools\hardware\pack_lab_return.py'
$cliArgs = @($scriptPath, "--root", $repoRoot, "--operator", $Operator)
if ($Output) { $cliArgs += @("--output", $Output) }
if ($Notes) { $cliArgs += @("--notes", $Notes) }
if ($PhotosDir) { $cliArgs += @("--extra-dir", $PhotosDir) }

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AuscultaForge — Lab Kanit ve Olcum Teslim Paketi (ZIP)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$jsonOut = & $pyExe @pyPrefix @cliArgs
if ($LASTEXITCODE -ne 0) {
    throw "Teslim ZIP paketi olusturulamadi (exit $LASTEXITCODE)."
}

$summaryText = ($jsonOut -join "`n")
$parsed = $summaryText | ConvertFrom-Json

Write-Host "[TAMAMLANDI] GitHub veya Git kullanmaniza gerek kalmadan teslim paketi hazir:" -ForegroundColor Green
Write-Host ("  ZIP Dosyasi : {0}" -f $parsed.zip_path) -ForegroundColor White
Write-Host ("  Boyut       : {0:N0} byte ({1} dosya)" -f $parsed.zip_size_bytes, $parsed.file_count) -ForegroundColor White
Write-Host ("  SHA-256     : {0}" -f $parsed.zip_sha256) -ForegroundColor White
Write-Host ""
Write-Host "Bu tek .zip dosyasini Google Drive / WhatsApp / E-posta ile Ege'ye gonderin." -ForegroundColor Yellow
