param([switch]$Json, [string]$Output = "")
$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$python = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Project .venv missing. See the lab runbook.' }
$cliArgs = @((Join-Path $PSScriptRoot 'preflight.py'))
if ($Json) { $cliArgs += '--json' }
if ($Output) { $cliArgs += @('--output', $Output) }
& $python @cliArgs
exit $LASTEXITCODE
